"""
Parser de código Python usando AST (Abstract Syntax Tree).
Extrai funções, classes, imports e estrutura do código.
"""

import logging
from graphalyzer import config

import ast
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import inspect

logger = logging.getLogger(__name__)


# Os DTOs são compartilhados por todas as linguagens
from graphalyzer.analysis.languages.base import (
    ClassInfo,
    FileInfo,
    FunctionInfo,
    ImportInfo,
    Parameter,
)


class PythonParser:
    """Parser para arquivos Python."""

    def __init__(self):
        self.source_code: Optional[str] = None
        self.tree: Optional[ast.AST] = None

    def parse_file(self, file_path: str) -> Optional[FileInfo]:
        """Parse de um arquivo Python."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.source_code = f.read()
        except Exception as e:
            logger.error(f"Erro ao ler arquivo {file_path}: {e}")
            return None

        try:
            self.tree = ast.parse(self.source_code)
        except SyntaxError as e:
            logger.error(f"Erro de sintaxe em {file_path}: {e}")
            return None

        module_name = self._get_module_name(file_path)
        docstring = ast.get_docstring(self.tree)

        imports = self._extract_imports()
        functions = self._extract_functions()
        classes = self._extract_classes()

        return FileInfo(
            file_path=file_path,
            module_name=module_name,
            docstring=docstring,
            imports=imports,
            functions=functions,
            classes=classes,
            source_code=self.source_code,
        )

    def _get_module_name(self, file_path: str) -> str:
        """Obtém o nome do módulo a partir do caminho do arquivo."""
        path = Path(file_path)
        if path.name == "__init__.py":
            return path.parent.name
        return path.stem

    def _extract_imports(self) -> List[ImportInfo]:
        """Extrai todos os imports do arquivo."""
        imports = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            names=[(alias.name, alias.asname)],
                            line_number=node.lineno,
                            is_from_import=False,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                names = [(alias.name, alias.asname) for alias in node.names]
                imports.append(
                    ImportInfo(
                        module=node.module or "",
                        names=names,
                        line_number=node.lineno,
                        is_from_import=True,
                        level=node.level,
                    )
                )

        return imports

    def _extract_functions(self) -> List[FunctionInfo]:
        """Extrai funções de nível superior."""
        functions = []

        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_info = self._parse_function(node)
                functions.append(func_info)

        return functions

    def _extract_classes(self) -> List[ClassInfo]:
        """Extrai classes do arquivo."""
        classes = []

        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                classes.append(class_info)

        return classes

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Parse de uma função."""
        docstring = ast.get_docstring(node)
        source_code = self._get_source(node)

        parameters = self._parse_parameters(node.args)

        # Extrair tipo de retorno
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Extrair decoradores
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        is_async = isinstance(node, ast.AsyncFunctionDef)

        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=docstring,
            source_code=source_code,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async,
            is_private=node.name.startswith("_"),
        )

    def _get_source(self, node: ast.AST) -> str:
        """Recorta o código-fonte de um nó, já sem a indentação do escopo.

        `textwrap.dedent` não serve aqui: uma função que contém string multilinha
        começando na coluna 0 faz a indentação comum virar zero, e o recorte sai
        indentado — `ast.parse` daquele trecho estoura IndentationError. A
        indentação do escopo é a da primeira linha do nó, então é essa que sai.
        """
        segment = ast.get_source_segment(self.source_code, node, padded=True)
        if segment is None:  # sem posição confiável: devolve o recorte por linhas
            lines = self.source_code.split("\n")
            segment = "\n".join(lines[node.lineno - 1 : node.end_lineno])

        first_line = segment.split("\n", 1)[0]
        indent = first_line[: len(first_line) - len(first_line.lstrip())]
        if not indent:
            return segment

        return "\n".join(
            line[len(indent) :] if line.startswith(indent) else line
            for line in segment.split("\n")
        )

    @staticmethod
    def _parse_parameters(
        args: ast.arguments,
    ) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """Extrai todos os parâmetros: posicionais, *args, keyword-only e **kwargs."""

        def annotate(arg: ast.arg) -> Optional[str]:
            return ast.unparse(arg.annotation) if arg.annotation else None

        # defaults alinham à direita de (posonlyargs + args)
        positional = list(args.posonlyargs) + list(args.args)
        defaults: List[Optional[str]] = [None] * (
            len(positional) - len(args.defaults)
        ) + [ast.unparse(d) for d in args.defaults]

        parameters = [
            (arg.arg, annotate(arg), default)
            for arg, default in zip(positional, defaults)
        ]

        if args.vararg:
            parameters.append((f"*{args.vararg.arg}", annotate(args.vararg), None))

        # kw_defaults alinha 1:1 com kwonlyargs (None = sem default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            parameters.append(
                (arg.arg, annotate(arg), ast.unparse(default) if default else None)
            )

        if args.kwarg:
            parameters.append((f"**{args.kwarg.arg}", annotate(args.kwarg), None))

        return parameters

    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse de uma classe."""
        docstring = ast.get_docstring(node)
        source_code = self._get_source(node)

        # Extrair classes base
        base_classes = [ast.unparse(base) for base in node.bases]

        # Extrair métodos
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_info = self._parse_function(item)
                method_info.is_method = True
                methods.append(method_info)

        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=docstring,
            source_code=source_code,
            base_classes=base_classes,
            methods=methods,
            is_private=node.name.startswith("_"),
        )


class ProjectParser:
    """Percorre um projeto e analisa cada arquivo com a linguagem certa."""

    def __init__(self, project_path: str, exclude_dirs: Optional[List[str]] = None):
        self.project_path = project_path
        self.exclude_dirs = exclude_dirs or list(config.EXCLUDE_DIRS)
        self.files: Dict[str, FileInfo] = {}
        self.languages: Dict[str, int] = {}  # linguagem -> nº de arquivos

    def parse_project(self) -> Dict[str, FileInfo]:
        """Analisa todos os arquivos de linguagem suportada."""
        from graphalyzer.analysis.languages import analyzer_for

        for file_path in self._find_source_files():
            analyzer = analyzer_for(file_path)
            if analyzer is None:
                continue

            try:
                file_info = analyzer.parse_file(file_path)
            except Exception as exc:
                # Um arquivo problemático não pode derrubar a análise inteira
                logger.warning("Falha ao analisar %s: %s", file_path, exc)
                continue

            if file_info:
                self.files[file_path] = file_info
                self.languages[file_info.language] = (
                    self.languages.get(file_info.language, 0) + 1
                )

        return self.files

    def _find_source_files(self) -> List[str]:
        """Arquivos de código das linguagens suportadas."""
        from graphalyzer.analysis.languages import supported_extensions

        extensoes = tuple(supported_extensions())
        encontrados = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if file.endswith(extensoes):
                    encontrados.append(os.path.join(root, file))

        return sorted(encontrados)

    def get_statistics(self) -> Dict:
        """Retorna estatísticas do projeto."""
        total_files = len(self.files)
        total_functions = sum(len(f.functions) for f in self.files.values())
        total_classes = sum(len(f.classes) for f in self.files.values())
        total_lines = sum(len(f.source_code.split("\n")) for f in self.files.values())

        return {
            "total_files": total_files,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_lines": total_lines,
        }
