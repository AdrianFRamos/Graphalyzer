"""Endpoints de análise: criar, consultar, visualizar e exportar."""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from graphalyzer import config
from graphalyzer.api.schemas import AnalysisRequest, AnalysisResponse
from graphalyzer.domain.views import node_detail, to_cytoscape
from graphalyzer.services import analysis as service
from graphalyzer.storage.reports import (
    ArchitectureAnalyzer,
    DependencyReporter,
    QualityReportGenerator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

# Uma instância por processo; ver a nota de escopo em services.analysis.AnalysisStore
store = service.AnalysisStore()

# Extensão de arquivo -> (formato do exportador, media type)
EXPORT_FORMATS = {
    "json": ("json", "application/json"),
    "md": ("markdown", "text/markdown"),
    "html": ("html", "text/html"),
    "csv": ("csv", "text/csv"),
}


def _ajuda_de_caminho(erro: Exception) -> str:
    """Enriquece o 404 com os projetos realmente disponíveis.

    Rodando em container, o usuário digita naturalmente o caminho do host
    (`C:\\Users\\...`), que não existe lá dentro. Sem esta lista, o erro não
    dá nenhuma pista de qual caminho usar.
    """
    raiz = config.PROJECTS_ROOT
    if not raiz.is_dir():
        return str(erro)

    try:
        # Pastas ocultas (.cache, .aws...) enchem a lista e escondem os projetos
        disponiveis = sorted(
            p.name for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
    except OSError:
        return str(erro)

    if not disponiveis:
        return f"{erro} — nenhum projeto montado em {raiz}."

    amostra = ", ".join(f"{raiz.as_posix()}/{nome}" for nome in disponiveis[:8])
    resto = f" (+{len(disponiveis) - 8})" if len(disponiveis) > 8 else ""
    return (
        f"{erro}. Use o caminho de dentro do container. Disponíveis: {amostra}{resto}"
    )


def _get_graph(analysis_id: str):
    """Busca o grafo de uma análise ou responde 404."""
    analysis = store.get(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return analysis.graph


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_project(request: AnalysisRequest) -> AnalysisResponse:
    """Analisa um projeto Python local."""
    try:
        analysis = service.analyze_project(
            request.project_path,
            use_ai=request.use_ai,
            ai_provider=request.ai_provider,
            ai_model=request.ai_model,
            use_cache=request.use_cache,
        )
    except NotADirectoryError as exc:
        raise HTTPException(status_code=404, detail=_ajuda_de_caminho(exc))
    except Exception as exc:
        logger.exception("Falha ao analisar %s", request.project_path)
        raise HTTPException(status_code=500, detail=str(exc))

    store.add(analysis)
    graph = analysis.graph

    return AnalysisResponse(
        analysis_id=analysis.id,
        status="completed",
        project_name=graph.project_name,
        project_path=analysis.project_path,
        file_count=graph.file_count,
        function_count=graph.function_count,
        class_count=graph.class_count,
        edge_count=len(graph.edges),
        timestamp=analysis.created_at,
        from_cache=analysis.from_cache,
    )


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Resumo de uma análise."""
    graph = _get_graph(analysis_id)

    return {
        "analysis_id": analysis_id,
        "project_name": graph.project_name,
        "project_path": graph.project_path,
        "file_count": graph.file_count,
        "function_count": graph.function_count,
        "class_count": graph.class_count,
        "edge_count": len(graph.edges),
        "timestamp": graph.analysis_timestamp,
    }


@router.get("/analysis/{analysis_id}/graph")
async def get_graph(analysis_id: str, view_type: str = "file"):
    """Grafo no formato do Cytoscape, no nível de arquivo ou de função."""
    return to_cytoscape(_get_graph(analysis_id), view_type)


@router.get("/analysis/{analysis_id}/node/{node_id:path}")
async def get_node_details(analysis_id: str, node_id: str):
    """Detalhes de um nó: assinatura, complexidade, conexões e resumo da IA."""
    detail = node_detail(_get_graph(analysis_id), node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Nó não encontrado")
    return detail


@router.get("/analysis/{analysis_id}/metrics")
async def get_metrics(analysis_id: str):
    """Métricas de arquitetura, qualidade e dependências."""
    graph = _get_graph(analysis_id)

    architecture = ArchitectureAnalyzer(graph).analyze()
    quality = QualityReportGenerator(graph).generate()
    dependencies = DependencyReporter(graph)

    return {
        "architecture": {
            "total_nodes": architecture.total_nodes,
            "total_edges": architecture.total_edges,
            "average_connections": architecture.average_connections,
            "cyclomatic_complexity": architecture.cyclomatic_complexity,
            "coupling": architecture.coupling,
            "cohesion": architecture.cohesion,
        },
        "quality": {
            "documented_functions": quality.documented_functions,
            "total_functions": quality.total_functions,
            "documentation_coverage": quality.documentation_coverage,
            "type_hints_coverage": quality.type_hints_coverage,
            "average_complexity": quality.average_complexity,
        },
        "dependencies": {
            "most_connected": [
                {"node_id": node_id, "connections": connections}
                for node_id, connections in dependencies.get_most_connected_nodes(10)
            ],
            "isolated_count": len(dependencies.get_isolated_nodes()),
        },
    }


@router.get("/analysis/{analysis_id}/export/{export_format}")
async def export_analysis(analysis_id: str, export_format: str):
    """Baixa a análise em JSON, Markdown, HTML ou CSV."""
    graph = _get_graph(analysis_id)

    if export_format not in EXPORT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use: {', '.join(EXPORT_FORMATS)}",
        )

    exporter_format, media_type = EXPORT_FORMATS[export_format]

    # Diretório temporário, não arquivo: o CSV gera dois arquivos (nós e arestas)
    # e um caminho único devolveria download vazio.
    tmpdir = tempfile.mkdtemp()
    cleanup = BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True)

    try:
        written = service.export_graph(graph, tmpdir, [exporter_format])
    except Exception as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        logger.exception("Falha ao exportar %s", export_format)
        raise HTTPException(status_code=500, detail=str(exc))

    # Exportadores de múltiplos arquivos (CSV) descem como um único .zip
    produced = sorted(Path(tmpdir).glob("*.*"))
    if len(produced) > 1:
        archive = Path(shutil.make_archive(str(Path(tmpdir) / "export"), "zip", tmpdir))
        return FileResponse(
            archive,
            media_type="application/zip",
            filename=f"analysis_{export_format}.zip",
            background=cleanup,
        )

    return FileResponse(
        produced[0] if produced else written[0],
        media_type=media_type,
        filename=f"analysis.{export_format}",
        background=cleanup,
    )


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Remove uma análise da memória."""
    if not store.remove(analysis_id):
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return {"message": "Análise deletada"}
