"""
Exportadores para diferentes formatos (JSON, Markdown, HTML, etc).
"""

import logging

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from graphalyzer.domain.models import ProjectGraph, Node, Edge, NodeType, EdgeType
from graphalyzer.domain.views import to_cytoscape

logger = logging.getLogger(__name__)


class Exporter:
    """Classe base para exportadores."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    def export(self, output_path: str) -> None:
        """Exporta o grafo."""
        raise NotImplementedError


class JSONExporter(Exporter):
    """Exporta grafo para JSON."""

    def export(self, output_path: str) -> None:
        """Exporta para JSON."""
        data = self.graph.to_dict()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Grafo exportado para JSON: {output_path}")


class MarkdownExporter(Exporter):
    """Exporta grafo para Markdown."""

    def export(self, output_path: str) -> None:
        """Exporta para Markdown."""
        content = self._generate_markdown()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"✓ Grafo exportado para Markdown: {output_path}")

    def _generate_markdown(self) -> str:
        """Gera conteúdo Markdown."""
        lines = []

        # Cabeçalho
        lines.append(f"# Análise do Projeto: {self.graph.project_name}")
        lines.append("")
        lines.append(f"**Caminho**: `{self.graph.project_path}`")
        lines.append(f"**Data da análise**: {self.graph.analysis_timestamp}")
        lines.append("")

        # Estatísticas
        lines.append("## Estatísticas")
        lines.append("")
        lines.append(f"- **Arquivos**: {self.graph.file_count}")
        lines.append(f"- **Funções**: {self.graph.function_count}")
        lines.append(f"- **Classes**: {self.graph.class_count}")
        lines.append(f"- **Dependências**: {len(self.graph.edges)}")
        lines.append("")

        # Arquivos
        lines.append("## Arquivos")
        lines.append("")
        for node in self.graph.nodes.values():
            if node.type == NodeType.FILE:
                lines.append(f"### {node.name}")
                if node.docstring:
                    lines.append(f"\n{node.docstring}\n")
                lines.append("")

        # Funções
        lines.append("## Funções")
        lines.append("")
        for node in self.graph.nodes.values():
            if node.type == NodeType.FUNCTION:
                lines.append(f"### {node.name}")
                lines.append(f"**Arquivo**: `{node.file_path}`")
                lines.append(f"**Linha**: {node.line_number}")
                
                if node.parameters:
                    lines.append("\n**Parâmetros**:")
                    for param in node.parameters:
                        type_str = f": {param.type_hint}" if param.type_hint else ""
                        default_str = f" = {param.default_value}" if param.default_value else ""
                        lines.append(f"- `{param.name}{type_str}{default_str}`")
                
                if node.return_value:
                    lines.append(f"\n**Retorno**: `{node.return_value.type_hint}`")
                
                if node.docstring:
                    lines.append(f"\n{node.docstring}")
                
                if node.ai_summary:
                    lines.append(f"\n**Resumo IA**: {node.ai_summary}")
                
                lines.append("")

        # Classes
        lines.append("## Classes")
        lines.append("")
        for node in self.graph.nodes.values():
            if node.type == NodeType.CLASS:
                lines.append(f"### {node.name}")
                lines.append(f"**Arquivo**: `{node.file_path}`")
                lines.append(f"**Linha**: {node.line_number}")
                
                if node.docstring:
                    lines.append(f"\n{node.docstring}")
                
                lines.append("")

        # Dependências
        lines.append("## Dependências")
        lines.append("")
        
        # Imports
        import_edges = [e for e in self.graph.edges if e.type == EdgeType.IMPORT]
        if import_edges:
            lines.append("### Imports")
            for edge in import_edges:
                source = self.graph.get_node(edge.source_id)
                target = self.graph.get_node(edge.target_id)
                if source and target:
                    lines.append(f"- `{source.name}` → `{target.name}` ({edge.label})")
            lines.append("")

        # Chamadas de função
        call_edges = [e for e in self.graph.edges if e.type == EdgeType.CALLS]
        if call_edges:
            lines.append("### Chamadas de Função")
            for edge in call_edges:
                source = self.graph.get_node(edge.source_id)
                target = self.graph.get_node(edge.target_id)
                if source and target:
                    lines.append(f"- `{source.name}` → `{target.name}`")
            lines.append("")

        # Fluxo de dados: qual variável sai de uma função e entra em outra
        flow_edges = [e for e in self.graph.edges if e.type == EdgeType.DATA_FLOW]
        if flow_edges:
            lines.append("### Fluxo de Dados")
            lines.append("")
            lines.append("| Origem | Variável | Tipo | Destino |")
            lines.append("| --- | --- | --- | --- |")
            for edge in flow_edges:
                source = self.graph.get_node(edge.source_id)
                target = self.graph.get_node(edge.target_id)
                if source and target:
                    lines.append(
                        f"| `{source.name}` | `{edge.label}` "
                        f"| {edge.data_type or '—'} | `{target.name}` |"
                    )
            lines.append("")

        return "\n".join(lines)


class HTMLExporter(Exporter):
    """Exporta grafo para HTML interativo."""

    def export(self, output_path: str) -> None:
        """Exporta para HTML."""
        content = self._generate_html()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"✓ Grafo exportado para HTML: {output_path}")

    def _generate_html(self) -> str:
        """Gera HTML interativo."""
        # Preparar dados para Cytoscape
        elements = to_cytoscape(self.graph)
        nodes_data = elements["nodes"]
        edges_data = elements["edges"]

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise: {self.graph.project_name}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 300px;
            background: white;
            border-right: 1px solid #ddd;
            overflow-y: auto;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .header {{
            background: white;
            padding: 20px;
            border-bottom: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 10px;
        }}
        
        .stat {{
            background: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        
        #cy {{
            flex: 1;
            background: white;
        }}
        
        .sidebar h2 {{
            font-size: 16px;
            margin-bottom: 15px;
            color: #333;
        }}
        
        .sidebar h3 {{
            font-size: 12px;
            margin-top: 15px;
            margin-bottom: 10px;
            color: #666;
            text-transform: uppercase;
        }}
        
        .node-item {{
            padding: 8px;
            margin-bottom: 5px;
            background: #f9f9f9;
            border-left: 3px solid #007bff;
            cursor: pointer;
            border-radius: 2px;
            font-size: 12px;
        }}
        
        .node-item:hover {{
            background: #f0f0f0;
        }}
        
        .node-item.file {{
            border-left-color: #28a745;
        }}
        
        .node-item.function {{
            border-left-color: #007bff;
        }}
        
        .node-item.class {{
            border-left-color: #ffc107;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>{self.graph.project_name}</h2>
            <p style="font-size: 12px; color: #666; margin-bottom: 15px;">{self.graph.project_path}</p>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{self.graph.file_count}</div>
                    <div class="stat-label">Arquivos</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{self.graph.function_count}</div>
                    <div class="stat-label">Funções</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{self.graph.class_count}</div>
                    <div class="stat-label">Classes</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(self.graph.edges)}</div>
                    <div class="stat-label">Deps</div>
                </div>
            </div>
            
            <h3>Arquivos</h3>
            {self._generate_sidebar_items('file')}
            
            <h3>Funções</h3>
            {self._generate_sidebar_items('function')}
            
            <h3>Classes</h3>
            {self._generate_sidebar_items('class')}
        </div>
        
        <div class="main">
            <div class="header">
                <h1>Grafo de Dependências</h1>
                <p style="color: #666; font-size: 12px;">Clique nos nós para ver detalhes</p>
            </div>
            <div id="cy"></div>
        </div>
    </div>
    
    <script>
        const cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: {json.dumps(nodes_data + edges_data)},
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'content': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': 'data(color)',
                        'width': '60px',
                        'height': '60px',
                        'font-size': '10px',
                        'color': '#fff',
                        'text-wrap': 'wrap',
                        'text-max-width': '55px',
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'target-arrow-shape': 'triangle',
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'width': '2px',
                    }}
                }},
                {{
                    selector: 'edge[type = "uses"]',
                    style: {{
                        'line-color': '#e0e0e0',
                        'target-arrow-color': '#e0e0e0',
                        'width': '1px',
                    }}
                }},
                {{
                    selector: 'edge[type = "import"]',
                    style: {{
                        'line-color': '#6c757d',
                        'target-arrow-color': '#6c757d',
                        'line-style': 'dashed',
                    }}
                }},
                {{
                    selector: 'edge[type = "calls"]',
                    style: {{
                        'line-color': '#007bff',
                        'target-arrow-color': '#007bff',
                    }}
                }},
                {{
                    selector: 'edge[type = "data_flow"]',
                    style: {{
                        'line-color': '#28a745',
                        'target-arrow-color': '#28a745',
                        'width': '3px',
                        'label': 'data(label)',
                        'font-size': '9px',
                        'color': '#28a745',
                        'text-background-color': '#fff',
                        'text-background-opacity': 0.85,
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'background-color': '#ff6b6b',
                        'width': '80px',
                        'height': '80px',
                    }}
                }}
            ],
            layout: {{
                name: 'cose',
                directed: true,
                animate: true,
                animationDuration: 500,
            }}
        }});
        
        // Event listeners
        cy.on('tap', 'node', function(evt) {{
            const node = evt.target;
            console.log('Nó selecionado:', node.data());
        }});
    </script>
</body>
</html>"""
        return html



    def _generate_sidebar_items(self, node_type: str) -> str:
        """Gera itens da sidebar."""
        type_map = {
            "file": NodeType.FILE,
            "function": NodeType.FUNCTION,
            "class": NodeType.CLASS,
        }

        items = []
        for node in self.graph.nodes.values():
            if node.type == type_map.get(node_type):
                items.append(
                    f'<div class="node-item {node_type}" onclick="selectNode(\'{node.id}\')">{node.name}</div>'
                )

        return "\n".join(items) if items else "<p style='font-size: 12px; color: #999;'>Nenhum item</p>"


class CSVExporter(Exporter):
    """Exporta grafo para CSV."""

    def export(self, output_path: str) -> None:
        """Exporta para CSV."""
        import csv

        # Exportar nós
        nodes_path = output_path.replace(".csv", "_nodes.csv")
        with open(nodes_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id",
                "name",
                "type",
                "file_path",
                "line_number",
                "is_public",
                "complexity",
                "ai_category",
            ])
            for node in self.graph.nodes.values():
                writer.writerow([
                    node.id,
                    node.name,
                    node.type.value,
                    node.file_path,
                    node.line_number,
                    node.is_public,
                    node.complexity,
                    node.ai_category or "",
                ])

        # Exportar arestas
        edges_path = output_path.replace(".csv", "_edges.csv")
        with open(edges_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "source_id",
                "target_id",
                "type",
                "label",
                "weight",
            ])
            for edge in self.graph.edges:
                writer.writerow([
                    edge.source_id,
                    edge.target_id,
                    edge.type.value,
                    edge.label or "",
                    edge.weight,
                ])

        logger.info(f"✓ Grafo exportado para CSV: {nodes_path}, {edges_path}")
