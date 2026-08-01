"""Conversão do grafo para o formato do Cytoscape.

Compartilhado pelo dashboard (via API) e pelo HTML exportado — as duas
telas mostram o mesmo grafo e não podem divergir na hora de montá-lo.
"""

from typing import Any, Dict, List, Optional

from graphalyzer.domain.models import NodeType, ProjectGraph

NODE_COLORS = {
    NodeType.FILE: "#28a745",
    NodeType.FUNCTION: "#007bff",
    NodeType.CLASS: "#ffc107",
    NodeType.MODULE: "#6c757d",
}

# Qual nível de detalhe cada visualização mostra
VIEW_TYPES = {
    "file": {NodeType.FILE},
    "function": {NodeType.FUNCTION, NodeType.CLASS},
    "all": {NodeType.FILE, NodeType.FUNCTION, NodeType.CLASS, NodeType.MODULE},
}


def to_cytoscape(graph: ProjectGraph, view_type: str = "all") -> Dict[str, List[Any]]:
    """Monta nós e arestas no formato do Cytoscape para a visualização pedida.

    Uma aresta só entra se os dois extremos estiverem visíveis — do contrário
    o Cytoscape recebe aresta órfã e quebra a renderização.
    """
    visible = VIEW_TYPES.get(view_type, VIEW_TYPES["all"])

    nodes = [
        {
            "data": {
                "id": node.id,
                "label": node.name,
                "type": node.type.value,
                "color": NODE_COLORS.get(node.type, "#999"),
                "complexity": node.complexity,
                "file_path": node.file_path,
            }
        }
        for node in graph.nodes.values()
        if node.type in visible
    ]

    visible_ids = {n["data"]["id"] for n in nodes}

    edges = [
        {
            "data": {
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.label or edge.type.value,
                "type": edge.type.value,
                "data_type": edge.data_type,
            }
        }
        for edge in graph.edges
        if edge.source_id in visible_ids and edge.target_id in visible_ids
    ]

    return {"nodes": nodes, "edges": edges}


def node_detail(graph: ProjectGraph, node_id: str) -> Optional[Dict[str, Any]]:
    """Detalhes completos de um nó, incluindo assinatura e grau de conexão."""
    node = graph.get_node(node_id)
    if node is None:
        return None

    return {
        "id": node.id,
        "name": node.name,
        "type": node.type.value,
        "file_path": node.file_path,
        "line_number": node.line_number,
        "docstring": node.docstring,
        "source_code": node.source_code,
        "parameters": [
            {"name": p.name, "type": p.type_hint, "default": p.default_value}
            for p in node.parameters
        ],
        "return_type": node.return_value.type_hint if node.return_value else None,
        "decorators": node.decorators,
        "complexity": node.complexity,
        "ai_summary": node.ai_summary,
        "ai_category": node.ai_category,
        "incoming_edges": len(graph.get_edges_to(node.id)),
        "outgoing_edges": len(graph.get_edges_from(node.id)),
    }
