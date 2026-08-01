"""Testes da própria arquitetura.

As regras de camada só valem se forem verificáveis: sem isto, o primeiro
import na direção errada passa despercebido e a separação apodrece.
"""

import ast
import pathlib

import pytest

PACOTE = pathlib.Path(__file__).resolve().parent.parent / "src" / "graphalyzer"

# Cada camada só pode importar de nível estritamente menor (ou igual, dentro de si)
NIVEL = {
    "config": 0,
    "console": 0,
    "domain": 1,
    "analysis": 2,
    "ai": 2,
    "storage": 2,
    "plugins": 2,
    "services": 3,
    "api": 4,
    "cli": 4,
    "server": 4,
}


def _modulos():
    """Cada arquivo do pacote com a camada a que pertence."""
    for path in sorted(PACOTE.rglob("*.py")):
        partes = path.relative_to(PACOTE).parts
        camada = partes[0] if len(partes) > 1 else path.stem
        if camada in NIVEL:
            yield camada, path


def test_camadas_nao_importam_para_fora():
    """Nenhuma camada importa de uma camada mais externa."""
    violacoes = []

    for camada, path in _modulos():
        arvore = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(arvore):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not (node.module or "").startswith("graphalyzer"):
                continue

            alvo = (node.module.split(".") + [""])[1]
            if alvo in NIVEL and NIVEL[alvo] > NIVEL[camada]:
                violacoes.append(f"{path.name}: {camada} importa {alvo}")

    assert not violacoes, "camadas invertidas:\n" + "\n".join(violacoes)


def test_dominio_nao_depende_de_ninguem():
    """`domain` é o núcleo: não importa nenhuma outra camada do projeto."""
    for camada, path in _modulos():
        if camada != "domain":
            continue

        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "graphalyzer."
            ):
                alvo = node.module.split(".")[1]
                assert alvo == "domain", f"{path.name} importa {node.module}"


@pytest.mark.parametrize(
    "camada", ["domain", "analysis", "ai", "storage", "plugins", "services"]
)
def test_camadas_internas_nao_escrevem_em_stdout(camada):
    """Só os entry points imprimem; o resto usa logging.

    Biblioteca que dá print quebra quem consome a API e derruba a execução em
    console cp1252 no Windows.
    """
    culpados = []

    for atual, path in _modulos():
        if atual != camada:
            continue

        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                culpados.append(f"{path.name}:{node.lineno}")

    assert not culpados, f"print() em {camada}: {', '.join(culpados)}"
