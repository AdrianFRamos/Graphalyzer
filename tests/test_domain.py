"""Testes da camada de domínio: invariantes do grafo."""

import pytest

from graphalyzer.domain.models import Edge, EdgeType, Node, NodeType, ProjectGraph
from graphalyzer.domain.views import to_cytoscape


def _node(node_id: str, node_type: NodeType = NodeType.FUNCTION) -> Node:
    return Node(id=node_id, name=node_id, type=node_type, file_path="f.py")


def test_add_edge_rejeita_aresta_pendente():
    """O grafo recusa aresta pendente em vez de guardá-la silenciosamente.

    Era esse silêncio que escondia arestas apontando para nós inexistentes.
    """
    graph = ProjectGraph(project_name="t", project_path="/t")
    graph.add_node(_node("a"))

    with pytest.raises(ValueError):
        graph.add_edge(Edge(source_id="a", target_id="inexistente", type=EdgeType.CALLS))

    assert graph.edges == []


def test_add_edge_deduplica():
    """A mesma aresta adicionada duas vezes conta uma só."""
    graph = ProjectGraph(project_name="t", project_path="/t")
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))

    for _ in range(2):
        graph.add_edge(
            Edge(source_id="a", target_id="b", type=EdgeType.CALLS, label="b")
        )

    assert len(graph.edges) == 1


def test_cytoscape_nao_emite_aresta_orfa():
    """Ao filtrar por visualização, aresta sem os dois extremos visíveis some.

    O Cytoscape quebra a renderização se receber aresta apontando para nó
    que não foi enviado.
    """
    graph = ProjectGraph(project_name="t", project_path="/t")
    graph.add_node(_node("arquivo", NodeType.FILE))
    graph.add_node(_node("funcao", NodeType.FUNCTION))
    graph.add_edge(
        Edge(source_id="arquivo", target_id="funcao", type=EdgeType.USES)
    )

    somente_arquivos = to_cytoscape(graph, "file")
    assert len(somente_arquivos["nodes"]) == 1
    assert somente_arquivos["edges"] == []

    tudo = to_cytoscape(graph, "all")
    assert len(tudo["nodes"]) == 2 and len(tudo["edges"]) == 1
