"""
Gerador de relatórios avançados sobre qualidade e arquitetura.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

from graphalyzer.domain.models import ProjectGraph, NodeType, EdgeType


@dataclass
class ArchitectureMetrics:
    """Métricas de arquitetura."""
    total_nodes: int
    total_edges: int
    average_connections: float
    cyclomatic_complexity: float
    coupling: float
    cohesion: float


@dataclass
class QualityMetrics:
    """Métricas de qualidade."""
    documented_functions: int
    total_functions: int
    documentation_coverage: float
    type_hints_coverage: float
    average_complexity: float
    issues_count: int


class ArchitectureAnalyzer:
    """Analisa arquitetura do projeto."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    def analyze(self) -> ArchitectureMetrics:
        """Analisa arquitetura."""
        total_nodes = len(self.graph.nodes)
        total_edges = len(self.graph.edges)
        average_connections = total_edges / max(total_nodes, 1)

        # Complexidade ciclomática média
        complexities = [n.complexity for n in self.graph.nodes.values()]
        cyclomatic_complexity = sum(complexities) / len(complexities) if complexities else 0

        # Acoplamento (número de dependências externas)
        coupling = self._calculate_coupling()

        # Coesão (quão bem os componentes trabalham juntos)
        cohesion = self._calculate_cohesion()

        return ArchitectureMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            average_connections=average_connections,
            cyclomatic_complexity=cyclomatic_complexity,
            coupling=coupling,
            cohesion=cohesion,
        )

    def _calculate_coupling(self) -> float:
        """Calcula acoplamento."""
        import_edges = [e for e in self.graph.edges if e.type == EdgeType.IMPORT]
        total_edges = len(self.graph.edges)
        return len(import_edges) / max(total_edges, 1)

    def _calculate_cohesion(self) -> float:
        """Calcula coesão."""
        # Proporção de arestas internas vs externas
        internal_edges = [
            e for e in self.graph.edges
            if e.type in (EdgeType.CALLS, EdgeType.USES)
        ]
        total_edges = len(self.graph.edges)
        return len(internal_edges) / max(total_edges, 1)


class QualityReportGenerator:
    """Gera relatório de qualidade."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    def generate(self) -> QualityMetrics:
        """Gera relatório de qualidade."""
        functions = [n for n in self.graph.nodes.values() if n.type == NodeType.FUNCTION]
        total_functions = len(functions)

        # Cobertura de documentação
        documented = sum(1 for f in functions if f.docstring)
        documentation_coverage = documented / max(total_functions, 1)

        # Cobertura de type hints
        with_hints = sum(1 for f in functions if f.parameters and any(p.type_hint for p in f.parameters))
        type_hints_coverage = with_hints / max(total_functions, 1)

        # Complexidade média
        complexities = [f.complexity for f in functions]
        average_complexity = sum(complexities) / len(complexities) if complexities else 0

        return QualityMetrics(
            documented_functions=documented,
            total_functions=total_functions,
            documentation_coverage=documentation_coverage,
            type_hints_coverage=type_hints_coverage,
            average_complexity=average_complexity,
            issues_count=0,  # Será preenchido por analisador de qualidade
        )


class ReportFormatter:
    """Formata relatórios em diferentes formatos."""

    @staticmethod
    def format_architecture_report(metrics: ArchitectureMetrics) -> str:
        """Formata relatório de arquitetura."""
        report = """
# Relatório de Arquitetura

## Métricas Gerais
- **Total de Nós**: {total_nodes}
- **Total de Arestas**: {total_edges}
- **Conexões Médias**: {average_connections:.2f}

## Complexidade
- **Complexidade Ciclomática Média**: {cyclomatic_complexity:.2f}

## Acoplamento e Coesão
- **Acoplamento**: {coupling:.2%}
- **Coesão**: {cohesion:.2%}

