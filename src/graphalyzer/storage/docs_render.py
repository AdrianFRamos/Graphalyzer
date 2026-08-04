"""Renderizadores da documentação: Markdown e PDF.

Ambos consomem o mesmo `DocumentoDeArquivo`, então o conteúdo é idêntico e só
a apresentação muda. Emoji aparece no Markdown e não no PDF: as fontes-padrão
do PDF não têm esses glifos, e um quadrado vazio é pior que um título limpo.
"""

import logging
import re
from pathlib import Path
from typing import List

from graphalyzer.domain.models import ProjectGraph
from graphalyzer.storage.docs import ConstrutorDeDocumentacao, DocumentoDeArquivo

logger = logging.getLogger(__name__)

SECOES = [
    ("inputs", "Inputs (Entradas)", "📥"),
    ("processamento", "Processamento (Lógica / Entidades)", "⚙️"),
    ("outputs", "Outputs (Saídas)", "📤"),
    ("relacionamentos", "Relacionamentos Lógicos", "🔗"),
    ("notas", "Notas de Implementação", "📝"),
]


def _nome_de_arquivo(nome: str) -> str:
    """Nome seguro para o sistema de arquivos, preservando a extensão original."""
    return re.sub(r'[<>:"/\\|?*]', "_", nome)


class MarkdownDocsExporter:
    """Um arquivo Markdown por arquivo de código, mais um índice.

    Os links são Markdown padrão (`[nome](nome.md)`), que funcionam em
    qualquer visualizador — inclusive no Obsidian, sem depender dele.
    """

    def __init__(self, graph: ProjectGraph):
        self.graph = graph
        self.construtor = ConstrutorDeDocumentacao(graph)

    def export(self, output_path: str) -> None:
        destino = Path(output_path)
        destino.mkdir(parents=True, exist_ok=True)

        documentos = self.construtor.documentos()
        usados = set()

        for doc in documentos:
            base = _nome_de_arquivo(doc.nome)
            # Mesmo nome em pastas diferentes: sem desempate, um sobrescreve
            # o outro e o índice passa a apontar para o arquivo errado.
            if base in usados:
                base = f"{base} ({_nome_de_arquivo(doc.camada).replace('/', '-')})"
            usados.add(base)
            doc._arquivo = f"{base}.md"

        indice = {d.nome: d._arquivo for d in documentos}

        for doc in documentos:
            (destino / doc._arquivo).write_text(
                self.render(doc, indice), encoding="utf-8"
            )

        (destino / "00_indice.md").write_text(
            self._indice(documentos), encoding="utf-8"
        )
        logger.info("✓ Documentação Markdown: %d arquivos em %s", len(documentos), destino)

    def render(self, doc: DocumentoDeArquivo, indice: dict = None) -> str:
        indice = indice or {}
        linhas = [
            "---",
            "tipo: arquivo-codigo",
            f"camada: {doc.camada}",
            "status: documentado",
            f"projeto: {self.graph.project_name}",
            f"linguagem: {doc.linguagem}",
            f"tags: [{doc.tag}]",
            "---",
            "",
            f"# 📄 {doc.nome}",
            f"**Responsabilidade**: {doc.responsabilidade}",
            "",
            "---",
            "",
            "## 📥 Inputs (Entradas)",
        ]
        # Sem linha em branco entre itens: mantém o documento compacto
        linhas += [f"- {item}" for item in doc.inputs]

        linhas += ["", "---", "", "## ⚙️ Processamento (Lógica / Entidades)"]
        for i, (categoria, subitens) in enumerate(doc.processamento, 1):
            linhas.append(f"{i}. {categoria}:")
            linhas += [f"     - {sub}" for sub in subitens]

        linhas += ["", "---", "", "## 📤 Outputs (Saídas)"]
        linhas += [f"- {item}" for item in doc.outputs]

        linhas += ["", "---", "", "## 🔗 Relacionamentos Lógicos"]
        for item in doc.relacionamentos:
            alvo = indice.get(item)
            linhas.append(f"- [{item}]({alvo})" if alvo else f"- {item}")

        linhas += ["", "---", "", "## 📝 Notas de Implementação"]
        linhas += [f"- {item}" for item in doc.notas]

        return "\n".join(linhas) + "\n"

    def _indice(self, documentos: List[DocumentoDeArquivo]) -> str:
        por_camada = {}
        for doc in documentos:
            por_camada.setdefault(doc.camada, []).append(doc)

        linhas = [
            "---",
            "tipo: documento",
            f"projeto: {self.graph.project_name}",
            "status: documentado",
            "tags: [documentacao]",
            "---",
            "",
            f"# 📚 {self.graph.project_name}",
            f"**Responsabilidade**: Índice da documentação extraída de "
            f"{len(documentos)} arquivos.",
            "",
            "---",
            "",
        ]

        for camada in sorted(por_camada):
            linhas.append(f"## {camada}")
            for doc in sorted(por_camada[camada], key=lambda d: d.nome):
                linhas.append(f"- [{doc.nome}]({doc._arquivo}) — {doc.responsabilidade}")
            linhas.append("")

        return "\n".join(linhas)


