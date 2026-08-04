"""Análise semântica voltada à documentação.

Enriquece **arquivos** e o **projeto**, não funções isoladas. É o que a
documentação consome: a responsabilidade de cada arquivo e uma visão geral da
organização. Analisar função por função custava uma chamada por rotina — num
projeto real, milhares — e não mudava uma linha do documento gerado.

O que é enviado ao modelo é a estrutura extraída (assinaturas, imports,
relações), não o código-fonte inteiro: mais barato e menos exposto.
"""

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional

from graphalyzer.ai.credentials import obter_chave
from graphalyzer.domain.models import NodeType, ProjectGraph
from graphalyzer.storage.docs import ConstrutorDeDocumentacao, DocumentoDeArquivo

logger = logging.getLogger(__name__)

# Chamadas em paralelo. Alto demais bate em limite de taxa; baixo demais
# torna um projeto de 100 arquivos uma espera longa.
CONCORRENCIA = 6

PROMPT_ARQUIVO = """Você documenta código. Analise a estrutura abaixo e responda\
 em JSON, em português do Brasil.

Arquivo: {nome}
Pasta: {camada}
Linguagem: {linguagem}
Imports: {imports}
Estrutura:
{estrutura}
Relaciona-se com: {relacoes}

Responda apenas com JSON:
{{"responsabilidade": "uma frase objetiva sobre o papel deste arquivo no sistema",
  "categoria": "uma palavra: api, dominio, persistencia, ui, infra, teste, config ou util",
  "observacoes": "no máximo duas frases sobre acoplamento, risco ou padrão notável; vazio se não houver"}}

Descreva apenas o que a estrutura mostra. Não invente comportamento."""

PROMPT_PROJETO = """Você analisa arquitetura de software. Com base no inventário\
 abaixo, escreva uma análise em português do Brasil.

Projeto: {projeto}
Arquivos: {arquivos} | Funções: {funcoes} | Classes: {classes}
Linguagens: {linguagens}

Organização por pasta:
{pastas}

Arquivos mais conectados:
{centrais}

Fluxo de dados entre arquivos (amostra):
{fluxos}

Responda apenas com JSON:
{{"visao_geral": "2 a 4 frases sobre o que o sistema faz e como está organizado",
  "organizacao": ["ponto sobre a estrutura de pastas e camadas", "..."],
  "pontos_de_atencao": ["acoplamento, concentração, ausência de testes, etc.", "..."],
  "sugestoes": ["recomendação prática", "..."]}}

Baseie-se apenas no inventário. Não invente arquivos nem comportamento."""


@dataclass
class AnaliseDoProjeto:
    """Resultado da análise de organização."""

    visao_geral: str = ""
    organizacao: List[str] = None
    pontos_de_atencao: List[str] = None
    sugestoes: List[str] = None

    def __post_init__(self):
        self.organizacao = self.organizacao or []
        self.pontos_de_atencao = self.pontos_de_atencao or []
        self.sugestoes = self.sugestoes or []


def _json_da_resposta(texto: str) -> Optional[dict]:
    """Extrai o objeto JSON da resposta, tolerando texto ao redor."""
    if not texto:
        return None
    achado = re.search(r"\{.*\}", texto, re.DOTALL)
    if not achado:
        return None
    try:
        return json.loads(achado.group())
    except json.JSONDecodeError:
        logger.warning("Resposta da IA não era JSON válido; ignorada")
        return None


