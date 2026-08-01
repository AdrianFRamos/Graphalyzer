"""Testes do parser AST."""

import ast
import tempfile

from conftest import build_graph

from graphalyzer.analysis.parser import PythonParser


def test_captura_todos_os_parametros():
    """*args, keyword-only e **kwargs também são variáveis de entrada."""
    source = "def f(a, b=1, *args, c: int = 2, d: str, **kwargs) -> None:\n    pass\n"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(source)
        tmp_path = tmp.name

    info = PythonParser().parse_file(tmp_path)
    parametros = info.functions[0].parameters

    assert [p[0] for p in parametros] == ["a", "b", "*args", "c", "d", "**kwargs"]

    defaults = {p[0]: p[2] for p in parametros}
    assert defaults["b"] == "1" and defaults["c"] == "2", defaults
    assert defaults["a"] is None and defaults["d"] is None, defaults


def test_fonte_com_string_multilinha_na_coluna_zero():
    """Recorte de fonte precisa sobreviver a string multilinha sem indentação.

    `textwrap.dedent` zerava a indentação comum nesses casos e o trecho saía
    indentado, estourando IndentationError ao ser reparseado.
    """
    graph = build_graph(
        {
            "p.py": (
                "class Gerador:\n"
                "    def prompt(self, nome: str) -> str:\n"
                '        texto = f"""\n'
                "Linha na coluna zero\n"
                "Outra linha: {nome}\n"
                '"""\n'
                "        return texto\n"
            )
        }
    )

    node = next(n for n in graph.nodes.values() if n.name == "prompt")
    assert node.source_code.startswith("def prompt"), repr(node.source_code[:40])

    ast.parse(node.source_code)  # não pode estourar IndentationError
