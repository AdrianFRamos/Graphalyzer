#!/usr/bin/env python3
"""
Script de teste para Fase 3 - Análise avançada de fluxo de dados e qualidade.
"""

from graphalyzer.analysis.data_flow import DataFlowAnalyzer, ParameterTracer, TypeInferencer
from graphalyzer.analysis.quality import QualityAnalyzer, SecurityAnalyzer, PerformanceAnalyzer
from graphalyzer.storage.cache import AnalysisCache
from graphalyzer.storage.reports import ArchitectureAnalyzer, QualityReportGenerator, DependencyReporter
from graphalyzer.analysis.builder import GraphBuilder

# Teste 1: Análise de Fluxo de Dados
print("=" * 60)
print("TESTE 1: Análise de Fluxo de Dados")
print("=" * 60)

sample_code = """
def add(a: int, b: int) -> int:
    result = a + b
    return result

def multiply(x: int, y: int) -> int:
    return x * y

def calculate(a: int, b: int) -> int:
    sum_result = add(a, b)
    prod_result = multiply(sum_result, 2)
    return prod_result
"""

analyzer = DataFlowAnalyzer(sample_code)
variables, flows = analyzer.analyze()

print(f"✓ Variáveis encontradas: {len(variables)}")
for var_name, var_info in variables.items():
    print(f"  - {var_name}: {var_info.type_hint or 'Any'}")

print(f"✓ Fluxos de dados encontrados: {len(flows)}")
for flow in flows:
    print(f"  - {flow.source_function} → {flow.target_function} (var: {flow.variable_name})")

# Teste 2: Análise de Qualidade
print("\n" + "=" * 60)
print("TESTE 2: Análise de Qualidade")
print("=" * 60)

quality_analyzer = QualityAnalyzer(sample_code)
issues = quality_analyzer.analyze()

print(f"✓ Problemas encontrados: {len(issues)}")
for issue in issues[:5]:
    print(f"  - [{issue.severity.value}] {issue.issue_type}: {issue.message}")

# Teste 3: Análise de Segurança
print("\n" + "=" * 60)
print("TESTE 3: Análise de Segurança")
print("=" * 60)

security_code = """
def unsafe_eval(user_input: str):
    result = eval(user_input)
    return result

def safe_json(user_input: str):
    import json
    result = json.loads(user_input)
    return result
"""

security_analyzer = SecurityAnalyzer(security_code)
security_issues = security_analyzer.analyze()

print(f"✓ Problemas de segurança encontrados: {len(security_issues)}")
for issue in security_issues:
    print(f"  - [{issue.severity.value}] {issue.issue_type}: {issue.message}")

# Teste 4: Análise de Performance
print("\n" + "=" * 60)
print("TESTE 4: Análise de Performance")
print("=" * 60)

perf_code = """
def nested_loops(n: int):
    for i in range(n):
        for j in range(n):
            for k in range(n):
                print(i, j, k)
"""

perf_analyzer = PerformanceAnalyzer(perf_code)
perf_issues = perf_analyzer.analyze()

print(f"✓ Problemas de performance encontrados: {len(perf_issues)}")
for issue in perf_issues:
    print(f"  - [{issue.severity.value}] {issue.issue_type}: {issue.message}")

# Teste 5: Cache
print("\n" + "=" * 60)
print("TESTE 5: Sistema de Cache")
print("=" * 60)

cache = AnalysisCache(".test_cache")
stats = cache.get_statistics()

print(f"✓ Cache inicializado")
print(f"  - Projetos em cache: {stats['cached_projects']}")
print(f"  - Arquivos em cache: {stats['cached_files']}")
print(f"  - Análises em cache: {stats['cached_analyses']}")

# Teste 6: Análise de Arquitetura
print("\n" + "=" * 60)
print("TESTE 6: Análise de Arquitetura")
print("=" * 60)

builder = GraphBuilder("examples/sample_project")
graph = builder.build()

arch_analyzer = ArchitectureAnalyzer(graph)
arch_metrics = arch_analyzer.analyze()

print(f"✓ Métricas de arquitetura calculadas")
print(f"  - Nós: {arch_metrics.total_nodes}")
print(f"  - Arestas: {arch_metrics.total_edges}")
print(f"  - Complexidade ciclomática média: {arch_metrics.cyclomatic_complexity:.2f}")
print(f"  - Acoplamento: {arch_metrics.coupling:.2%}")
print(f"  - Coesão: {arch_metrics.cohesion:.2%}")

# Teste 7: Relatório de Qualidade
print("\n" + "=" * 60)
print("TESTE 7: Relatório de Qualidade")
print("=" * 60)

quality_gen = QualityReportGenerator(graph)
quality_metrics = quality_gen.generate()

print(f"✓ Métricas de qualidade calculadas")
print(f"  - Funções documentadas: {quality_metrics.documented_functions}/{quality_metrics.total_functions}")
print(f"  - Cobertura de documentação: {quality_metrics.documentation_coverage:.1%}")
print(f"  - Cobertura de type hints: {quality_metrics.type_hints_coverage:.1%}")
print(f"  - Complexidade média: {quality_metrics.average_complexity:.2f}")

# Teste 8: Relatório de Dependências
print("\n" + "=" * 60)
print("TESTE 8: Relatório de Dependências")
print("=" * 60)

dep_reporter = DependencyReporter(graph)
most_connected = dep_reporter.get_most_connected_nodes(5)
isolated = dep_reporter.get_isolated_nodes()

print(f"✓ Análise de dependências concluída")
print(f"  - Nós mais conectados: {len(most_connected)}")
for node_id, connections in most_connected[:3]:
    print(f"    - {node_id}: {connections} conexões")
print(f"  - Nós isolados: {len(isolated)}")

print("\n" + "=" * 60)
print("✓ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
print("=" * 60)
