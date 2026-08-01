"""Contratos da camada de linguagens.

As estruturas aqui são neutras: o resto do sistema (grafo, exportadores,
métricas) só conhece funções, classes, parâmetros e imports — nunca a sintaxe
de onde vieram. É o que permite somar linguagens sem tocar nas outras camadas.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Tuple

# (nome, tipo, valor padrão)
Parameter = Tuple[str, Optional[str], Optional[str]]


@dataclass
class CallInfo:
    """Uma chamada encontrada dentro de uma função."""

    callee: str
    line_number: int
    arguments: List[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Uma função ou método."""

    name: str
    line_number: int
    docstring: Optional[str]
    source_code: str
    parameters: List[Parameter]
    return_type: Optional[str]
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    is_private: bool = False

    # Preenchidos durante o parse. Reanalisar o trecho recortado da função
    # depois produzia falso positivo — fora do contexto da classe, a própria
    # assinatura `metodo(a, b)` volta a parsear como se fosse uma chamada.
    calls: List["CallInfo"] = field(default_factory=list)
    complexity: int = 1


@dataclass
class ClassInfo:
    """Uma classe, struct ou tipo equivalente."""

    name: str
    line_number: int
    docstring: Optional[str]
    source_code: str
    base_classes: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    is_private: bool = False


@dataclass
class ImportInfo:
    """Uma dependência declarada de outro módulo/arquivo."""

    module: str
    names: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    line_number: int = 0
    is_from_import: bool = False
    level: int = 0  # import relativo em Python (0 = absoluto, 1 = ".", 2 = "..")
    # Caminho literal do import ("./utils", "package:app/x.dart"), quando a
    # linguagem usa caminho de arquivo em vez de nome de módulo pontilhado.
    path: Optional[str] = None


@dataclass
class FileInfo:
    """Um arquivo já analisado, independente da linguagem."""

    file_path: str
    module_name: str
    docstring: Optional[str]
    imports: List[ImportInfo]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    source_code: str
    language: str = "python"


class LanguageAnalyzer(Protocol):
    """O que uma linguagem precisa saber fazer para entrar no grafo."""

    language: str
    extensions: Tuple[str, ...]

    def parse_file(self, file_path: str) -> Optional[FileInfo]:
        """Analisa um arquivo. Devolve None se não for possível."""
        ...

    def extract_calls(self, function: FunctionInfo) -> List[CallInfo]:
        """Chamadas feitas dentro de uma função, com os argumentos."""
        ...

    def complexity(self, function: FunctionInfo) -> int:
        """Complexidade ciclomática da função."""
        ...
