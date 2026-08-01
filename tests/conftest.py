"""Utilidades compartilhadas pelos testes."""

import tempfile
from pathlib import Path

import pytest

from graphalyzer.analysis.builder import GraphBuilder
from graphalyzer.domain.models import ProjectGraph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PROJECT = PROJECT_ROOT / "examples" / "sample_project"


def build_graph(source_by_file: dict) -> ProjectGraph:
    """Constrói um grafo a partir de fontes escritas num diretório temporário."""
    tmpdir = tempfile.mkdtemp()
    for name, source in source_by_file.items():
        path = Path(tmpdir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return GraphBuilder(tmpdir).build()


@pytest.fixture
def sample_graph() -> ProjectGraph:
    """Grafo do projeto de exemplo que acompanha o repositório."""
    return GraphBuilder(str(SAMPLE_PROJECT)).build()
