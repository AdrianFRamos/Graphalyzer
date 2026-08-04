"""Orquestração da análise.

Único lugar que combina as camadas: constrói o grafo, enriquece com IA e
exporta. CLI e API chamam daqui — antes cada uma tinha a sua própria cópia
desta sequência, e elas já haviam divergido.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from graphalyzer import config
from graphalyzer.ai.analyzer import AIAnalyzer, LLMAnalyzer, MockAIAnalyzer
from graphalyzer.analysis.builder import GraphBuilder
from graphalyzer.domain.models import NodeType, ProjectGraph
from graphalyzer.storage.docs_render import MarkdownDocsExporter, PdfDocsExporter
from graphalyzer.storage.exporters import (
    CSVExporter,
    HTMLExporter,
    JSONExporter,
    MarkdownExporter,
)

logger = logging.getLogger(__name__)

EXPORTERS = {
    "json": (JSONExporter, "json"),
    "markdown": (MarkdownExporter, "md"),
    "html": (HTMLExporter, "html"),
    "csv": (CSVExporter, "csv"),
    # Documentação técnica por arquivo, o produto final da extração
    "docs": (MarkdownDocsExporter, "docs"),
    "pdf": (PdfDocsExporter, "pdf"),
}


@dataclass
class Analysis:
    """Uma análise concluída, identificada para consulta posterior."""

    id: str
    graph: ProjectGraph
    project_path: str
    created_at: str
    from_cache: bool = False


def build_ai_analyzer(provider: str, model: str) -> AIAnalyzer:
    """Devolve o analisador de IA pedido, caindo para o mock se indisponível.

    Sem chave de API ou sem o SDK instalado a análise continua — só perde o
    enriquecimento semântico, em vez de derrubar a execução inteira.
    """
    try:
        analyzer = LLMAnalyzer(provider=provider, model=model)
        if analyzer.client is None:
            raise RuntimeError(f"SDK de {provider} não disponível")
        return analyzer
    except Exception as exc:
        logger.warning("IA indisponível (%s); usando análise mock", exc)
        return MockAIAnalyzer()


def enrich_with_ai(graph: ProjectGraph, provider: str, model: str, cache=None) -> int:
    """Enriquece o grafo com análise semântica voltada à documentação.

    Alvo são os **arquivos** e a organização do projeto, não cada função: é o
    que a documentação consome, e custa uma chamada por arquivo em vez de uma
    por rotina — a diferença entre ~100 e vários milhares num projeto real.
    """
    from graphalyzer.ai.documentation import DocumentationAI

    ia = DocumentationAI(provider=provider, model=model)
    if not ia.disponivel:
        logger.warning("IA indisponível: sem chave ou SDK. Análise segue sem ela.")
        return 0

    analisados = ia.resumir_arquivos(graph, cache=cache)

    analise = ia.analisar_organizacao(graph)
    if analise.visao_geral or analise.organizacao:
        # Vai no grafo para sobreviver ao cache e chegar à documentação
        graph.metadata["analise_do_projeto"] = {
            "visao_geral": analise.visao_geral,
            "organizacao": analise.organizacao,
            "pontos_de_atencao": analise.pontos_de_atencao,
            "sugestoes": analise.sugestoes,
        }

    graph.ai_analysis_timestamp = datetime.now().isoformat()
    return analisados


_CACHE = None


def _get_cache():
    """Cache compartilhado, criado sob demanda.

    Preguiçoso de propósito: criar o SQLite no import quebraria quem só usa a
    camada de análise, e falha de cache nunca deve impedir uma análise.
    """
    global _CACHE

    if _CACHE is None:
        try:
            from graphalyzer.storage.cache import AnalysisCache

            _CACHE = AnalysisCache()
        except Exception as exc:
            logger.warning("Cache indisponível (%s); seguindo sem ele", exc)
            return None

    return _CACHE


def resolve_project_path(project_path: str) -> Path:
    """Traduz o caminho informado para um caminho que exista aqui dentro.

    Rodando em container, o usuário digita naturalmente o caminho do host
    (`C:\\Users\\bahni\\GBOrganiza`), que não existe no container. A tradução
    usa o mapeamento declarado em `GRAPHALYZER_HOST_ROOT` — não é adivinhação.
    """
    caminho = Path(project_path)
    if caminho.is_dir():
        return caminho

    raiz = config.PROJECTS_ROOT
    if not raiz.is_dir():
        return caminho

    # Barra invertida do Windows vira barra normal para comparar
    normalizado = project_path.replace("\\", "/").rstrip("/")

    if config.HOST_ROOT:
        host = config.HOST_ROOT.replace("\\", "/").rstrip("/")
        if normalizado.lower().startswith(host.lower()):
            resto = normalizado[len(host) :].lstrip("/")
            traduzido = raiz / resto if resto else raiz
            if traduzido.is_dir():
                logger.info("Caminho do host traduzido: %s -> %s", project_path, traduzido)
                return traduzido

    # Último recurso: o nome final bate com um único projeto montado.
    # Só vale se for inequívoco — na dúvida, deixa falhar com a lista de opções.
    nome = normalizado.rsplit("/", 1)[-1]
    if nome:
        iguais = [
            p for p in raiz.iterdir() if p.is_dir() and p.name.lower() == nome.lower()
        ]
        if len(iguais) == 1:
            logger.info("Projeto localizado pelo nome: %s -> %s", project_path, iguais[0])
            return iguais[0]

    return caminho


def analyze_project(
    project_path: str,
    use_ai: bool = False,
    ai_provider: str = config.DEFAULT_AI_PROVIDER,
    ai_model: str = config.DEFAULT_AI_MODEL,
    use_cache: bool = True,
) -> Analysis:
    """Analisa um projeto e devolve o resultado pronto para consulta ou export."""
    path = resolve_project_path(project_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Projeto não encontrado ou não é diretório: {path}")

    cache = _get_cache() if use_cache else None

    if cache is not None:
        guardado = cache.get(str(path), require_ai=use_ai)
        if guardado is not None:
            logger.info("Grafo recuperado do cache: %s", path)
            return Analysis(
                id=str(uuid.uuid4()),
                graph=ProjectGraph.from_dict(guardado),
                project_path=str(path),
                created_at=guardado.get("analysis_timestamp")
                or datetime.now().isoformat(),
                from_cache=True,
            )

    graph = GraphBuilder(str(path)).build()

    if use_ai:
        count = enrich_with_ai(graph, ai_provider, ai_model, cache=cache)
        logger.info("IA aplicada a %d arquivos", count)

    if cache is not None:
        try:
            # include_source: o cache precisa reconstruir o grafo inteiro,
            # inclusive o código que o painel de detalhes mostra
            cache.store(
                str(path),
                graph.to_json(indent=None, include_source=True),
                has_ai=use_ai,
            )
        except Exception as exc:
            # Falhar em gravar cache não pode derrubar uma análise que deu certo
            logger.warning("Não foi possível gravar o cache: %s", exc)

    return Analysis(
        id=str(uuid.uuid4()),
        graph=graph,
        project_path=str(path),
        created_at=graph.analysis_timestamp or datetime.now().isoformat(),
    )


def export_graph(graph: ProjectGraph, output_dir: str, formats: List[str]) -> List[Path]:
    """Exporta o grafo nos formatos pedidos. Devolve os arquivos gerados."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written = []
    for fmt in formats:
        if fmt not in EXPORTERS:
            raise ValueError(f"Formato não suportado: {fmt}")
        exporter_cls, extension = EXPORTERS[fmt]
        # `docs` produz um diretório de notas, não um arquivo único
        target = out / ("documentacao" if extension == "docs" else f"analysis.{extension}")
        exporter_cls(graph).export(str(target))
        written.append(target)

    return written


class AnalysisStore:
    """Guarda análises em memória, por ID.

    ponytail: dicionário em processo — some ao reiniciar e não serve a vários
    workers. Trocar por SQLite (o `storage.cache` já existe) quando a API
    precisar sobreviver a restart ou rodar com mais de um worker.
    """

    def __init__(self) -> None:
        self._items: Dict[str, Analysis] = {}

    def add(self, analysis: Analysis) -> None:
        self._items[analysis.id] = analysis

    def get(self, analysis_id: str) -> Optional[Analysis]:
        return self._items.get(analysis_id)

    def remove(self, analysis_id: str) -> bool:
        return self._items.pop(analysis_id, None) is not None

    def __len__(self) -> int:
        return len(self._items)
