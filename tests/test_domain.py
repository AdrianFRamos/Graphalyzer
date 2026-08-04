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


def test_pasta_do_no_relativa_ao_projeto():
    """A cor do nó vem da pasta, então ela precisa sair relativa à raiz."""
    from graphalyzer.domain.views import pasta_do_no

    no = Node(
        id="x",
        name="x",
        type=NodeType.FUNCTION,
        file_path="/proj/backend/app/api/rotas.py",
    )

    assert pasta_do_no(no, "/proj") == "backend/app/api"
    assert pasta_do_no(no, "/proj/backend/app/api") == ""


def test_cytoscape_inclui_a_pasta():
    """O payload leva a pasta: é o que o dashboard e o HTML usam para colorir."""
    graph = ProjectGraph(project_name="t", project_path="/proj")
    graph.add_node(
        Node(
            id="a",
            name="a",
            type=NodeType.FILE,
            file_path="/proj/modulos/financeiro/a.py",
        )
    )

    dados = to_cytoscape(graph, "all")
    assert dados["nodes"][0]["data"]["folder"] == "modulos/financeiro"


def test_detalhe_traz_entradas_e_saidas_reais():
    """O pop-up mostra o que de fato chega e sai, não só a assinatura.

    Parâmetro diz o que a rotina aceita; a aresta de fluxo diz qual variável
    chega, vinda de quem — é essa a informação que o grafo tem e o painel
    antigo jogava fora.
    """
    from conftest import build_graph
    from graphalyzer.domain.views import node_detail

    graph = build_graph(
        {
            "f.py": (
                "def somar(a: float, b: float) -> float:\n"
                "    return a + b\n\n"
                "def main(x: float, y: float) -> float:\n"
                "    return somar(x, y)\n"
            )
        }
    )

    alvo = next(n for n in graph.nodes.values() if n.name == "somar")
    detalhe = node_detail(graph, alvo.id)

    assert detalhe["signature"] == "somar(a: float, b: float) -> float"

    variaveis = {e["variavel"] for e in detalhe["entradas"]}
    assert variaveis == {"x", "y"}, detalhe["entradas"]
    assert all(e["origem"] == "main" for e in detalhe["entradas"])
    assert all(e["tipo"] == "float" for e in detalhe["entradas"])

    assert "main" in {c["nome"] for c in detalhe["chamado_por"]}

    origem = node_detail(graph, next(
        n.id for n in graph.nodes.values() if n.name == "main"
    ))
    assert {s["destino"] for s in origem["saidas"]} == {"somar"}
    assert "somar" in {c["nome"] for c in origem["chama"]}


def test_detalhe_de_no_inexistente_e_nulo():
    from graphalyzer.domain.views import node_detail

    graph = ProjectGraph(project_name="t", project_path="/t")
    assert node_detail(graph, "nao-existe") is None
