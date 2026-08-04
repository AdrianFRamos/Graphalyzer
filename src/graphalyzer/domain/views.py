"""Conversão do grafo para o formato do Cytoscape.

Compartilhado pelo dashboard (via API) e pelo HTML exportado — as duas
telas mostram o mesmo grafo e não podem divergir na hora de montá-lo.
"""

from pathlib import PurePath
from typing import Any, Dict, List, Optional

from graphalyzer.domain.models import EdgeType, NodeType, ProjectGraph

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


def pasta_do_no(node, project_path: str) -> str:
    """Pasta do nó, relativa à raiz do projeto.

    É o agrupamento natural de um repositório — `lib/servicos`, `api/routes` —
    e serve para colorir o grafo por módulo em vez de por tipo de nó.
    """
    if not node.file_path:
        return ""

    try:
        relativo = PurePath(node.file_path).relative_to(PurePath(project_path))
    except ValueError:
        relativo = PurePath(node.file_path)

    pasta = relativo.parent.as_posix()
    return "" if pasta in (".", "/") else pasta


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
                "folder": pasta_do_no(node, graph.project_path),
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


def assinatura(node) -> str:
    """Assinatura legível da rotina: `nome(param: tipo) -> retorno`."""
    partes = []
    for p in node.parameters:
        texto = f"{p.name}: {p.type_hint}" if p.type_hint else p.name
        if p.default_value:
            texto += f" = {p.default_value}"
        partes.append(texto)

    retorno = ""
    if node.return_value and node.return_value.type_hint:
        retorno = f" -> {node.return_value.type_hint}"

    return f"{node.name}({', '.join(partes)}){retorno}"


def _relacoes(graph: ProjectGraph, node_id: str) -> Dict[str, Any]:
    """Todas as relações do nó, separadas por tipo de aresta.

    Os parâmetros dizem o que a rotina aceita; estas listas dizem o que de
    fato chega e sai — qual variável, vinda de quem, indo para onde.

    Cada tipo de aresta tem seu balde, e todos são exibidos. Antes só `calls`
    e `data_flow` chegavam à tela: um nó com três arestas de import ou de
    contenção mostrava "3 entradas" e a seção vazia logo abaixo.
    """
    baldes: Dict[str, list] = {
        "entradas": [],  # data flow que chega
        "saidas": [],  # data flow que sai
        "chamado_por": [],
        "chama": [],
        "importado_por": [],
        "importa": [],
        "contido_em": [],  # arquivo ou classe que contém este nó
        "contem": [],  # membros deste nó
    }

    def referencia(node, edge=None):
        item = {"nome": node.name, "id": node.id, "tipo": node.type.value}
        if edge is not None and edge.label:
            item["rotulo"] = edge.label
        return item

    for edge in graph.get_edges_to(node_id):
        origem = graph.get_node(edge.source_id)
        if origem is None:
            continue

        if edge.type == EdgeType.DATA_FLOW:
            baldes["entradas"].append(
                {
                    "variavel": edge.label,
                    "tipo": edge.data_type,
                    "origem": origem.name,
                    "origem_id": origem.id,
                }
            )
        elif edge.type == EdgeType.CALLS:
            baldes["chamado_por"].append(referencia(origem))
        elif edge.type == EdgeType.IMPORT:
            baldes["importado_por"].append(referencia(origem, edge))
        elif edge.type == EdgeType.USES:
            baldes["contido_em"].append(referencia(origem))

    for edge in graph.get_edges_from(node_id):
        destino = graph.get_node(edge.target_id)
        if destino is None:
            continue

        if edge.type == EdgeType.DATA_FLOW:
            baldes["saidas"].append(
                {
                    "variavel": edge.label,
                    "tipo": edge.data_type,
                    "destino": destino.name,
                    "destino_id": destino.id,
                }
            )
        elif edge.type == EdgeType.CALLS:
            baldes["chama"].append(referencia(destino))
        elif edge.type == EdgeType.IMPORT:
            baldes["importa"].append(referencia(destino, edge))
        elif edge.type == EdgeType.USES:
            baldes["contem"].append(referencia(destino))

    # Contagem por tipo: é o que a tela mostra em vez de um total sem detalhe
    baldes["resumo_das_relacoes"] = {
        "entram": {
            "fluxo": len(baldes["entradas"]),
            "chamadas": len(baldes["chamado_por"]),
            "imports": len(baldes["importado_por"]),
            "contencao": len(baldes["contido_em"]),
        },
        "saem": {
            "fluxo": len(baldes["saidas"]),
            "chamadas": len(baldes["chama"]),
            "imports": len(baldes["importa"]),
            "contencao": len(baldes["contem"]),
        },
    }

    return baldes


def node_detail(graph: ProjectGraph, node_id: str) -> Optional[Dict[str, Any]]:
    """Detalhes completos de um nó, incluindo assinatura e grau de conexão."""
    node = graph.get_node(node_id)
    if node is None:
        return None

    return {
        **_relacoes(graph, node_id),
        "signature": assinatura(node),
        "folder": pasta_do_no(node, graph.project_path),
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
