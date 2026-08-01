"""Testes das linguagens além de Python.

O grafo tem que sair igual em qualquer linguagem: mesmas arestas, mesmos
tipos de parâmetro, mesmo fluxo de dados. O que muda é só a gramática.
"""

import pytest

from conftest import build_graph

from graphalyzer.analysis.languages import analyzer_for, supported_languages
from graphalyzer.domain.models import EdgeType

# Mesmo programa nas quatro linguagens: uma classe cujo método chama duas
# funções livres, passando variáveis. O grafo esperado é idêntico.
PROGRAMAS = {
    "dart": {
        "calc.dart": (
            "double somar(List<Item> itens) => 0.0;\n"
            "double aplicar(double valor, double taxa) => valor * taxa;\n"
        ),
        "pedido.dart": (
            "import 'calc.dart';\n\n"
            "class Pedido {\n"
            "  double calcularTotal(List<Item> itens, double desconto) {\n"
            "    double bruto = somar(itens);\n"
            "    return aplicar(bruto, desconto);\n"
            "  }\n"
            "}\n"
        ),
    },
    "typescript": {
        "calc.ts": (
            "export function somar(itens: Item[]): number { return 0; }\n"
            "export function aplicar(valor: number, taxa: number): number { return valor; }\n"
        ),
        "pedido.ts": (
            "import { somar, aplicar } from './calc';\n\n"
            "export class Pedido {\n"
            "  calcularTotal(itens: Item[], desconto: number): number {\n"
            "    const bruto = somar(itens);\n"
            "    return aplicar(bruto, desconto);\n"
            "  }\n"
            "}\n"
        ),
    },
    "go": {
        "calc.go": (
            "package main\n"
            "func Somar(itens []Item) float64 { return 0 }\n"
            "func Aplicar(valor float64, taxa float64) float64 { return valor }\n"
        ),
        "pedido.go": (
            "package main\n"
            "type Pedido struct{}\n"
            "func (p *Pedido) CalcularTotal(itens []Item, desconto float64) float64 {\n"
            "    bruto := Somar(itens)\n"
            "    return Aplicar(bruto, desconto)\n"
            "}\n"
        ),
    },
    "java": {
        "Calc.java": (
            "public class Calc {\n"
            "  public static double somar(java.util.List<Item> itens) { return 0; }\n"
            "  public static double aplicar(double valor, double taxa) { return valor; }\n"
            "}\n"
        ),
        "Pedido.java": (
            "public class Pedido {\n"
            "  public double calcularTotal(java.util.List<Item> itens, double desconto) {\n"
            "    double bruto = somar(itens);\n"
            "    return aplicar(bruto, desconto);\n"
            "  }\n"
            "}\n"
        ),
    },
}


@pytest.mark.parametrize("linguagem", sorted(PROGRAMAS))
def test_chamadas_e_fluxo_em_cada_linguagem(linguagem):
    """Cada linguagem produz chamadas e fluxo de dados com nome de variável."""
    graph = build_graph(PROGRAMAS[linguagem])

    chamadas = {
        graph.nodes[e.target_id].name.lower()
        for e in graph.edges
        if e.type == EdgeType.CALLS
    }
    assert {"somar", "aplicar"} <= chamadas, chamadas

    fluxos = [e for e in graph.edges if e.type == EdgeType.DATA_FLOW]
    assert fluxos, f"{linguagem}: nenhum fluxo de dados"

    variaveis = {e.label for e in fluxos}
    assert {"bruto", "desconto"} <= variaveis, variaveis


@pytest.mark.parametrize("linguagem", sorted(PROGRAMAS))
def test_nenhuma_aresta_pendente_em_cada_linguagem(linguagem):
    """O invariante do grafo vale para toda linguagem, não só Python."""
    graph = build_graph(PROGRAMAS[linguagem])

    for edge in graph.edges:
        assert edge.source_id in graph.nodes
        assert edge.target_id in graph.nodes


def test_tipos_de_parametro_do_dart():
    """Tipos genéricos precisam sair inteiros, não só o parâmetro de tipo."""
    graph = build_graph(PROGRAMAS["dart"])

    metodo = next(n for n in graph.nodes.values() if n.name == "calcularTotal")
    tipos = {p.name: p.type_hint for p in metodo.parameters}

    assert tipos["itens"] == "List<Item>", tipos
    assert tipos["desconto"] == "double", tipos


def test_import_dart_resolve_package_e_relativo():
    """`package:` e caminho relativo apontam para o arquivo certo do projeto."""
    graph = build_graph(
        {
            "lib/modelos.dart": "class Item { final String nome; Item(this.nome); }\n",
            "lib/servicos/calculo.dart": (
                "import '../modelos.dart';\n"
                "double somar(List<Item> itens) => 0.0;\n"
            ),
            "lib/pedido.dart": (
                "import 'package:demo/servicos/calculo.dart';\n"
                "class Pedido {\n"
                "  double total(List<Item> itens) => somar(itens);\n"
                "}\n"
            ),
        }
    )

    imports = {
        (graph.nodes[e.source_id].name, graph.nodes[e.target_id].name)
        for e in graph.edges
        if e.type == EdgeType.IMPORT
    }

    assert ("pedido", "calculo") in imports, imports  # package:
    assert ("calculo", "modelos") in imports, imports  # relativo


def test_projeto_misto_analisa_todas_as_linguagens():
    """Um repositório com várias linguagens entra inteiro no mesmo grafo."""
    graph = build_graph(
        {
            "backend/api.py": "def servir(porta: int) -> None:\n    pass\n",
            "app/lib/main.dart": "void main() { }\n",
            "web/index.ts": "export function iniciar(): void {}\n",
            "infra/main.go": "package main\nfunc main() {}\n",
            "README.md": "não é código, deve ser ignorado\n",
        }
    )

    arquivos = {
        n.name for n in graph.nodes.values() if n.type.value == "file"
    }
    assert {"api", "main", "index"} <= arquivos, arquivos
    assert "README" not in arquivos


def test_extensao_desconhecida_nao_quebra():
    """Arquivo de linguagem não suportada é ignorado, não derruba a análise."""
    assert analyzer_for("qualquer.xyz") is None
    assert analyzer_for("modulo.py") is not None
    assert analyzer_for("app.dart") is not None


def test_linguagens_anunciadas_tem_analisador():
    """Toda linguagem listada precisa realmente carregar."""
    for label, extensoes in supported_languages().items():
        assert analyzer_for(f"exemplo{extensoes[0]}") is not None, label
