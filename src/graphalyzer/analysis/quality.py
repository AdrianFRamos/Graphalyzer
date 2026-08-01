"""
Analisador de qualidade de código.
Identifica problemas, padrões e oportunidades de melhoria.
"""

import ast
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    """Severidade de problemas."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CodeIssue:
    """Representa um problema de código."""
    function_name: str
    line_number: int
    severity: IssueSeverity
    issue_type: str
    message: str
    suggestion: Optional[str] = None


class QualityAnalyzer(ast.NodeVisitor):
    """Analisa qualidade de código."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.issues: List[CodeIssue] = []
        self.current_function: Optional[str] = None
        self.function_lines: Dict[str, Tuple[int, int]] = {}

    def analyze(self) -> List[CodeIssue]:
        """Analisa qualidade."""
        # Primeira passagem: coletar funções
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.function_lines[node.name] = (node.lineno, node.end_lineno or node.lineno)

        # Segunda passagem: analisar
        self.visit(self.tree)

        return self.issues

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        self.current_function = node.name

        self._check_function_quality(node)

        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visita definição de função assíncrona."""
        self.visit_FunctionDef(node)

    def _check_function_quality(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Verifica qualidade de uma função."""
        # Verificar docstring
        if not ast.get_docstring(node):
            self.issues.append(
                CodeIssue(
                    function_name=node.name,
                    line_number=node.lineno,
                    severity=IssueSeverity.WARNING,
                    issue_type="missing_docstring",
                    message=f"Função '{node.name}' sem docstring",
                    suggestion="Adicione uma docstring descrevendo a função",
                )
            )

        # Verificar type hints
        missing_hints = []
        for arg in node.args.args:
            if not arg.annotation:
                missing_hints.append(arg.arg)

        if missing_hints:
            self.issues.append(
                CodeIssue(
                    function_name=node.name,
                    line_number=node.lineno,
                    severity=IssueSeverity.INFO,
                    issue_type="missing_type_hints",
                    message=f"Parâmetros sem type hints: {', '.join(missing_hints)}",
                    suggestion="Adicione type hints para melhor documentação",
                )
            )

        # Verificar tipo de retorno
        if not node.returns:
            self.issues.append(
                CodeIssue(
                    function_name=node.name,
                    line_number=node.lineno,
                    severity=IssueSeverity.INFO,
                    issue_type="missing_return_type",
                    message=f"Função '{node.name}' sem type hint de retorno",
                    suggestion="Adicione type hint de retorno",
                )
            )

        # Verificar comprimento da função
        func_length = (node.end_lineno or node.lineno) - node.lineno
        if func_length > 50:
            self.issues.append(
                CodeIssue(
                    function_name=node.name,
                    line_number=node.lineno,
                    severity=IssueSeverity.WARNING,
                    issue_type="long_function",
                    message=f"Função muito longa ({func_length} linhas)",
                    suggestion="Considere dividir em funções menores",
                )
            )

        # Verificar número de parâmetros
        num_params = len(node.args.args)
        if num_params > 5:
            self.issues.append(
                CodeIssue(
                    function_name=node.name,
                    line_number=node.lineno,
                    severity=IssueSeverity.WARNING,
                    issue_type="too_many_parameters",
                    message=f"Função com muitos parâmetros ({num_params})",
                    suggestion="Considere usar um objeto ou dicionário",
                )
            )

    def visit_If(self, node: ast.If) -> None:
        """Verifica estruturas if."""
        self._check_nested_depth(node)
        self.generic_visit(node)

    def _check_nested_depth(self, node: ast.AST, depth: int = 0) -> None:
        """Verifica profundidade de aninhamento."""
        if depth > 3:
            if self.current_function:
                self.issues.append(
                    CodeIssue(
                        function_name=self.current_function,
                        line_number=getattr(node, "lineno", 0),
                        severity=IssueSeverity.WARNING,
                        issue_type="deep_nesting",
                        message=f"Aninhamento profundo (nível {depth})",
                        suggestion="Considere refatorar para reduzir aninhamento",
                    )
                )

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While)):
                self._check_nested_depth(child, depth + 1)


class SecurityAnalyzer(ast.NodeVisitor):
    """Analisa problemas de segurança."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.issues: List[CodeIssue] = []
        self.current_function: Optional[str] = None

    def analyze(self) -> List[CodeIssue]:
        """Analisa segurança."""
        self.visit(self.tree)
        return self.issues

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call) -> None:
        """Verifica chamadas perigosas."""
        func_name = self._get_function_name(node.func)

        # Verificar eval/exec
        if func_name in ("eval", "exec", "compile"):
            self.issues.append(
                CodeIssue(
                    function_name=self.current_function or "unknown",
                    line_number=node.lineno,
                    severity=IssueSeverity.ERROR,
                    issue_type="dangerous_function",
                    message=f"Uso de função perigosa: {func_name}",
                    suggestion=f"Evite usar {func_name}. Use alternativas seguras.",
                )
            )

        # Verificar pickle
        if func_name in ("pickle.loads", "pickle.load"):
            self.issues.append(
                CodeIssue(
                    function_name=self.current_function or "unknown",
                    line_number=node.lineno,
                    severity=IssueSeverity.WARNING,
                    issue_type="insecure_deserialization",
                    message="Desserialização insegura com pickle",
                    suggestion="Use json ou outras alternativas seguras",
                )
            )

        self.generic_visit(node)

    def _get_function_name(self, node: ast.expr) -> Optional[str]:
        """Extrai nome da função."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None


class PerformanceAnalyzer(ast.NodeVisitor):
    """Analisa problemas de performance."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.issues: List[CodeIssue] = []
        self.current_function: Optional[str] = None

    def analyze(self) -> List[CodeIssue]:
        """Analisa performance."""
        self.visit(self.tree)
        return self.issues

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_For(self, node: ast.For) -> None:
        """Verifica loops."""
        # Verificar loops aninhados
        nested_loops = sum(1 for child in ast.walk(node) if isinstance(child, (ast.For, ast.While)))
        if nested_loops > 2:
            self.issues.append(
                CodeIssue(
                    function_name=self.current_function or "unknown",
                    line_number=node.lineno,
                    severity=IssueSeverity.WARNING,
                    issue_type="nested_loops",
                    message="Loops aninhados podem afetar performance",
                    suggestion="Considere usar estruturas de dados mais eficientes",
                )
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Verifica chamadas de performance."""
        func_name = self._get_function_name(node.func)

        # Verificar operações em loops
        if func_name in ("append", "extend", "insert"):
            # Isso é uma heurística simples
            pass

        self.generic_visit(node)

    def _get_function_name(self, node: ast.expr) -> Optional[str]:
        """Extrai nome da função."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None
