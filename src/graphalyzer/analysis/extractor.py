"""
Extrator de dependências e fluxo de dados entre funções e arquivos.
Analisa chamadas de função, imports e fluxo de variáveis.
"""

import ast
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FunctionCall:
    """Informações sobre uma chamada de função."""
    caller: str  # Nome da função que faz a chamada
    callee: str  # Nome da função chamada
    line_number: int
    arguments: List[str]  # Nomes dos argumentos passados


@dataclass
class VariableFlow:
    """Informações sobre fluxo de variáveis."""
    source_function: str
    target_function: str
    variable_name: str
    variable_type: Optional[str]
    line_number: int


class DependencyExtractor(ast.NodeVisitor):
    """Extrai dependências entre funções usando AST."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.current_function: Optional[str] = None
        self.function_calls: List[FunctionCall] = []
        self.variable_assignments: Dict[str, str] = {}  # var_name -> type
        self.function_defs: Set[str] = set()

    def extract(self) -> Tuple[List[FunctionCall], Dict[str, str]]:
        """Extrai todas as dependências."""
        # Primeiro, coletar todas as funções definidas
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.function_defs.add(node.name)

        # Depois, visitar o árvore para encontrar chamadas
        self.visit(self.tree)

        return self.function_calls, self.variable_assignments

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        self.current_function = node.name

        # Registrar parâmetros como variáveis
        for arg in node.args.args:
            self.variable_assignments[arg.arg] = "parameter"

        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visita definição de função assíncrona."""
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visita chamada de função."""
        if self.current_function:
            callee_name = self._get_function_name(node.func)
            if callee_name:
                arguments = [ast.unparse(arg) for arg in node.args]
                self.function_calls.append(
                    FunctionCall(
                        caller=self.current_function,
                        callee=callee_name,
                        line_number=node.lineno,
                        arguments=arguments,
                    )
                )

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visita atribuição de variável."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_type = None
                if isinstance(node.value, ast.Call):
                    var_type = self._get_function_name(node.value.func)
                self.variable_assignments[target.id] = var_type or "unknown"

        self.generic_visit(node)

    def _get_function_name(self, node: ast.expr) -> Optional[str]:
        """Extrai o nome da função de um nó AST."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Para chamadas como obj.method()
            return node.attr
        elif isinstance(node, ast.Subscript):
            return None
        return None


class CallGraphBuilder:
    """Constrói grafo de chamadas entre funções."""

    def __init__(self):
        self.call_graph: Dict[str, Set[str]] = {}  # function -> set of called functions
        self.reverse_call_graph: Dict[str, Set[str]] = {}  # function -> set of functions that call it

    def add_call(self, caller: str, callee: str) -> None:
        """Adiciona uma chamada ao grafo."""
        if caller not in self.call_graph:
            self.call_graph[caller] = set()
        self.call_graph[caller].add(callee)

        if callee not in self.reverse_call_graph:
            self.reverse_call_graph[callee] = set()
        self.reverse_call_graph[callee].add(caller)

    def get_callees(self, function: str) -> Set[str]:
        """Obtém funções chamadas por uma função."""
        return self.call_graph.get(function, set())

    def get_callers(self, function: str) -> Set[str]:
        """Obtém funções que chamam uma função."""
        return self.reverse_call_graph.get(function, set())

    def get_transitive_callees(self, function: str) -> Set[str]:
        """Obtém todas as funções chamadas transitivamente."""
        visited = set()
        stack = [function]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for callee in self.get_callees(current):
                if callee not in visited:
                    stack.append(callee)

        visited.discard(function)
        return visited

    def get_transitive_callers(self, function: str) -> Set[str]:
        """Obtém todas as funções que chamam uma função transitivamente."""
        visited = set()
        stack = [function]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for caller in self.get_callers(current):
                if caller not in visited:
                    stack.append(caller)

        visited.discard(function)
        return visited


class ImportGraphBuilder:
    """Constrói grafo de imports entre arquivos."""

    def __init__(self):
        self.import_graph: Dict[str, Set[str]] = {}  # file -> set of imported files
        self.reverse_import_graph: Dict[str, Set[str]] = {}  # file -> set of files that import it

    def add_import(self, importer: str, imported: str) -> None:
        """Adiciona um import ao grafo."""
        if importer not in self.import_graph:
            self.import_graph[importer] = set()
        self.import_graph[importer].add(imported)

        if imported not in self.reverse_import_graph:
            self.reverse_import_graph[imported] = set()
        self.reverse_import_graph[imported].add(importer)

    def get_imports(self, file: str) -> Set[str]:
        """Obtém arquivos importados por um arquivo."""
        return self.import_graph.get(file, set())

    def get_importers(self, file: str) -> Set[str]:
        """Obtém arquivos que importam um arquivo."""
        return self.reverse_import_graph.get(file, set())

    def get_transitive_imports(self, file: str) -> Set[str]:
        """Obtém todos os arquivos importados transitivamente."""
        visited = set()
        stack = [file]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for imported in self.get_imports(current):
                if imported not in visited:
                    stack.append(imported)

        visited.discard(file)
        return visited

    def get_transitive_importers(self, file: str) -> Set[str]:
        """Obtém todos os arquivos que importam um arquivo transitivamente."""
        visited = set()
        stack = [file]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for importer in self.get_importers(current):
                if importer not in visited:
                    stack.append(importer)

        visited.discard(file)
        return visited


class ComplexityAnalyzer(ast.NodeVisitor):
    """Calcula complexidade ciclomática de funções."""

    def __init__(self):
        self.complexity = 1
        self.function_complexity: Dict[str, int] = {}  # nome qualificado -> complexidade
        self.current_function: Optional[str] = None
        self._scope: List[str] = []  # pilha de classes, para qualificar métodos

    def analyze(self, source_code: str) -> Dict[str, int]:
        """Analisa complexidade de um arquivo.

        Chaves são qualificadas ("Classe.metodo") para que métodos homônimos
        em classes diferentes não se sobrescrevam.
        """
        tree = ast.parse(source_code)
        self.visit(tree)
        return self.function_complexity

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visita definição de classe."""
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        old_complexity = self.complexity

        qualified = ".".join(self._scope + [node.name])
        self.current_function = qualified
        self.complexity = 1

        # funções aninhadas não devem herdar o escopo de classe do pai
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

        self.function_complexity[qualified] = self.complexity
        self.current_function = old_function
        self.complexity = old_complexity

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visita definição de função assíncrona."""
        self.visit_FunctionDef(node)

    def visit_If(self, node: ast.If) -> None:
        """Incrementa complexidade para if."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Incrementa complexidade para for."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Incrementa complexidade para while."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Incrementa complexidade para except."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Incrementa complexidade para operadores booleanos."""
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
