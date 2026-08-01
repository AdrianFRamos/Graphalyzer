"""Registro de linguagens suportadas.

Uma linguagem entra pelo `specs.py`; Python é a exceção deliberada — usa o
`ast` da stdlib, que resolve escopo e tipos melhor que uma gramática genérica.
"""

from pathlib import Path
from typing import Dict, List, Optional

from graphalyzer.analysis.languages.base import (
    CallInfo,
    ClassInfo,
    FileInfo,
    FunctionInfo,
    ImportInfo,
    LanguageAnalyzer,
    Parameter,
)
from graphalyzer.analysis.languages.specs import EXTENSION_MAP, SPECS, LanguageSpec

__all__ = [
    "CallInfo",
    "ClassInfo",
    "FileInfo",
    "FunctionInfo",
    "ImportInfo",
    "LanguageAnalyzer",
    "LanguageSpec",
    "Parameter",
    "analyzer_for",
    "supported_extensions",
    "supported_languages",
]

_CACHE: Dict[str, LanguageAnalyzer] = {}


def analyzer_for(file_path: str) -> Optional[LanguageAnalyzer]:
    """Analisador da linguagem do arquivo, ou None se não for suportada."""
    extensao = Path(file_path).suffix.lower()

    if extensao in _CACHE:
        return _CACHE[extensao]

    if extensao == ".py":
        from graphalyzer.analysis.python_ast import PythonAnalyzer

        _CACHE[extensao] = PythonAnalyzer()
        return _CACHE[extensao]

    spec = EXTENSION_MAP.get(extensao)
    if spec is None:
        return None

    try:
        from graphalyzer.analysis.languages.generic import GenericAnalyzer

        _CACHE[extensao] = GenericAnalyzer(spec)
    except ImportError:
        # tree-sitter é opcional: sem ele o sistema segue analisando Python
        return None

    return _CACHE[extensao]


def supported_extensions() -> List[str]:
    """Todas as extensões que o analisador reconhece."""
    return sorted({".py", *EXTENSION_MAP})


def supported_languages() -> Dict[str, List[str]]:
    """Mapa de linguagem legível -> extensões."""
    linguagens = {"Python": [".py"]}
    for spec in SPECS.values():
        linguagens[spec.label] = list(spec.extensions)
    return linguagens
