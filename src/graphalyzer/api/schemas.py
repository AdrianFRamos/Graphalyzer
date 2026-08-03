"""Contratos de entrada e saída da API."""

from typing import Optional

from pydantic import BaseModel, Field

from graphalyzer import config


class AnalysisRequest(BaseModel):
    """Pedido de análise de um projeto local."""

    project_path: str = Field(..., description="Caminho do projeto a analisar")
    use_ai: bool = False
    ai_provider: str = config.DEFAULT_AI_PROVIDER
    ai_model: str = config.DEFAULT_AI_MODEL
    use_cache: bool = Field(True, description="Reaproveita análise anterior se o projeto não mudou")


class AnalysisResponse(BaseModel):
    """Resumo de uma análise concluída."""

    analysis_id: str
    status: str
    project_name: str
    # O caminho já resolvido (traduzido do host, quando em container). O
    # frontend precisa dele para reanalisar quando o servidor reinicia.
    project_path: str
    file_count: int
    function_count: int
    class_count: int
    edge_count: int
    timestamp: Optional[str] = None
    from_cache: bool = False


class CacheStats(BaseModel):
    """Estatísticas do cache."""

    cached_projects: int
    cache_bytes: int
    in_memory_analyses: int
