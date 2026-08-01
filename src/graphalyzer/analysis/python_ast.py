"""Analisador de Python sobre o `ast` da stdlib.

Python continua fora do caminho genérico de propósito: o `ast` resolve escopo,
defaults e anotações com precisão que uma gramática genérica não alcança, e o
fluxo de dados detalhado (`data_flow.py`) depende dele.
"""

import logging
from typing import List, Optional

from graphalyzer.analysis.extractor import ComplexityAnalyzer, DependencyExtractor
from graphalyzer.analysis.languages.base import CallInfo, FileInfo, FunctionInfo
from graphalyzer.analysis.parser import PythonParser

logger = logging.getLogger(__name__)


class PythonAnalyzer:
    """Adapta o `PythonParser` ao contrato de linguagem."""

    language = "python"
    extensions = (".py",)

    def __init__(self) -> None:
        self._parser = PythonParser()

    def parse_file(self, file_path: str) -> Optional[FileInfo]:
        info = self._parser.parse_file(file_path)
        if info is None:
            return None

        # Complexidade por nome qualificado ("Classe.metodo"), calculada uma vez
        try:
            complexidades = ComplexityAnalyzer().analyze(info.source_code)
        except SyntaxError:
            complexidades = {}

        for função in info.functions:
            self._preencher(função, complexidades.get(função.name, 1))

        for classe in info.classes:
            for método in classe.methods:
                chave = f"{classe.name}.{método.name}"
                self._preencher(método, complexidades.get(chave, 1))

        info.language = "python"
        return info

    def _preencher(self, função: FunctionInfo, complexidade: int) -> None:
        função.complexity = complexidade
        função.calls = self._chamadas(função)

    @staticmethod
    def _chamadas(função: FunctionInfo) -> List[CallInfo]:
        try:
            chamadas, _ = DependencyExtractor(função.source_code).extract()
        except SyntaxError:
            # Recorte de função isolada nem sempre reparseia (decorators
            # exóticos, sintaxe nova): perde-se essa função, não a análise.
            return []

        return [
            CallInfo(
                callee=chamada.callee,
                line_number=chamada.line_number,
                arguments=chamada.arguments,
            )
            for chamada in chamadas
        ]

    def extract_calls(self, função: FunctionInfo) -> List[CallInfo]:
        return função.calls

    def complexity(self, função: FunctionInfo) -> int:
        return função.complexity
