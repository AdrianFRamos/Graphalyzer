"""Geração de documentação técnica a partir da extração.

Um documento por arquivo de código, com a mesma estrutura em qualquer formato:
responsabilidade, entradas, processamento, saídas, relacionamentos e notas.

O modelo (`DocumentoDeArquivo`) é montado uma vez e renderizado depois — por
isso Markdown e PDF nunca divergem no conteúdo, só na apresentação.

Nada aqui é inventado: o que não foi extraído aparece como ausente.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Tuple

from graphalyzer.domain.models import EdgeType, Node, NodeType, ProjectGraph
from graphalyzer.domain.views import pasta_do_no

logger = logging.getLogger(__name__)


@dataclass
class DocumentoDeArquivo:
    """Conteúdo documentado de um arquivo, independente do formato de saída."""

    nome: str
    camada: str
    linguagem: str
    tag: str
    responsabilidade: str
    inputs: List[str] = field(default_factory=list)
    # (categoria, subitens) — vira lista numerada com subitens identados
    processamento: List[Tuple[str, List[str]]] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    relacionamentos: List[str] = field(default_factory=list)
    notas: List[str] = field(default_factory=list)


def _primeira_frase(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    limpo = " ".join(texto.strip().split())
    return re.split(r"(?<=[.!?])\s", limpo, maxsplit=1)[0][:300] or None


def _assinatura(node: Node) -> str:
    partes = [
        f"{p.name}: {p.type_hint}" if p.type_hint else p.name for p in node.parameters
    ]
    retorno = f" -> {node.return_value.type_hint}" if node.return_value else ""
    return f"{node.name}({', '.join(partes)}){retorno}"


class ConstrutorDeDocumentacao:
    """Transforma o grafo em documentos, um por arquivo."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph
        self._por_arquivo = self._agrupar_por_arquivo()
        self._nome = {
            n.id: n.metadata.get("filename") or Path(n.file_path).name
            for n in graph.nodes.values()
            if n.type == NodeType.FILE
        }

    def documentos(self) -> List[DocumentoDeArquivo]:
        arquivos = [n for n in self.graph.nodes.values() if n.type == NodeType.FILE]
        return [
            self._documento(n)
            for n in sorted(arquivos, key=lambda n: (pasta_do_no(n, self.graph.project_path), self._nome[n.id]))
        ]

    def _documento(self, file_node: Node) -> DocumentoDeArquivo:
        conteudo = self._por_arquivo.get(file_node.id, {})
        rotinas = conteudo.get("funcoes", []) + conteudo.get("metodos", [])

        return DocumentoDeArquivo(
            nome=self._nome[file_node.id],
            camada=pasta_do_no(file_node, self.graph.project_path) or ".",
            linguagem=file_node.metadata.get("language", "desconhecida"),
            tag=self._tag(file_node),
            responsabilidade=self._responsabilidade(file_node, conteudo),
            inputs=self._inputs(file_node, rotinas),
            processamento=self._processamento(conteudo),
            outputs=self._outputs(file_node, rotinas),
            relacionamentos=self._relacionamentos(file_node),
            notas=self._notas(file_node, rotinas),
        )

    def _tag(self, file_node: Node) -> str:
        """Etiqueta derivada da camada — o topo da árvore é o módulo."""
        camada = pasta_do_no(file_node, self.graph.project_path)
        return camada.split("/")[0] if camada else file_node.metadata.get(
            "language", "codigo"
        )

    def _responsabilidade(self, file_node: Node, conteudo: Dict) -> str:
        # Docstring do módulo, depois resumo da IA. Sem nenhum dos dois,
        # descreve-se a estrutura — que é fato extraído, não suposição.
        frase = _primeira_frase(file_node.docstring) or _primeira_frase(
            file_node.ai_summary
        )
        if frase:
            return frase

        partes = []
        if conteudo.get("classes"):
            partes.append(f"{len(conteudo['classes'])} classe(s)")
        if conteudo.get("funcoes"):
            partes.append(f"{len(conteudo['funcoes'])} função(ões)")

        return f"Define {' e '.join(partes)}." if partes else (
            "Sem descrição declarada no arquivo."
        )

    def _inputs(self, file_node: Node, rotinas: List[Node]) -> List[str]:
        itens = [
            f"Import: {m}" for m in file_node.metadata.get("imports", [])[:20]
        ]
        itens += [
            _assinatura(n) for n in rotinas if n.is_public and n.parameters
        ]
        return itens or ["Sem entradas declaradas."]

    def _processamento(self, conteudo: Dict) -> List[Tuple[str, List[str]]]:
        blocos = []

        for classe in conteudo.get("classes", []):
            metodos = [
                m
                for m in conteudo.get("metodos", [])
                if m.id.startswith(f"method::{classe.file_path}::{classe.name}::")
            ]
            subitens = [
                f"{_assinatura(m)} — complexidade {m.complexity}" for m in metodos
            ] or ["Sem métodos extraídos."]
            blocos.append((f"Classe {classe.name}", subitens))

        funcoes = conteudo.get("funcoes", [])
        if funcoes:
            blocos.append(
                (
                    "Funções de módulo",
                    [f"{_assinatura(f)} — complexidade {f.complexity}" for f in funcoes],
                )
            )

        return blocos or [
            ("Sem lógica extraída", ["O arquivo não declara funções nem classes."])
        ]

    def _outputs(self, file_node: Node, rotinas: List[Node]) -> List[str]:
        itens = [
            f"{n.name} -> {n.return_value.type_hint}"
            for n in rotinas
            if n.is_public and n.return_value and n.return_value.type_hint
        ]

        for destino, variaveis in self._fluxos_de_saida(file_node).items():
            amostra = ", ".join(sorted(variaveis)[:6])
            itens.append(f"Alimenta {destino} com: {amostra}")

        return itens or ["Sem saídas declaradas."]

    def _relacionamentos(self, file_node: Node) -> List[str]:
        vizinhos = set()
        for edge in self.graph.get_edges_from(file_node.id):
            if alvo := self._nome.get(edge.target_id):
                vizinhos.add(alvo)
        for edge in self.graph.get_edges_to(file_node.id):
            if origem := self._nome.get(edge.source_id):
                vizinhos.add(origem)

        vizinhos.discard(self._nome[file_node.id])
        return sorted(vizinhos) or ["Nenhuma dependência interna detectada."]

    def analise_do_projeto(self) -> Dict[str, Any]:
        """Visão geral produzida pela IA, se houver. Vazio sem ela."""
        return self.graph.metadata.get("analise_do_projeto") or {}

    def _notas(self, file_node: Node, rotinas: List[Node]) -> List[str]:
        notas = []

        if rotinas:
            complexidades = [n.complexity for n in rotinas]
            documentados = sum(1 for n in rotinas if n.docstring)
            notas.append(
                f"Complexidade ciclomática máxima {max(complexidades)}, "
                f"média {sum(complexidades) / len(complexidades):.1f}."
            )
            notas.append(f"Docstring em {documentados} de {len(rotinas)} rotinas.")

            privadas = sum(1 for n in rotinas if not n.is_public)
            if privadas:
                notas.append(f"{privadas} rotina(s) de uso interno.")

        if file_node.metadata.get("ai_observacoes"):
            notas.append(f"Observação da IA: {file_node.metadata['ai_observacoes']}")

        return notas or ["Sem métricas relevantes para este arquivo."]

    # -- Apoio -------------------------------------------------------------

    def _agrupar_por_arquivo(self) -> Dict[str, Dict[str, List[Node]]]:
        indice = {
            n.file_path: n.id
            for n in self.graph.nodes.values()
            if n.type == NodeType.FILE
        }
        agrupado: Dict[str, Dict[str, List[Node]]] = {}

        for node in self.graph.nodes.values():
            if node.type == NodeType.FILE:
                continue
            file_id = indice.get(node.file_path)
            if not file_id:
                continue

            balde = agrupado.setdefault(
                file_id, {"classes": [], "funcoes": [], "metodos": []}
            )
            if node.type == NodeType.CLASS:
                balde["classes"].append(node)
            elif node.id.startswith("method::"):
                balde["metodos"].append(node)
            else:
                balde["funcoes"].append(node)

        return agrupado

    def _fluxos_de_saida(self, file_node: Node) -> Dict[str, set]:
        """Variáveis que saem deste arquivo para outros, por arquivo destino."""
        daqui = {
            n.id
            for n in self.graph.nodes.values()
            if n.file_path == file_node.file_path and n.type != NodeType.FILE
        }
        caminho_de = {n.id: n.file_path for n in self.graph.nodes.values()}
        nome_por_caminho = {
            n.file_path: self._nome[n.id]
            for n in self.graph.nodes.values()
            if n.type == NodeType.FILE
        }

        saidas: Dict[str, set] = {}
        for edge in self.graph.edges:
            if edge.type != EdgeType.DATA_FLOW or edge.source_id not in daqui:
                continue
            destino = caminho_de.get(edge.target_id)
            if not destino or destino == file_node.file_path:
                continue
            if (nome := nome_por_caminho.get(destino)) and edge.label:
                saidas.setdefault(nome, set()).add(edge.label)

        return saidas
