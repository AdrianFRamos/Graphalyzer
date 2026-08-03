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
    <script src="https://unpkg.com/layout-base@2.0.1/layout-base.js"></script>
    <script src="https://unpkg.com/cose-base@2.2.0/cose-base.js"></script>
    <script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #16161e;
            color: #c0caf5;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 300px;
            background: #1a1b26;
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
            background: #1a1b26;
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
            background: #24283b;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #c0caf5;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #8b93a7;
            margin-top: 5px;
        }}
        
        #carregando {{
            position: fixed;
            inset: 0;
            display: grid;
            place-content: center;
            background: #16161e;
            color: #8b93a7;
            font-size: 14px;
            z-index: 999;
        }}
        #cy {{
            background: #1a1b26;
            flex: 1;
            background: #1a1b26;
        }}
        
        .sidebar h2 {{
            font-size: 16px;
            margin-bottom: 15px;
            color: #c0caf5;
        }}
        
        .sidebar h3 {{
            font-size: 12px;
            margin-top: 15px;
            margin-bottom: 10px;
            color: #8b93a7;
            text-transform: uppercase;
        }}
        
        .node-item {{
            padding: 8px;
            margin-bottom: 5px;
            background: #1f2335;
            border-left: 3px solid #007bff;
            cursor: pointer;
            border-radius: 2px;
            font-size: 12px;
        }}
        
        .node-item:hover {{
            background: #24283b;
        }}
        
        .node-item.file {{
            border-left-color: #4a7c59;
        }}
        
        .node-item.function {{
            border-left-color: #3d5a80;
        }}
        
        .node-item.class {{
            border-left-color: #e0af68;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>{self.graph.project_name}</h2>
            <p style="font-size: 12px; color: #8b93a7; margin-bottom: 15px;">{self.graph.project_path}</p>
            
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
                <p style="color: #8b93a7; font-size: 12px;">Passe o mouse para focar · dê zoom para ver os nomes</p>
            </div>
            <div id="cy"></div>
        </div>
    </div>
    
    <div id="carregando">Montando o grafo…</div>
    <script>
        // Extensões UMD costumam se auto-registrar, mas registrar de novo é
        // inofensivo e garante o fcose mesmo se a ordem de carga variar.
        if (typeof cytoscapeFcose !== 'undefined' && typeof cytoscape !== 'undefined') {{
            try {{ cytoscape.use(cytoscapeFcose); }} catch (e) {{ /* já registrado */ }}
        }}

        const elementos = {json.dumps(nodes_data + edges_data)};

        // Cor por pasta: mesma paleta e mesma ordenação do dashboard, para o
        // arquivo exportado e a tela não divergirem.
        const PALETA = ['#7aa2f7','#9ece6a','#e0af68','#bb9af7','#7dcfff','#f7768e',
                        '#73daca','#ff9e64','#c0caf5','#b4f9f8','#d19a66','#a6e3a1',
                        '#f5c2e7','#89dceb','#eba0ac','#94e2d5'];
        const pastas = [...new Set(elementos.filter(e => !e.data.source)
                        .map(e => e.data.folder || ''))].sort();
        const corDaPasta = {{}};
        pastas.forEach((p, i) => {{ corDaPasta[p] = PALETA[i % PALETA.length]; }});
        for (const el of elementos) {{
            if (!el.data.source) el.data.corDaPasta = corDaPasta[el.data.folder || ''];
        }}

        // Grau = nº de conexões. É o que dimensiona o nó, como no Obsidian.
        const grau = {{}};
        for (const el of elementos) {{
            if (el.data.source) {{
                grau[el.data.source] = (grau[el.data.source] || 0) + 1;
                grau[el.data.target] = (grau[el.data.target] || 0) + 1;
            }}
        }}
        for (const el of elementos) {{
            if (!el.data.source) el.data.grau = grau[el.data.id] || 0;
        }}

        const cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: elementos,
            wheelSensitivity: 0.2,
            minZoom: 0.08,
            maxZoom: 6,
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'background-color': 'data(corDaPasta)',
                        'width': 'mapData(grau, 0, 20, 7, 38)',
                        'height': 'mapData(grau, 0, 20, 7, 38)',
                        'border-width': 0,
                        'label': 'data(label)',
                        'font-size': 7,
                        'text-valign': 'bottom',
                        'text-margin-y': 4,
                        'color': '#c0caf5',
                        'text-opacity': 0,
                        'text-outline-width': 2,
                        'text-outline-color': '#1a1b26',
                        'min-zoomed-font-size': 6,
                    }}
                }},
                {{
                    selector: 'node[type = "file"]',
                    style: {{ 'border-width': 2, 'border-color': '#e8ecfb', 'border-opacity': 0.55 }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 0.6,
                        'line-color': '#3b4261',
                        'curve-style': 'straight',
                        'target-arrow-shape': 'none',
                        'opacity': 0.55,
                    }}
                }},
                {{ selector: 'edge[type = "data_flow"]', style: {{ 'line-color': '#4a7c59', 'width': 0.9 }} }},
                {{ selector: 'edge[type = "calls"]', style: {{ 'line-color': '#3d5a80' }} }},
                {{ selector: 'edge[type = "import"]', style: {{ 'line-color': '#4a4458', 'line-style': 'dashed' }} }},
                {{ selector: 'node.com-rotulo', style: {{ 'text-opacity': 0.9 }} }},
                {{ selector: '.apagado', style: {{ 'opacity': 0.08, 'text-opacity': 0 }} }},
                {{ selector: 'node.vizinho', style: {{ 'text-opacity': 0.95, 'z-index': 10 }} }},
                {{
                    selector: 'node.foco',
                    style: {{ 'background-color': '#f7768e', 'text-opacity': 1, 'z-index': 20 }}
                }},
                {{ selector: 'edge.vizinho', style: {{ 'opacity': 1, 'width': 1.4, 'line-color': '#f7768e' }} }}
            ],
            layout: {{
                // fcose, não cose: `cose` é O(n²) e trava o navegador em
                // projetos reais — 4 mil nós nunca terminavam de carregar.
                name: typeof cytoscapeFcose !== 'undefined' ? 'fcose' : 'cose',
                quality: elementos.length > 5000 ? 'draft' : 'default',
                numIter: elementos.length > 5000 ? 1000 : 2500,
                animate: false,
                randomize: true,
                nodeRepulsion: 6000,
                idealEdgeLength: 60,
                fit: true,
                padding: 50,
            }}
        }});

        // Órfãos num anel externo, em vez de vagarem pelo centro
        (function anelDeOrfaos() {{
            const orfaos = cy.nodes().filter(n => n.degree(false) === 0);
            if (!orfaos.length) return;
            const conectados = cy.nodes().difference(orfaos);
            const caixa = conectados.length
                ? conectados.boundingBox()
                : {{ x1: 0, y1: 0, w: 400, h: 400 }};
            const cx = caixa.x1 + caixa.w / 2;
            const cyy = caixa.y1 + caixa.h / 2;
            const raio = Math.max(caixa.w, caixa.h) / 2 + 90;
            orfaos.forEach((n, i) => {{
                const a = (2 * Math.PI * i) / orfaos.length;
                n.position({{ x: cx + raio * Math.cos(a), y: cyy + raio * Math.sin(a) }});
            }});
            cy.fit(undefined, 60);
        }})();

        // O layout roda síncrono na inicialização (animate: false), então o
        // evento `layoutstop` já passou aqui — remover direto é o que funciona.
        document.getElementById('carregando')?.remove();

        // Rótulos só com zoom
        function atualizarRotulos() {{
            const mostrar = cy.zoom() >= 1.4;
            cy.batch(() => cy.nodes().toggleClass('com-rotulo', mostrar));
        }}
        cy.on('zoom', atualizarRotulos);
        atualizarRotulos();

        // Foco na vizinhança
        cy.on('mouseover', 'node', function(e) {{
            const viz = e.target.closedNeighborhood();
            cy.batch(() => {{
                cy.elements().addClass('apagado');
                viz.removeClass('apagado').addClass('vizinho');
                e.target.removeClass('vizinho').addClass('foco');
            }});
        }});
        cy.on('mouseout', 'node', function() {{
            cy.batch(() => cy.elements().removeClass('apagado vizinho foco'));
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

        return "\n".join(items) if items else "<p style='font-size: 12px; color: #6b7394;'>Nenhum item</p>"


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
