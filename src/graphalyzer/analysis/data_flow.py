"""
Analisador avançado de fluxo de dados.
Rastreia como dados fluem entre funções, parâmetros e retornos.
"""

import ast
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class VariableInfo:
    """Informações sobre uma variável."""
    name: str
    type_hint: Optional[str] = None
    assignments: List[Tuple[int, str]] = field(default_factory=list)  # (line, value)
    usages: List[Tuple[int, str]] = field(default_factory=list)  # (line, context)
    is_parameter: bool = False
    is_return: bool = False


@dataclass
class DataFlow:
    """Representa fluxo de dados entre duas funções."""
    source_function: str
    target_function: str
    variable_name: str
    source_type: Optional[str]
    target_type: Optional[str]
    line_number: int
    confidence: float = 0.8


class DataFlowAnalyzer(ast.NodeVisitor):
    """Analisa fluxo de dados em funções."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.current_function: Optional[str] = None
        self.variables: Dict[str, VariableInfo] = {}
        self.data_flows: List[DataFlow] = []
        self.function_signatures: Dict[str, Dict] = {}

    def analyze(self) -> Tuple[Dict[str, VariableInfo], List[DataFlow]]:
        """Analisa o fluxo de dados."""
        # Primeira passagem: coletar assinaturas de funções
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function_signature(node)

        # Segunda passagem: analisar fluxo
        self.visit(self.tree)

        return self.variables, self.data_flows

    def _extract_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Extrai assinatura de função."""
        params = []
        for arg in node.args.args:
            type_hint = None
            if arg.annotation:
                type_hint = ast.unparse(arg.annotation)
            params.append({"name": arg.arg, "type": type_hint})

        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        self.function_signatures[node.name] = {
            "parameters": params,
            "return_type": return_type,
        }

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        old_function = self.current_function
        old_variables = self.variables.copy()

        self.current_function = node.name
        self.variables = {}

        # Registrar parâmetros
        for arg in node.args.args:
            type_hint = None
            if arg.annotation:
                type_hint = ast.unparse(arg.annotation)
            var = VariableInfo(
                name=arg.arg,
                type_hint=type_hint,
                is_parameter=True,
            )
            self.variables[arg.arg] = var

        self.generic_visit(node)

        self.current_function = old_function
        self.variables = old_variables

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visita definição de função assíncrona."""
        self.visit_FunctionDef(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visita atribuição."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                value_str = ast.unparse(node.value)

                if var_name not in self.variables:
                    self.variables[var_name] = VariableInfo(name=var_name)

                self.variables[var_name].assignments.append((node.lineno, value_str))

                # Tentar extrair tipo de retorno de chamada
                if isinstance(node.value, ast.Call):
                    func_name = self._get_call_name(node.value.func)
                    if func_name and func_name in self.function_signatures:
                        sig = self.function_signatures[func_name]
                        if sig["return_type"]:
                            self.variables[var_name].type_hint = sig["return_type"]

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Visita retorno."""
        if node.value:
            value_str = ast.unparse(node.value)
            # Registrar que essa variável é retornada
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                if var_name in self.variables:
                    self.variables[var_name].is_return = True

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visita chamada de função."""
        if self.current_function:
            callee_name = self._get_call_name(node.func)
            if callee_name and callee_name in self.function_signatures:
                sig = self.function_signatures[callee_name]
                params = sig["parameters"]

                # `self`/`cls` está na assinatura mas não nos argumentos da chamada:
                # sem esse desconto o tipo de cada variável sai deslocado em um.
                if params and params[0]["name"] in ("self", "cls"):
                    params = params[1:]

                # Analisar argumentos
                for i, arg in enumerate(node.args):
                    if isinstance(arg, ast.Name):
                        var_name = arg.id
                        if var_name in self.variables:
                            # Encontrar tipo do parâmetro
                            param_type = None
                            if i < len(params):
                                param_type = params[i]["type"]

                            flow = DataFlow(
                                source_function=self.current_function,
                                target_function=callee_name,
                                variable_name=var_name,
                                source_type=self.variables[var_name].type_hint,
                                target_type=param_type,
                                line_number=node.lineno,
                            )
                            self.data_flows.append(flow)

        self.generic_visit(node)

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """Extrai nome da função chamada."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class ParameterTracer:
    """Rastreia como parâmetros fluem através de funções."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)

    def trace_parameter(self, function_name: str, param_index: int) -> Set[str]:
        """Rastreia para onde um parâmetro flui."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    return self._trace_in_function(node, param_index)
        return set()

    def _trace_in_function(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, param_index: int
    ) -> Set[str]:
        """Rastreia parâmetro dentro de uma função."""
        if param_index >= len(func_node.args.args):
            return set()

        param_name = func_node.args.args[param_index].arg
        destinations = set()

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                for i, arg in enumerate(node.args):
                    if isinstance(arg, ast.Name) and arg.id == param_name:
                        # Parâmetro é passado como argumento
                        if isinstance(node.func, ast.Name):
                            destinations.add(f"{node.func.id}:param{i}")
                        elif isinstance(node.func, ast.Attribute):
                            destinations.add(f"{node.func.attr}:param{i}")

            elif isinstance(node, ast.Return):
                if node.value and isinstance(node.value, ast.Name):
                    if node.value.id == param_name:
                        destinations.add("return")

        return destinations


