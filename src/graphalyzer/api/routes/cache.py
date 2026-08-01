"""Endpoints do cache de análises."""

from typing import Optional

from fastapi import APIRouter

from graphalyzer.api.routes.analysis import store
from graphalyzer.api.schemas import CacheStats
from graphalyzer.storage.cache import AnalysisCache

router = APIRouter(prefix="/api/cache", tags=["cache"])

cache = AnalysisCache()


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats() -> CacheStats:
    """Estatísticas do cache em disco e das análises em memória."""
    stats = cache.statistics()
    return CacheStats(**stats, in_memory_analyses=len(store))


@router.post("/clear")
async def clear_cache(project_path: Optional[str] = None):
    """Limpa o cache — de um projeto específico ou inteiro."""
    removidos = cache.clear(project_path)
    return {"message": "Cache limpo", "removidos": removidos}
