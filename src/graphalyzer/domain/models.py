"""
Modelos de dados para o analisador de projetos.
Define estruturas para representar código, dependências e fluxo de dados.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set
from enum import Enum
import json


class NodeType(Enum):
    """Tipos de nós no grafo."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"


class EdgeType(Enum):
    """Tipos de arestas no grafo."""
    IMPORT = "import"
    CALLS = "calls"
    INHERITS = "inherits"
    USES = "uses"
    RETURNS_TO = "returns_to"
    DATA_FLOW = "data_flow"  # variável de saída de A vira variável de entrada de B


@dataclass
class Parameter:
    """Representa um parâmetro de função."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReturnValue:
    """Representa o valor de retorno de uma função."""
    type_hint: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Node:
    """Representa um nó no grafo (arquivo, função, classe, etc)."""
    id: str  # Identificador único (ex: "module.py::function_name")
    name: str
    type: NodeType
    file_path: str
    line_number: int = 0
    docstring: Optional[str] = None
    source_code: Optional[str] = None
    parameters: List[Parameter] = field(default_factory=list)
    return_value: Optional[ReturnValue] = None
    decorators: List[str] = field(default_factory=list)
    is_public: bool = True
    complexity: int = 1  # Complexidade ciclomática
    ai_summary: Optional[str] = None  # Resumo gerado por IA
    ai_category: Optional[str] = None  # Categoria gerada por IA (ex: "utility", "core", "api")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_source: bool = False) -> Dict[str, Any]:
        """Serializa o nó.

        `include_source` fica desligado por padrão porque o código-fonte de um
        projeto inteiro multiplica o tamanho do export. O cache liga, porque
        precisa reconstruir o grafo fielmente.
        """
        dados = {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "docstring": self.docstring,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_value": self.return_value.to_dict() if self.return_value else None,
            "decorators": self.decorators,
            "is_public": self.is_public,
            "complexity": self.complexity,
            "ai_summary": self.ai_summary,
            "ai_category": self.ai_category,
            "metadata": self.metadata,
        }

        if include_source:
            dados["source_code"] = self.source_code

        return dados

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "Node":
        return cls(
            id=dados["id"],
            name=dados["name"],
            type=NodeType(dados["type"]),
            file_path=dados["file_path"],
            line_number=dados.get("line_number", 0),
            docstring=dados.get("docstring"),
            source_code=dados.get("source_code"),
            parameters=[Parameter(**p) for p in dados.get("parameters", [])],
            return_value=(
                ReturnValue(**dados["return_value"])
                if dados.get("return_value")
                else None
            ),
            decorators=dados.get("decorators", []),
            is_public=dados.get("is_public", True),
            complexity=dados.get("complexity", 1),
            ai_summary=dados.get("ai_summary"),
            ai_category=dados.get("ai_category"),
            metadata=dados.get("metadata", {}),
        )


@dataclass
class Edge:
    """Representa uma aresta no grafo (dependência ou fluxo)."""
    source_id: str  # ID do nó de origem
    target_id: str  # ID do nó de destino
    type: EdgeType
    label: Optional[str] = None  # Ex: nome da variável que flui
    data_type: Optional[str] = None  # Tipo de dado que flui
    weight: float = 1.0  # Força da conexão
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "label": self.label,
            "data_type": self.data_type,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "Edge":
        return cls(
            source_id=dados["source_id"],
            target_id=dados["target_id"],
            type=EdgeType(dados["type"]),
            label=dados.get("label"),
            data_type=dados.get("data_type"),
            weight=dados.get("weight", 1.0),
            metadata=dados.get("metadata", {}),
        )


@dataclass
class ProjectGraph:
    """Representa o grafo completo de um projeto."""
    project_name: str
    project_path: str
    nodes: Dict[str, Node] = field(default_factory=dict)  # id -> Node
    edges: List[Edge] = field(default_factory=list)
    file_count: int = 0
    function_count: int = 0
    class_count: int = 0
    analysis_timestamp: Optional[str] = None
    ai_analysis_timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _edge_keys: Set[tuple] = field(default_factory=set, repr=False, compare=False)

    def add_node(self, node: Node) -> None:
        """Adiciona um nó ao grafo."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Adiciona uma aresta ao grafo.

        Rejeita arestas pendentes (apontando para nós inexistentes) e duplicatas.
        Aresta pendente é erro de programação do builder, não entrada do usuário:
        falha alto em vez de corromper o grafo silenciosamente.
        """
        if edge.source_id not in self.nodes:
            raise ValueError(f"Aresta com origem inexistente: {edge.source_id}")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Aresta com destino inexistente: {edge.target_id}")

        key = (edge.source_id, edge.target_id, edge.type, edge.label)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Obtém um nó pelo ID."""
        return self.nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> List[Edge]:
        """Obtém todas as arestas que saem de um nó."""
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[Edge]:
        """Obtém todas as arestas que chegam a um nó."""
        return [e for e in self.edges if e.target_id == node_id]

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Obtém todos os nós dos quais este nó depende."""
        return {e.target_id for e in self.get_edges_from(node_id)}

    def get_dependents(self, node_id: str) -> Set[str]:
        """Obtém todos os nós que dependem deste nó."""
        return {e.source_id for e in self.get_edges_to(node_id)}

    def to_dict(self, include_source: bool = False) -> Dict[str, Any]:
        """Converte o grafo para dicionário."""
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "nodes": {
                k: v.to_dict(include_source=include_source)
                for k, v in self.nodes.items()
            },
            "edges": [e.to_dict() for e in self.edges],
            "file_count": self.file_count,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "analysis_timestamp": self.analysis_timestamp,
            "ai_analysis_timestamp": self.ai_analysis_timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "ProjectGraph":
        """Reconstrói o grafo a partir do dicionário serializado.

        As arestas passam por `add_node`/`add_edge`, então a validação vale
        também aqui: um grafo corrompido no cache falha ao carregar em vez de
        entrar em circulação.
        """
        graph = cls(
            project_name=dados["project_name"],
            project_path=dados["project_path"],
            file_count=dados.get("file_count", 0),
            function_count=dados.get("function_count", 0),
            class_count=dados.get("class_count", 0),
            analysis_timestamp=dados.get("analysis_timestamp"),
            ai_analysis_timestamp=dados.get("ai_analysis_timestamp"),
            metadata=dados.get("metadata", {}),
        )

        for node in dados.get("nodes", {}).values():
            graph.add_node(Node.from_dict(node))

        for edge in dados.get("edges", []):
            graph.add_edge(Edge.from_dict(edge))

        return graph

    def to_json(self, indent: int = 2, include_source: bool = False) -> str:
        """Converte o grafo para JSON."""
        return json.dumps(
            self.to_dict(include_source=include_source),
            indent=indent,
            ensure_ascii=False,
        )