class TypeInferencer(ast.NodeVisitor):
    """Infere tipos de variáveis e retornos."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.type_map: Dict[str, str] = {}
        self.function_return_types: Dict[str, str] = {}

    def infer_types(self) -> Dict[str, str]:
        """Infere tipos."""
        self.visit(self.tree)
        return self.type_map

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definição de função."""
        # Extrair tipo de retorno
        if node.returns:
            return_type = ast.unparse(node.returns)
            self.function_return_types[node.name] = return_type

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visita atribuição."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                inferred_type = self._infer_type(node.value)
                self.type_map[target.id] = inferred_type

        self.generic_visit(node)

    def _infer_type(self, node: ast.expr) -> str:
        """Infere tipo de uma expressão."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int):
                return "int"
            elif isinstance(node.value, float):
                return "float"
            elif isinstance(node.value, str):
                return "str"
            elif isinstance(node.value, bool):
                return "bool"
            elif node.value is None:
                return "None"
            else:
                return "Any"

        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Tuple):
            return "tuple"

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.function_return_types:
                    return self.function_return_types[func_name]
                # Tipos built-in
                if func_name == "list":
                    return "list"
                elif func_name == "dict":
                    return "dict"
                elif func_name == "str":
                    return "str"
                elif func_name == "int":
                    return "int"
                elif func_name == "float":
                    return "float"

        elif isinstance(node, ast.BinOp):
            left_type = self._infer_type(node.left)
            right_type = self._infer_type(node.right)
            if left_type == right_type:
                return left_type
            return "Any"

        elif isinstance(node, ast.Name):
            return self.type_map.get(node.id, "Any")

        return "Any"


class DependencyResolver:
    """Resolve dependências transitivas."""

    def __init__(self, call_graph: Dict[str, Set[str]]):
        self.call_graph = call_graph

    def get_all_dependencies(self, function: str) -> Set[str]:
        """Obtém todas as dependências transitivas."""
        visited = set()
        stack = [function]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dep in self.call_graph.get(current, set()):
                if dep not in visited:
                    stack.append(dep)

        visited.discard(function)
        return visited

    def get_impact_set(self, function: str, reverse_graph: Dict[str, Set[str]]) -> Set[str]:
        """Obtém conjunto de impacto (funções afetadas por mudanças)."""
        visited = set()
        stack = [function]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dependent in reverse_graph.get(current, set()):
                if dependent not in visited:
                    stack.append(dependent)

        visited.discard(function)
        return visited

    def find_circular_dependencies(self) -> List[List[str]]:
        """Encontra dependências circulares."""
        cycles = []

        for node in self.call_graph:
            visited = set()
            rec_stack = set()
            if self._has_cycle(node, visited, rec_stack, []):
                # Encontrou ciclo
                pass

        return cycles

    def _has_cycle(
        self, node: str, visited: Set[str], rec_stack: Set[str], path: List[str]
    ) -> bool:
        """Verifica se há ciclo usando DFS."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in self.call_graph.get(node, set()):
            if neighbor not in visited:
                if self._has_cycle(neighbor, visited, rec_stack, path):
                    return True
            elif neighbor in rec_stack:
                # Encontrou ciclo
                return True

        path.pop()
        rec_stack.discard(node)
        return False