class PdfDocsExporter:
    """Documento PDF único, com capa, sumário e uma seção por arquivo."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph
        self.construtor = ConstrutorDeDocumentacao(graph)

    def export(self, output_path: str) -> None:
        try:
            from fpdf import FPDF
        except ImportError as exc:
            raise RuntimeError(
                "Exportar PDF requer fpdf2. Instale com: pip install 'graphalyzer[pdf]'"
            ) from exc

        documentos = self.construtor.documentos()
        pdf = self._montar(FPDF, documentos)
        pdf.output(output_path)
        logger.info("✓ Documentação PDF: %d arquivos em %s", len(documentos), output_path)

    # -- Montagem ----------------------------------------------------------

    def _montar(self, FPDF, documentos: List[DocumentoDeArquivo]):
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(18, 18, 18)

        self._capa(pdf, documentos)

        analise = self.construtor.analise_do_projeto()
        if analise:
            self._pagina_de_analise(pdf, analise)

        self._sumario(pdf, documentos)

        for doc in documentos:
            self._pagina(pdf, doc)

        return pdf

    @staticmethod
    def _txt(texto: str) -> str:
        """Reduz a texto que as fontes-padrão do PDF sabem desenhar.

        As fontes core cobrem Latin-1: acentuação do português passa, emoji e
        setas tipográficas não. Substituir é melhor que imprimir tofu.
        """
        trocas = {"→": "->", "—": "-", "–": "-", "≥": ">=", "≤": "<=", "…": "..."}
        for de, para in trocas.items():
            texto = texto.replace(de, para)
        return texto.encode("latin-1", "replace").decode("latin-1")

    def _centrado(self, pdf, altura: float, texto: str):
        """Linha centrada, sempre a partir da margem esquerda.

        `multi_cell` deixa o cursor onde o texto terminou; a chamada seguinte
        com largura 0 herdaria esse resto de linha e estouraria.
        """
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, altura, self._txt(texto), align="C")

    def _capa(self, pdf, documentos):
        pdf.add_page()
        pdf.ln(60)

        pdf.set_font("Helvetica", "B", 26)
        self._centrado(pdf, 12, "Documentação Técnica")

        pdf.set_font("Helvetica", "B", 18)
        self._centrado(pdf, 10, self.graph.project_name)

        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        self._centrado(
            pdf,
            7,
            f"{self.graph.file_count} arquivos - {self.graph.function_count} funções - "
            f"{self.graph.class_count} classes - {len(self.graph.edges)} relações",
        )

        if self.graph.analysis_timestamp:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(110)
            self._centrado(pdf, 6, f"Extraído em {self.graph.analysis_timestamp[:19]}")
            pdf.set_text_color(0)

    def _pagina_de_analise(self, pdf, analise: dict):
        """Visão geral da organização — só existe quando a IA foi usada."""
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        self._escrever(pdf, 9, "Visão Geral")
        pdf.ln(2)

        if analise.get("visao_geral"):
            pdf.set_font("Helvetica", "", 10)
            self._escrever(pdf, 5.5, analise["visao_geral"])
            pdf.ln(3)

        for titulo, chave in [
            ("Organização", "organizacao"),
            ("Pontos de atenção", "pontos_de_atencao"),
            ("Sugestões", "sugestoes"),
        ]:
            itens = analise.get(chave) or []
            if not itens:
                continue
            self._titulo(pdf, titulo)
            pdf.set_font("Helvetica", "", 9.5)
            for item in itens:
                self._escrever(pdf, 5, f"  - {item}")

    def _sumario(self, pdf, documentos):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        self._escrever(pdf, 9, "Sumário")
        pdf.ln(2)

        camada_atual = None
        for doc in documentos:
            if doc.camada != camada_atual:
                camada_atual = doc.camada
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(70)
                self._escrever(pdf, 6, camada_atual)
                pdf.set_text_color(0)

            pdf.set_font("Helvetica", "", 9)
            self._escrever(pdf, 5, f"   {doc.nome}")

    def _pagina(self, pdf, doc: DocumentoDeArquivo):
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 15)
        self._escrever(pdf, 9, doc.nome)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(110)
        self._escrever(pdf, 5, f"{doc.camada}  |  {doc.linguagem}  |  #{doc.tag}")
        pdf.set_text_color(0)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 10)
        self._escrever(pdf, 6, "Responsabilidade")
        pdf.set_font("Helvetica", "", 10)
        self._escrever(pdf, 5.5, doc.responsabilidade)
        pdf.ln(3)

        self._lista(pdf, "Inputs (Entradas)", doc.inputs)
        self._numerada(pdf, "Processamento (Lógica / Entidades)", doc.processamento)
        self._lista(pdf, "Outputs (Saídas)", doc.outputs)
        self._lista(pdf, "Relacionamentos Lógicos", doc.relacionamentos)
        self._lista(pdf, "Notas de Implementação", doc.notas)

    def _escrever(self, pdf, altura: float, texto: str):
        """Escreve um parágrafo sempre a partir da margem.

        `multi_cell(0, ...)` usa o espaço que sobra à direita do cursor: depois
        de uma célula preenchida esse espaço é zero e o fpdf estoura com
        "not enough horizontal space". Fixar x e largura remove a dependência
        da posição anterior.
        """
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, altura, self._txt(texto))

    def _titulo(self, pdf, texto: str):
        pdf.ln(2)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(238, 240, 245)
        pdf.cell(pdf.epw, 7, self._txt(f"  {texto}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def _lista(self, pdf, titulo: str, itens: List[str]):
        self._titulo(pdf, titulo)
        pdf.set_font("Courier", "", 8.5)
        for item in itens:
            self._escrever(pdf, 4.6, f"  - {item}")

    def _numerada(self, pdf, titulo: str, blocos):
        self._titulo(pdf, titulo)
        for i, (categoria, subitens) in enumerate(blocos, 1):
            pdf.set_font("Helvetica", "B", 9)
            self._escrever(pdf, 5, f"  {i}. {categoria}:")
            pdf.set_font("Courier", "", 8.5)
            for sub in subitens:
                self._escrever(pdf, 4.6, f"       - {sub}")