## Interpretação
""".format(**metrics.__dict__)

        # Adicionar interpretação
        if metrics.cyclomatic_complexity > 5:
            report += "⚠️ **Complexidade Alta**: O projeto tem alta complexidade ciclomática. Considere refatorar.\n"
        else:
            report += "✅ **Complexidade Aceitável**: A complexidade está dentro dos limites recomendados.\n"

        if metrics.coupling > 0.5:
            report += "⚠️ **Acoplamento Alto**: Muitas dependências externas. Considere melhorar a modularização.\n"
        else:
            report += "✅ **Acoplamento Baixo**: Boa separação de responsabilidades.\n"

        if metrics.cohesion > 0.7:
            report += "✅ **Coesão Alta**: Os componentes trabalham bem juntos.\n"
        else:
            report += "⚠️ **Coesão Baixa**: Considere reorganizar os componentes.\n"

        return report

    @staticmethod
    def format_quality_report(metrics: QualityMetrics) -> str:
        """Formata relatório de qualidade."""
        report = """
# Relatório de Qualidade

## Documentação
- **Funções Documentadas**: {documented_functions}/{total_functions}
- **Cobertura de Documentação**: {documentation_coverage:.1%}

## Type Hints
- **Cobertura de Type Hints**: {type_hints_coverage:.1%}

## Complexidade
- **Complexidade Média**: {average_complexity:.2f}

## Problemas Encontrados
- **Total de Problemas**: {issues_count}

## Recomendações
""".format(**metrics.__dict__)

        if metrics.documentation_coverage < 0.5:
            report += "📝 Adicione documentação para mais funções. Objetivo: >80%\n"
        elif metrics.documentation_coverage < 0.8:
            report += "📝 Melhore a cobertura de documentação. Objetivo: >80%\n"
        else:
            report += "✅ Excelente cobertura de documentação!\n"

        if metrics.type_hints_coverage < 0.5:
            report += "🔍 Adicione type hints para melhor qualidade de código.\n"
        elif metrics.type_hints_coverage < 0.8:
            report += "🔍 Aumente a cobertura de type hints.\n"
        else:
            report += "✅ Ótima cobertura de type hints!\n"

        if metrics.average_complexity > 5:
            report += "⚙️ Reduza a complexidade média das funções.\n"
        else:
            report += "✅ Complexidade dentro dos limites recomendados.\n"

        return report


class DependencyReporter:
    """Gera relatório de dependências."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

    def get_most_connected_nodes(self, top_n: int = 10) -> List[tuple]:
        """Obtém nós mais conectados."""
        connections = {}

        for node in self.graph.nodes.values():
            outgoing = len(self.graph.get_edges_from(node.id))
            incoming = len(self.graph.get_edges_to(node.id))
            connections[node.id] = outgoing + incoming

        sorted_nodes = sorted(connections.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]

    def get_isolated_nodes(self) -> List[str]:
        """Obtém nós isolados (sem conexões)."""
        isolated = []

        for node in self.graph.nodes.values():
            if not self.graph.get_edges_from(node.id) and not self.graph.get_edges_to(node.id):
                isolated.append(node.id)

        return isolated

    def get_dependency_chains(self, max_depth: int = 3) -> Dict[str, List[List[str]]]:
        """Obtém cadeias de dependência."""
        chains = {}

        for node in self.graph.nodes.values():
            if node.type == NodeType.FUNCTION:
                chains[node.id] = self._find_chains(node.id, max_depth)

        return chains

    def _find_chains(self, node_id: str, max_depth: int, current_depth: int = 0, visited: set = None) -> List[List[str]]:
        """Encontra cadeias de dependência."""
        if visited is None:
            visited = set()

        if current_depth >= max_depth or node_id in visited:
            return []

        visited.add(node_id)
        chains = []

        for edge in self.graph.get_edges_from(node_id):
            target_node = self.graph.get_node(edge.target_id)
            if target_node:
                chains.append([node_id, edge.target_id])

                # Recursivamente encontrar cadeias mais longas
                sub_chains = self._find_chains(
                    edge.target_id,
                    max_depth,
                    current_depth + 1,
                    visited.copy(),
                )
                for sub_chain in sub_chains:
                    chains.append([node_id] + sub_chain)

        return chains