class DocumentationAI:
    """Cliente de LLM focado em documentação e organização."""

    def __init__(self, provider: str = "claude", model: str = "claude-sonnet-5"):
        self.provider = provider
        self.model = model
        self.client = self._criar_cliente()

    @property
    def disponivel(self) -> bool:
        return self.client is not None

    def _criar_cliente(self):
        chave = obter_chave(self.provider)
        if not chave:
            logger.info("Sem chave para %s; análise por IA desligada", self.provider)
            return None

        try:
            if self.provider == "claude":
                from anthropic import Anthropic

                return Anthropic(api_key=chave)

            from openai import OpenAI

            return OpenAI(api_key=chave)
        except ImportError:
            logger.warning("SDK de %s não instalado", self.provider)
            return None

    def _perguntar(self, prompt: str, max_tokens: int = 700) -> str:
        """Uma chamada ao modelo. Erro vira string vazia, nunca exceção:
        falha de IA degrada a documentação, não derruba a análise."""
        try:
            if self.provider == "claude":
                resposta = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resposta.content[0].text

            resposta = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resposta.choices[0].message.content or ""
        except Exception as exc:
            # Sem o prompt no log: ele carrega estrutura do código do usuário
            logger.warning("Chamada à IA falhou: %s", type(exc).__name__)
            return ""

    # -- Arquivos ---------------------------------------------------------

    def resumir_arquivos(self, graph: ProjectGraph, cache=None) -> int:
        """Preenche `ai_summary` e `ai_category` dos nós de arquivo.

        É este campo que a documentação usa como Responsabilidade quando o
        arquivo não tem docstring. Devolve quantos foram analisados.
        """
        if not self.disponivel:
            return 0

        documentos = {
            d.nome: d for d in ConstrutorDeDocumentacao(graph).documentos()
        }
        arquivos = [
            n for n in graph.nodes.values() if n.type == NodeType.FILE
        ]

        def trabalhar(node):
            doc = documentos.get(node.metadata.get("filename", ""))
            if doc is None:
                return None

            prompt = self._prompt_do_arquivo(doc, node)
            chave = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

            # Conteúdo idêntico, resposta idêntica: não se paga duas vezes
            if cache is not None:
                guardado = cache.ai_get(chave)
                if guardado is not None:
                    return node, guardado

            dados = _json_da_resposta(self._perguntar(prompt))
            if dados and cache is not None:
                cache.ai_store(chave, dados)
            return (node, dados) if dados else None

        analisados = 0
        with ThreadPoolExecutor(max_workers=CONCORRENCIA) as executor:
            for resultado in executor.map(trabalhar, arquivos):
                if not resultado:
                    continue
                node, dados = resultado
                node.ai_summary = dados.get("responsabilidade") or None
                node.ai_category = dados.get("categoria") or None
                if dados.get("observacoes"):
                    node.metadata["ai_observacoes"] = dados["observacoes"]
                analisados += 1

        logger.info("IA resumiu %d de %d arquivos", analisados, len(arquivos))
        return analisados

    def _prompt_do_arquivo(self, doc: DocumentoDeArquivo, node) -> str:
        estrutura = []
        for categoria, subitens in doc.processamento[:12]:
            estrutura.append(f"- {categoria}")
            estrutura += [f"    {s}" for s in subitens[:12]]

        return PROMPT_ARQUIVO.format(
            nome=doc.nome,
            camada=doc.camada,
            linguagem=doc.linguagem,
            imports=", ".join(node.metadata.get("imports", [])[:15]) or "nenhum",
            estrutura="\n".join(estrutura) or "(sem funções ou classes)",
            relacoes=", ".join(doc.relacionamentos[:12]) or "nenhuma",
        )

    # -- Projeto ----------------------------------------------------------

    def analisar_organizacao(self, graph: ProjectGraph) -> AnaliseDoProjeto:
        """Análise da organização do projeto como um todo."""
        if not self.disponivel:
            return AnaliseDoProjeto()

        dados = _json_da_resposta(
            self._perguntar(self._prompt_do_projeto(graph), max_tokens=1500)
        )
        if not dados:
            return AnaliseDoProjeto()

        return AnaliseDoProjeto(
            visao_geral=dados.get("visao_geral", ""),
            organizacao=dados.get("organizacao") or [],
            pontos_de_atencao=dados.get("pontos_de_atencao") or [],
            sugestoes=dados.get("sugestoes") or [],
        )

    def _prompt_do_projeto(self, graph: ProjectGraph) -> str:
        from graphalyzer.domain.models import EdgeType
        from graphalyzer.domain.views import pasta_do_no

        arquivos = [n for n in graph.nodes.values() if n.type == NodeType.FILE]

        por_pasta: Dict[str, int] = {}
        linguagens: Dict[str, int] = {}
        for node in arquivos:
            pasta = pasta_do_no(node, graph.project_path) or "."
            por_pasta[pasta] = por_pasta.get(pasta, 0) + 1
            lang = node.metadata.get("language", "?")
            linguagens[lang] = linguagens.get(lang, 0) + 1

        graus = sorted(
            (
                (len(graph.get_edges_to(n.id)) + len(graph.get_edges_from(n.id)), n)
                for n in arquivos
            ),
            key=lambda par: par[0],
            reverse=True,
        )

        nome_de = {n.id: n.metadata.get("filename", n.name) for n in arquivos}
        arquivo_de = {n.id: n.file_path for n in graph.nodes.values()}
        caminho_para_nome = {n.file_path: nome_de[n.id] for n in arquivos}

        fluxos = []
        vistos = set()
        for edge in graph.edges:
            if edge.type != EdgeType.DATA_FLOW:
                continue
            origem = caminho_para_nome.get(arquivo_de.get(edge.source_id))
            destino = caminho_para_nome.get(arquivo_de.get(edge.target_id))
            if not origem or not destino or origem == destino:
                continue
            par = f"{origem} -> {destino}"
            if par not in vistos:
                vistos.add(par)
                fluxos.append(f"- {par} ({edge.label})")
            if len(fluxos) >= 25:
                break

        return PROMPT_PROJETO.format(
            projeto=graph.project_name,
            arquivos=graph.file_count,
            funcoes=graph.function_count,
            classes=graph.class_count,
            linguagens=", ".join(f"{k} ({v})" for k, v in sorted(linguagens.items())),
            pastas="\n".join(
                f"- {pasta}: {n} arquivo(s)"
                for pasta, n in sorted(por_pasta.items(), key=lambda p: -p[1])[:30]
            ),
            centrais="\n".join(
                f"- {nome_de[node.id]} ({grau} conexões)" for grau, node in graus[:15]
            ),
            fluxos="\n".join(fluxos) or "(nenhum fluxo entre arquivos)",
        )
