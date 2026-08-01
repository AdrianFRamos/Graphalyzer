"""Testes do construtor de grafo: resolução de símbolos e arestas."""

from pathlib import Path

from conftest import build_graph

from graphalyzer.domain.models import EdgeType


def test_nenhuma_aresta_pendente(sample_graph):
    """Toda aresta referencia nós existentes.

    Invariante central: antes, 100% das arestas `calls` vindas de métodos
    apontavam para uma origem inexistente e ninguém percebia.
    """
    for edge in sample_graph.edges:
        assert edge.source_id in sample_graph.nodes, f"origem pendente: {edge.source_id}"
        assert edge.target_id in sample_graph.nodes, f"destino pendente: {edge.target_id}"

    assert sample_graph.edges, "grafo sem nenhuma aresta"


def test_import_interno_vira_aresta():
    """Import entre arquivos do projeto produz aresta; import externo não."""
    graph = build_graph(
        {
            "pkg/__init__.py": "",
            "pkg/util.py": "def helper():\n    return 1\n",
            "app.py": (
                "import os\n"
                "from pkg.util import helper\n\n"
                "def run():\n"
                "    return helper()\n"
            ),
        }
    )

    alvos = {
        Path(graph.nodes[e.target_id].file_path).name
        for e in graph.edges
        if e.type == EdgeType.IMPORT
    }

    assert "util.py" in alvos, f"import interno não resolvido: {alvos}"
    assert not any("os" in Path(a).stem for a in alvos), "import externo virou aresta"


def test_chamada_de_metodo_liga_ao_no_do_metodo():
    """Chamada dentro de um método parte do nó do método, não de um ID inventado."""
    graph = build_graph(
        {
            "m.py": (
                "class Calc:\n"
                "    def dobro(self, x: int) -> int:\n"
                "        return x * 2\n\n"
                "    def run(self, x: int) -> int:\n"
                "        return self.dobro(x)\n"
            )
        }
    )

    chamadas = [e for e in graph.edges if e.type == EdgeType.CALLS]
    assert chamadas, "nenhuma chamada detectada"

    assert "run" in {graph.nodes[e.source_id].name for e in chamadas}
    assert "dobro" in {graph.nodes[e.target_id].name for e in chamadas}


def test_fluxo_de_dados_carrega_variavel_e_tipo():
    """A aresta de fluxo nomeia a variável e o tipo que ela assume no destino."""
    graph = build_graph(
        {
            "f.py": (
                "def soma(a: float, b: float) -> float:\n"
                "    return a + b\n\n"
                "def main(x: float, y: float) -> float:\n"
                "    return soma(x, y)\n"
            )
        }
    )

    fluxos = [e for e in graph.edges if e.type == EdgeType.DATA_FLOW]
    assert fluxos, "nenhum fluxo de dados detectado"
    assert {e.label for e in fluxos} == {"x", "y"}
    assert all(e.data_type == "float" for e in fluxos), [e.data_type for e in fluxos]


def test_fluxo_desconta_self_no_tipo():
    """`self` está na assinatura mas não na chamada: o tipo não pode deslocar."""
    graph = build_graph(
        {
            "s.py": (
                "class A:\n"
                "    def alvo(self, nome: str, quantidade: int) -> None:\n"
                "        pass\n\n"
                "    def origem(self, quantidade: int) -> None:\n"
                "        nome = 'x'\n"
                "        self.alvo(nome, quantidade)\n"
            )
        }
    )

    tipos = {e.label: e.data_type for e in graph.edges if e.type == EdgeType.DATA_FLOW}
    assert tipos.get("nome") == "str", tipos
    assert tipos.get("quantidade") == "int", tipos


def test_complexidade_nao_colide_entre_classes():
    """Duas classes com método homônimo mantêm complexidades independentes."""
    graph = build_graph(
        {
            "c.py": (
                "class Simples:\n"
                "    def run(self):\n"
                "        return 1\n\n"
                "class Complexa:\n"
                "    def run(self, x):\n"
                "        if x:\n"
                "            for i in range(x):\n"
                "                if i:\n"
                "                    return i\n"
                "        return 0\n"
            )
        }
    )

    por_classe = {
        node.id.split("::")[2]: node.complexity
        for node in graph.nodes.values()
        if node.id.startswith("method::") and node.name == "run"
    }

    assert por_classe["Simples"] == 1, por_classe
    assert por_classe["Complexa"] > 1, por_classe
