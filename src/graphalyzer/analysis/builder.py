"""
Construtor de grafo de dependências para projetos Python.
Integra parser, extrator e modelos de dados.
"""

import logging
import os

from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path

from graphalyzer.domain.models import (
    Node,
    Edge,
    NodeType,
    EdgeType,
    Parameter,
    ReturnValue,
    ProjectGraph,
)
from graphalyzer.analysis.parser import ProjectParser, FileInfo, FunctionInfo, ClassInfo
from graphalyzer.analysis.extractor import (
    DependencyExtractor,
    CallGraphBuilder,
    ImportGraphBuilder,
    ComplexityAnalyzer,
)
from graphalyzer.analysis.data_flow import DataFlowAnalyzer

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Constrói grafo de dependências de um projeto Python."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.project_name = Path(project_path).name
        self.parser = ProjectParser(project_path)
        self.graph = ProjectGraph(
            project_name=self.project_name,
            project_path=project_path,
        )
        self.call_graph = CallGraphBuilder()
        self.import_graph = ImportGraphBuilder()
        self.complexity_analyzer = ComplexityAnalyzer()

    def build(self) -> ProjectGraph:
        """Constrói o grafo completo do projeto."""
        # Fase 1: Parse do projeto
        logger.info(f"[1/4] Parseando projeto: {self.project_path}")
        files = self.parser.parse_project()

        # Fase 2: Criar nós para arquivos, funções e classes
        logger.info(f"[2/4] Criando nós ({len(files)} arquivos)...")
        self._create_nodes(files)

        # Fase 3: Indexar símbolos e extrair dependências
        logger.info(f"[3/4] Resolvendo símbolos e extraindo dependências...")
        self._build_symbol_table(files)
        self._extract_dependencies(files)

        # Fase 4: Calcular complexidade
        logger.info(f"[4/4] Calculando complexidade...")
        self._calculate_complexity(files)

        # Atualizar metadados
        self.graph.analysis_timestamp = datetime.now().isoformat()
        self.graph.file_count = len(files)
        self.graph.function_count = sum(len(f.functions) for f in files.values())
        self.graph.class_count = sum(len(f.classes) for f in files.values())

        logger.info(f"✓ Grafo construído com sucesso!")
        logger.info(f"  - Arquivos: {self.graph.file_count}")
        logger.info(f"  - Funções: {self.graph.function_count}")
        logger.info(f"  - Classes: {self.graph.class_count}")
        logger.info(f"  - Arestas: {len(self.graph.edges)}")

        return self.graph

    def _create_nodes(self, files: Dict[str, FileInfo]) -> None:
        """Cria nós para arquivos, funções e classes."""
        for file_path, file_info in files.items():
            # Nó para arquivo
            file_node_id = self._get_file_node_id(file_path)
            file_node = Node(
                id=file_node_id,
                name=file_info.module_name,
                type=NodeType.FILE,
                file_path=file_path,
                docstring=file_info.docstring,
                source_code=file_info.source_code,
                is_public=not file_info.module_name.startswith("_"),
            )
            self.graph.add_node(file_node)

            # Nós para classes
            for class_info in file_info.classes:
                class_node_id = self._get_class_node_id(file_path, class_info.name)
                class_node = Node(
                    id=class_node_id,
                    name=class_info.name,
                    type=NodeType.CLASS,
                    file_path=file_path,
                    line_number=class_info.line_number,
                    docstring=class_info.docstring,
                    source_code=class_info.source_code,
                    is_public=not class_info.is_private,
                )
                self.graph.add_node(class_node)

                # Aresta: arquivo -> classe
                self.graph.add_edge(
                    Edge(
                        source_id=file_node_id,
                        target_id=class_node_id,
                        type=EdgeType.USES,
                        label="contains",
                    )
                )

                # Nós para métodos
                for method_info in class_info.methods:
                    method_node_id = self._get_method_node_id(
                        file_path, class_info.name, method_info.name
                    )
                    method_node = self._create_function_node(
                        method_node_id, method_info, file_path
                    )
                    self.graph.add_node(method_node)

                    # Aresta: classe -> método
                    self.graph.add_edge(
                        Edge(
                            source_id=class_node_id,
                            target_id=method_node_id,
                            type=EdgeType.USES,
                            label="contains",
                        )
                    )

            # Nós para funções de nível superior
            for func_info in file_info.functions:
                func_node_id = self._get_function_node_id(file_path, func_info.name)
                func_node = self._create_function_node(func_node_id, func_info, file_path)
                self.graph.add_node(func_node)

                # Aresta: arquivo -> função
                self.graph.add_edge(
                    Edge(
                        source_id=file_node_id,
                        target_id=func_node_id,
                        type=EdgeType.USES,
                        label="contains",
                    )
                )

    def _create_function_node(
        self, node_id: str, func_info: FunctionInfo, file_path: str
    ) -> Node:
        """Cria um nó de função."""
        # Converter parâmetros
        parameters = [
            Parameter(
                name=param[0],
                type_hint=param[1],
                default_value=param[2],
            )
            for param in func_info.parameters
        ]

        # Converter tipo de retorno
        return_value = None
        if func_info.return_type:
            return_value = ReturnValue(type_hint=func_info.return_type)

        return Node(
            id=node_id,
            name=func_info.name,
            type=NodeType.FUNCTION,
            file_path=file_path,
            line_number=func_info.line_number,
            docstring=func_info.docstring,
            source_code=func_info.source_code,
            parameters=parameters,
            return_value=return_value,
            decorators=func_info.decorators,
            is_public=not func_info.is_private,
        )

    def _build_symbol_table(self, files: Dict[str, FileInfo]) -> None:
        """Indexa módulos e símbolos do projeto para resolver referências por ID.

        Sem esta tabela não há como ligar um import a um arquivo nem uma chamada
        ao nó certo — é a base de todas as arestas reais do grafo.
        """
        self._module_index: Dict[str, str] = {}  # "core.parser" -> caminho do arquivo
        self._file_symbols: Dict[str, Dict[str, str]] = {}  # arquivo -> {nome: node_id}
        self._class_methods: Dict[str, Dict[tuple, str]] = {}  # arquivo -> {(classe, metodo): id}
        self._method_names: Dict[str, List[str]] = {}  # metodo -> ids (projeto todo)
        self._file_methods: Dict[str, Dict[str, List[str]]] = {}  # arquivo -> {metodo: ids}
        self._imported: Dict[str, Dict[str, str]] = {}  # arquivo -> {nome local: node_id}
        self._params_by_node: Dict[str, list] = {}  # node_id -> parâmetros declarados
        self._symbol_names: Dict[str, List[str]] = {}  # nome de topo -> ids (projeto)
        self._package_scope: Dict[str, bool] = {}  # arquivo -> vê o pacote todo?
        self._path_index: Dict[str, str] = {}  # caminho relativo sem extensão -> arquivo
        # Índice de caminhos para resolver imports sem consultar o disco:
        # cada arquivo entra com e sem extensão, já normalizado.
        self._raiz_normalizada = os.path.abspath(self.project_path)
        self._por_caminho: Dict[str, str] = {}
        for f in files:
            chave = os.path.normcase(os.path.abspath(f))
            self._por_caminho[chave] = f
            self._por_caminho[os.path.splitext(chave)[0]] = f

        root = Path(self.project_path).resolve()

        for file_path, file_info in files.items():
            # Índice de módulos: caminho relativo vira nome pontilhado
            parts = list(Path(file_path).resolve().relative_to(root).parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = Path(parts[-1]).stem
            if parts:
                self._module_index[".".join(parts)] = file_path
                # Linguagens que importam por caminho ("./utils", "utils.dart")
                # precisam de um índice pelo caminho, não pelo nome pontilhado
                self._path_index["/".join(parts)] = file_path

            symbols: Dict[str, str] = {}
            methods: Dict[tuple, str] = {}
            by_name: Dict[str, List[str]] = {}

            for func_info in file_info.functions:
                node_id = self._get_function_node_id(file_path, func_info.name)
                symbols[func_info.name] = node_id
                self._params_by_node[node_id] = func_info.parameters

            for class_info in file_info.classes:
                symbols[class_info.name] = self._get_class_node_id(
                    file_path, class_info.name
                )
                for method_info in class_info.methods:
                    node_id = self._get_method_node_id(
                        file_path, class_info.name, method_info.name
                    )
                    methods[(class_info.name, method_info.name)] = node_id
                    self._params_by_node[node_id] = method_info.parameters
                    by_name.setdefault(method_info.name, []).append(node_id)
                    self._method_names.setdefault(method_info.name, []).append(node_id)

            self._file_symbols[file_path] = symbols
            self._class_methods[file_path] = methods
            self._file_methods[file_path] = by_name

            for nome, node_id in symbols.items():
                self._symbol_names.setdefault(nome, []).append(node_id)

            self._package_scope[file_path] = self._tem_escopo_de_pacote(file_info)

        # Segunda passagem: `from x import y` só resolve com todos os símbolos prontos
        for file_path, file_info in files.items():
            local: Dict[str, str] = {}
            for import_info in file_info.imports:
                if not import_info.is_from_import:
                    continue
                target_file = self._resolve_import(import_info, file_path)
                if not target_file:
                    continue
                if not import_info.names:
                    # Dart, JS e afins: `import 'x.dart'` traz todos os símbolos
                    # públicos do arquivo, não um nome específico. Sem isto,
                    # nenhuma chamada entre arquivos seria resolvida.
                    local.update(self._file_symbols.get(target_file, {}))
                    continue

                for name, alias in import_info.names:
                    node_id = self._file_symbols.get(target_file, {}).get(name)
                    if node_id:
                        local[alias or name] = node_id
            self._imported[file_path] = local

    @staticmethod
    def _tem_escopo_de_pacote(file_info: FileInfo) -> bool:
        """A linguagem do arquivo enxerga símbolos irmãos sem import?"""
        from graphalyzer.analysis.languages.specs import SPECS

        spec = SPECS.get(file_info.language)
        return bool(spec and spec.package_scope)

    def _extract_dependencies(self, files: Dict[str, FileInfo]) -> None:
        """Extrai dependências entre funções e arquivos."""
        for file_path, file_info in files.items():
            file_node_id = self._get_file_node_id(file_path)

            # Arestas de import entre arquivos do projeto
            for import_info in file_info.imports:
                for imported_file in self._resolve_import_targets(
                    import_info, file_path
                ):
                    if imported_file == file_path:
                        continue
                    self.graph.add_edge(
                        Edge(
                            source_id=file_node_id,
                            target_id=self._get_file_node_id(imported_file),
                            type=EdgeType.IMPORT,
                            label=import_info.module or ".",
                        )
                    )
                    self.import_graph.add_import(file_path, imported_file)

            # Chamadas: cada função carrega o próprio node_id e a classe que a contém
            scoped_functions = [
                (func_info, self._get_function_node_id(file_path, func_info.name), None)
                for func_info in file_info.functions
            ] + [
                (
                    method_info,
                    self._get_method_node_id(file_path, cls.name, method_info.name),
                    cls.name,
                )
                for cls in file_info.classes
                for method_info in cls.methods
            ]

            for func_info, caller_node_id, class_name in scoped_functions:
                # As chamadas já vêm resolvidas pelo analisador da linguagem
                for call in func_info.calls:
                    callee_node_id = self._resolve_reference(
                        call.callee, file_path, class_name
                    )
                    if callee_node_id and callee_node_id != caller_node_id:
                        self.graph.add_edge(
                            Edge(
                                source_id=caller_node_id,
                                target_id=callee_node_id,
                                type=EdgeType.CALLS,
                                label=call.callee,
                            )
                        )
                        self.call_graph.add_call(caller_node_id, callee_node_id)

            self._extract_data_flow(file_path, file_info)

    def _extract_data_flow(self, file_path: str, file_info: FileInfo) -> None:
        """Cria arestas de fluxo de dados: saída de uma função vira entrada de outra.

        São estas as conexões que o grafo existe para mostrar — quem alimenta quem,
        com qual variável e de qual tipo.
        """
        if file_info.language != "python":
            # Demais linguagens: o fluxo sai dos argumentos da chamada, casados
            # posicionalmente com os parâmetros de quem é chamado. Sem inferência
            # de tipo de variável, o tipo vem do parâmetro de destino.
            self._data_flow_generico(file_path, file_info)
            return

        try:
            _, flows = DataFlowAnalyzer(file_info.source_code).analyze()
        except SyntaxError:
            return

        for flow in flows:
            source_id = self._resolve_reference(flow.source_function, file_path, None)
            target_id = self._resolve_reference(flow.target_function, file_path, None)

            if source_id and target_id and source_id != target_id:
                self.graph.add_edge(
                    Edge(
                        source_id=source_id,
                        target_id=target_id,
                        type=EdgeType.DATA_FLOW,
                        label=flow.variable_name,
                        data_type=flow.target_type or flow.source_type,
                        weight=flow.confidence,
                    )
                )

    def _data_flow_generico(self, file_path: str, file_info: FileInfo) -> None:
        """Fluxo de dados a partir dos argumentos de cada chamada.

        Serve qualquer linguagem: `calcularTotal(itens, desconto)` liga quem
        chama a quem é chamado, uma aresta por argumento, com o tipo declarado
        do parâmetro correspondente no destino.
        """
        escopos = [(f, self._get_function_node_id(file_path, f.name), None) for f in file_info.functions]
        escopos += [
            (m, self._get_method_node_id(file_path, c.name, m.name), c.name)
            for c in file_info.classes
            for m in c.methods
        ]

        for func_info, origem_id, class_name in escopos:
            for call in func_info.calls:
                if not call.arguments:
                    continue

                destino_id = self._resolve_reference(call.callee, file_path, class_name)
                if not destino_id or destino_id == origem_id:
                    continue

                parametros = self._params_by_node.get(destino_id, [])

                for indice, argumento in enumerate(call.arguments):
                    tipo = parametros[indice][1] if indice < len(parametros) else None
                    self.graph.add_edge(
                        Edge(
                            source_id=origem_id,
                            target_id=destino_id,
                            type=EdgeType.DATA_FLOW,
                            label=argumento,
                            data_type=tipo,
                            # Sem resolver o tipo da variável de origem, a
                            # confiança é menor que no caminho do Python
                            weight=0.6,
                        )
                    )

    def _resolve_reference(
        self, name: str, file_path: str, class_name: Optional[str]
    ) -> Optional[str]:
        """Resolve um nome para o ID de um nó, do escopo mais próximo ao mais distante."""
        # 1. Método da própria classe (self.metodo())
        if class_name:
            node_id = self._class_methods.get(file_path, {}).get((class_name, name))
            if node_id:
                return node_id

        # 2. Função ou classe de nível superior no mesmo arquivo
        node_id = self._file_symbols.get(file_path, {}).get(name)
        if node_id:
            return node_id

        # 3. Nome trazido por `from x import y`
        node_id = self._imported.get(file_path, {}).get(name)
        if node_id:
            return node_id

        # 4. Mesmo pacote: em Go, Java e C#, arquivos irmãos se enxergam sem
        # import. Só vale para essas linguagens — em Python ou Dart, um nome
        # global sem import correspondente seria aresta inventada.
        if self._package_scope.get(file_path):
            candidatos = self._symbol_names.get(name, [])
            if len(candidatos) == 1:
                return candidatos[0]

        # 5. Método de outra classe, só quando o nome é inequívoco.
        # ponytail: heurística por nome único — sem inferência de tipo do receptor,
        # `obj.save()` é ambíguo se duas classes têm `save`. Ambíguo = sem aresta,
        # preferindo perder uma conexão a inventar uma falsa.
        for scope in (self._file_methods.get(file_path, {}), self._method_names):
            candidates = scope.get(name, [])
            if len(candidates) == 1:
                return candidates[0]
            if candidates:
                return None  # ambíguo neste escopo, não escala para o próximo

        return None

    def _calculate_complexity(self, files: Dict[str, FileInfo]) -> None:
        """Copia para os nós a complexidade calculada pelo analisador da linguagem."""
        for file_path, file_info in files.items():
            for func_info in file_info.functions:
                node = self.graph.get_node(
                    self._get_function_node_id(file_path, func_info.name)
                )
                if node:
                    node.complexity = func_info.complexity

            for class_info in file_info.classes:
                for method_info in class_info.methods:
                    node = self.graph.get_node(
                        self._get_method_node_id(
                            file_path, class_info.name, method_info.name
                        )
                    )
                    if node:
                        node.complexity = method_info.complexity

    def _get_file_node_id(self, file_path: str) -> str:
        """Gera ID único para nó de arquivo."""
        return f"file::{file_path}"

    def _get_function_node_id(self, file_path: str, func_name: str) -> str:
        """Gera ID único para nó de função."""
        return f"func::{file_path}::{func_name}"

    def _get_class_node_id(self, file_path: str, class_name: str) -> str:
        """Gera ID único para nó de classe."""
        return f"class::{file_path}::{class_name}"

    def _get_method_node_id(self, file_path: str, class_name: str, method_name: str) -> str:
        """Gera ID único para nó de método."""
        return f"method::{file_path}::{class_name}::{method_name}"

    def _resolve_import(self, import_info, current_file: str) -> Optional[str]:
        """Resolve um import para um arquivo do projeto (None se for externo)."""
        # Linguagens que importam por caminho ("./utils", "utils.dart",
        # "package:app/x.dart") resolvem contra o arquivo, não contra um
        # nome de módulo pontilhado.
        if getattr(import_info, "path", None):
            resolvido = self._resolve_import_por_caminho(import_info.path, current_file)
            if resolvido:
                return resolvido

        module = import_info.module

        if import_info.level:
            # Import relativo: sobe `level - 1` pacotes a partir do diretório atual
            root = Path(self.project_path).resolve()
            package = Path(current_file).resolve().parent
            for _ in range(import_info.level - 1):
                package = package.parent
            if root not in package.parents and package != root:
                return None
            prefix = ".".join(package.relative_to(root).parts)
            module = f"{prefix}.{module}" if prefix and module else (prefix or module)

        return self._module_index.get(module)

    def _resolve_import_por_caminho(
        self, caminho: str, current_file: str
    ) -> Optional[str]:
        """Resolve import baseado em caminho de arquivo.

        Cobre os formatos comuns: relativo ao arquivo (`./utils`, `../x/y`),
        relativo à raiz, e o `package:app/...` do Dart — que aponta para `lib/`.
        """
        if not caminho or caminho.startswith(("dart:", "http:", "https:")):
            return None  # biblioteca da plataforma ou URL: externo

        # Resolução puramente aritmética, sem tocar o disco. Consultar o
        # sistema de arquivos aqui custava ~10 mil chamadas por projeto — no
        # bind mount do Docker isso transformava 2 segundos em dois minutos.
        raiz = self._raiz_normalizada
        limpo = caminho

        if limpo.startswith("package:"):
            # package:meu_app/servicos/x.dart -> lib/servicos/x.dart
            partes = limpo[len("package:") :].split("/", 1)
            if len(partes) != 2:
                return None
            candidatos = [os.path.join(raiz, "lib", partes[1])]
        else:
            candidatos = [
                os.path.join(os.path.dirname(current_file), limpo),
                os.path.join(raiz, limpo.lstrip("./")),
            ]

        for candidato in candidatos:
            chave = os.path.normcase(os.path.normpath(candidato))
            alvo = self._por_caminho.get(chave) or self._por_caminho.get(
                os.path.splitext(chave)[0]
            )
            if alvo:
                return alvo

        return None

    def _resolve_import_targets(self, import_info, current_file: str) -> List[str]:
        """Todos os arquivos do projeto que um import alcança.

        `from pacote import a, b` alcança o pacote e cada submódulo importado.
        """
        targets = []

        module_file = self._resolve_import(import_info, current_file)
        if module_file:
            targets.append(module_file)

        if import_info.is_from_import:
            # `from pacote import modulo` — o alvo é um submódulo, não um nome
            prefix = import_info.module
            if import_info.level and module_file:
                prefix = ".".join(
                    Path(module_file).resolve().parent.relative_to(
                        Path(self.project_path).resolve()
                    ).parts
                )
            for name, _alias in import_info.names:
                submodule = f"{prefix}.{name}" if prefix else name
                target = self._module_index.get(submodule)
                if target and target not in targets:
                    targets.append(target)

        return targets
