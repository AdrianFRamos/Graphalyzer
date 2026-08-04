"""Testes da geração de documentação.

O documento é o produto final da extração: se ele inventar conteúdo ou perder
seção, o valor da ferramenta se perde sem ninguém notar.
"""

import re

import pytest

from conftest import build_graph

from graphalyzer.storage.docs import ConstrutorDeDocumentacao
from graphalyzer.storage.docs_render import MarkdownDocsExporter, PdfDocsExporter

FONTE = {
    "servicos/calculo.py": (
        '"""Cálculo de totais do pedido. Detalhe extra que não deve entrar."""\n'
        "import json\n\n"
        "def somar(itens: list, taxa: float) -> float:\n"
        '    """Soma os itens."""\n'
        "    if taxa > 0:\n"
        "        return 1.0\n"
        "    return 0.0\n"
    ),
    "pedido.py": (
        "from servicos.calculo import somar\n\n"
        "class Pedido:\n"
        "    def total(self, itens: list, taxa: float) -> float:\n"
        "        return somar(itens, taxa)\n"
    ),
}


@pytest.fixture
def documentos():
    graph = build_graph(FONTE)
    return {d.nome: d for d in ConstrutorDeDocumentacao(graph).documentos()}


def test_um_documento_por_arquivo(documentos):
    assert set(documentos) == {"calculo.py", "pedido.py"}


def test_responsabilidade_vem_da_docstring(documentos):
    """Primeira frase da docstring do módulo, não o texto inteiro."""
    doc = documentos["calculo.py"]
    assert doc.responsabilidade == "Cálculo de totais do pedido."


def test_responsabilidade_sem_docstring_descreve_a_estrutura(documentos):
    """Sem docstring, descreve o que foi extraído — nunca inventa propósito."""
    doc = documentos["pedido.py"]
    assert "classe" in doc.responsabilidade.lower()


def test_inputs_trazem_imports_e_parametros(documentos):
    doc = documentos["calculo.py"]
    texto = " | ".join(doc.inputs)

    assert "json" in texto
    assert "itens: list" in texto and "taxa: float" in texto


def test_processamento_numerado_com_subitens(documentos):
    """A seção é lista numerada de categorias, cada uma com seus subitens."""
    doc = documentos["pedido.py"]
    categorias = [c for c, _ in doc.processamento]

    assert any("Pedido" in c for c in categorias)
    subitens = [s for _, subs in doc.processamento for s in subs]
    assert any("total(" in s for s in subitens)
    assert any("complexidade" in s for s in subitens)


def test_outputs_trazem_tipo_de_retorno(documentos):
    assert any("float" in item for item in documentos["calculo.py"].outputs)


def test_relacionamentos_apontam_para_o_arquivo_relacionado(documentos):
    """`pedido.py` importa `calculo.py`: a relação tem que aparecer nos dois."""
    assert "calculo.py" in documentos["pedido.py"].relacionamentos
    assert "pedido.py" in documentos["calculo.py"].relacionamentos


def test_notas_trazem_metricas_extraidas(documentos):
    texto = " ".join(documentos["calculo.py"].notas)
    assert "omplexidade" in texto and "ocstring" in texto


def test_markdown_tem_todas_as_secoes(tmp_path):
    graph = build_graph(FONTE)
    MarkdownDocsExporter(graph).export(str(tmp_path / "docs"))

    nota = (tmp_path / "docs" / "calculo.py.md").read_text(encoding="utf-8")

    for secao in ("Inputs", "Processamento", "Outputs", "Relacionamentos", "Notas"):
        assert secao in nota, secao

    assert nota.startswith("---\n"), "sem frontmatter"
    assert "linguagem: python" in nota
    assert (tmp_path / "docs" / "00_indice.md").is_file()


def test_markdown_nao_deixa_linha_em_branco_entre_itens(tmp_path):
    """Regra de formatação: a lista fica compacta."""
    graph = build_graph(FONTE)
    MarkdownDocsExporter(graph).export(str(tmp_path / "docs"))

    nota = (tmp_path / "docs" / "calculo.py.md").read_text(encoding="utf-8")
    assert not re.search(r"^- .*\n\n- ", nota, re.MULTILINE)


def test_markdown_liga_os_arquivos(tmp_path):
    """O link tem que apontar para uma nota que existe de verdade."""
    graph = build_graph(FONTE)
    destino = tmp_path / "docs"
    MarkdownDocsExporter(graph).export(str(destino))

    nota = (destino / "pedido.py.md").read_text(encoding="utf-8")
    alvos = re.findall(r"\]\(([^)]+\.md)\)", nota)

    assert alvos, "nenhum link gerado"
    for alvo in alvos:
        assert (destino / alvo).is_file(), alvo


def test_pdf_gera_arquivo_valido(tmp_path):
    graph = build_graph(FONTE)
    destino = tmp_path / "doc.pdf"
    PdfDocsExporter(graph).export(str(destino))

    dados = destino.read_bytes()
    assert dados.startswith(b"%PDF-")

    # Capa + sumário + uma página por arquivo
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", dados))
    assert paginas >= 4, paginas


def test_pdf_sobrevive_a_acento_e_simbolo(tmp_path):
    """Fonte-padrão do PDF é Latin-1: emoji e setas precisam ser convertidos."""
    graph = build_graph(
        {
            "acao.py": (
                '"""Ação de configuração — inclui símbolos → e ✓."""\n'
                "def executar(operação: str) -> None:\n"
                "    pass\n"
            )
        }
    )

    destino = tmp_path / "doc.pdf"
    PdfDocsExporter(graph).export(str(destino))  # não pode estourar
    assert destino.read_bytes().startswith(b"%PDF-")
