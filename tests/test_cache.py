"""Testes do cache de análises.

Um cache que não invalida é pior que nenhum: entrega grafo velho de código
novo, em silêncio. É esse o comportamento que estes testes prendem.
"""

import sqlite3
import time

import pytest

from conftest import build_graph

from graphalyzer.analysis.builder import GraphBuilder
from graphalyzer.domain.models import ProjectGraph
from graphalyzer.storage.cache import AnalysisCache


@pytest.fixture
def projeto(tmp_path):
    """Um projeto pequeno em disco, para poder ser modificado."""
    origem = tmp_path / "projeto"
    origem.mkdir()
    (origem / "calc.py").write_text(
        "def somar(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
    )
    return origem


@pytest.fixture
def cache(tmp_path):
    return AnalysisCache(cache_dir=str(tmp_path / "cache"))


def test_ida_e_volta_preserva_o_grafo(projeto, cache):
    """O grafo reconstruído do cache é igual ao original, com código-fonte."""
    original = GraphBuilder(str(projeto)).build()
    cache.store(str(projeto), original.to_json(indent=None, include_source=True))

    recuperado = ProjectGraph.from_dict(cache.get(str(projeto)))

    assert recuperado.file_count == original.file_count
    assert set(recuperado.nodes) == set(original.nodes)
    assert len(recuperado.edges) == len(original.edges)

    # O painel de detalhes mostra o código: sem ele, o cache degradaria a UI
    função = next(n for n in recuperado.nodes.values() if n.name == "somar")
    assert função.source_code and "return a + b" in função.source_code
    assert [p.name for p in função.parameters] == ["a", "b"]
    assert função.parameters[0].type_hint == "int"


def test_invalida_quando_o_codigo_muda(projeto, cache):
    """Editar um arquivo tem que invalidar — este é o ponto do teste."""
    graph = GraphBuilder(str(projeto)).build()
    cache.store(str(projeto), graph.to_json(indent=None, include_source=True))
    assert cache.get(str(projeto)) is not None

    time.sleep(1.1)  # o fingerprint usa mtime em segundos inteiros
    (projeto / "calc.py").write_text(
        "def somar(a: int, b: int) -> int:\n    return a + b\n\n"
        "def subtrair(a: int, b: int) -> int:\n    return a - b\n",
        encoding="utf-8",
    )

    assert cache.get(str(projeto)) is None


def test_invalida_quando_arquivo_e_adicionado(projeto, cache):
    """Arquivo novo muda o projeto, mesmo sem tocar nos existentes."""
    graph = GraphBuilder(str(projeto)).build()
    cache.store(str(projeto), graph.to_json(indent=None, include_source=True))

    (projeto / "novo.py").write_text("def outra():\n    pass\n", encoding="utf-8")

    assert cache.get(str(projeto)) is None


def test_fingerprint_ignora_pastas_de_dependencia(projeto, cache):
    """`node_modules` e afins não podem entrar na impressão digital.

    Se entrassem, qualquer `npm install` invalidaria o cache — e percorrê-las
    custaria mais que a própria análise.
    """
    antes = cache.fingerprint(str(projeto))

    lixo = projeto / "node_modules" / "pacote"
    lixo.mkdir(parents=True)
    (lixo / "index.js").write_text("module.exports = {};\n", encoding="utf-8")

    assert cache.fingerprint(str(projeto)) == antes


def test_grafo_sem_ia_nao_serve_para_pedido_com_ia(projeto, cache):
    """Quem pediu IA não pode receber um grafo que não passou por ela."""
    graph = GraphBuilder(str(projeto)).build()
    cache.store(str(projeto), graph.to_json(indent=None), has_ai=False)

    assert cache.get(str(projeto), require_ai=False) is not None
    assert cache.get(str(projeto), require_ai=True) is None


def test_esquema_antigo_e_recriado(tmp_path):
    """Banco de versão anterior é descartado em vez de quebrar toda consulta."""
    diretorio = tmp_path / "cache"
    diretorio.mkdir()
    db = diretorio / "analysis.db"

    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, obsoleto TEXT)")
        conn.commit()

    cache = AnalysisCache(cache_dir=str(diretorio))

    # Não pode estourar "no such column"
    assert cache.get("/qualquer") is None
    assert cache.statistics()["cached_projects"] == 0


def test_clear_remove(projeto, cache):
    graph = GraphBuilder(str(projeto)).build()
    cache.store(str(projeto), graph.to_json(indent=None))

    assert cache.statistics()["cached_projects"] == 1
    assert cache.clear(str(projeto)) == 1
    assert cache.get(str(projeto)) is None


def test_analise_usa_o_cache_na_segunda_vez(projeto, tmp_path, monkeypatch):
    """O serviço devolve `from_cache` quando reaproveita."""
    from graphalyzer.services import analysis as service

    monkeypatch.setattr(
        service, "_CACHE", AnalysisCache(cache_dir=str(tmp_path / "c2"))
    )

    primeira = service.analyze_project(str(projeto))
    assert not primeira.from_cache

    segunda = service.analyze_project(str(projeto))
    assert segunda.from_cache
    assert set(segunda.graph.nodes) == set(primeira.graph.nodes)

    # E o `--no-cache` continua reanalisando
    terceira = service.analyze_project(str(projeto), use_cache=False)
    assert not terceira.from_cache
