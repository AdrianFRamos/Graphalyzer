#!/usr/bin/env python3
"""
Script de teste para Fase 4 - Análise com IA e Pipeline de Treinamento.
"""

from pathlib import Path

from graphalyzer.ai.training import (
    TrainingExample,
    DatasetGenerator,
    AnnotationTool,
    ModelTrainer,
    ModelEvaluator,
)
from graphalyzer.plugins.registry import PluginManager, PluginRegistry, ExampleAnalyzerPlugin
from graphalyzer.analysis.builder import GraphBuilder

print("=" * 60)
print("TESTE 1: Gerador de Dataset")
print("=" * 60)

# Criar exemplos de treinamento
generator = DatasetGenerator("test_training_data")

examples = [
    TrainingExample(
        code_snippet="def add(a: int, b: int) -> int:\n    return a + b",
        function_name="add",
        docstring="Adds two numbers",
        parameters=[
            {"name": "a", "type": "int"},
            {"name": "b", "type": "int"},
        ],
        return_type="int",
        summary="Simple addition function",
        category="utility",
        complexity=1,
    ),
    TrainingExample(
        code_snippet="def calculate_total(items: list) -> float:\n    return sum(items)",
        function_name="calculate_total",
        docstring="Calculates total from list",
        parameters=[{"name": "items", "type": "list"}],
        return_type="float",
        summary="Sums all items in a list",
        category="utility",
        complexity=1,
    ),
]

for example in examples:
    generator.add_example(example)

print(f"✓ {len(generator.examples)} exemplos adicionados")

# Adicionar exemplos do projeto de teste
print("\nCarregando exemplos do projeto...")
builder = GraphBuilder("examples/sample_project")
graph = builder.build()
generator.add_examples_from_graph(graph)

print(f"✓ Total de exemplos: {len(generator.examples)}")

# Exportar dataset
print("\nExportando dataset...")
generator.export_jsonl("training_data.jsonl")
generator.export_csv("training_data.csv")
generator.export_json("training_data.json")

# Estatísticas
stats = generator.get_statistics()
print(f"\n✓ Estatísticas do Dataset:")
print(f"  - Total de exemplos: {stats['total_examples']}")
print(f"  - Categorias: {stats['categories']}")
print(f"  - Complexidade média: {stats['average_complexity']:.2f}")
print(f"  - Parâmetros médios: {stats['average_parameters']:.2f}")

# Teste 2: Ferramenta de Anotação
print("\n" + "=" * 60)
print("TESTE 2: Ferramenta de Anotação")
print("=" * 60)

annotator = AnnotationTool("test_training_data/training_data.jsonl") if Path("test_training_data/training_data.jsonl").exists() else AnnotationTool("training_data.jsonl")

# Simular anotações
annotator.annotate(
    "example_1",
    summary="Addition function",
    category="utility",
    confidence=0.95,
)
annotator.annotate(
    "example_2",
    summary="Summation function",
    category="utility",
    confidence=0.90,
)

print(f"✓ {len(annotator.annotations)} anotações criadas")
annotator.save_annotations("test_training_data/annotations.json" if Path("test_training_data").exists() else "annotations.json")

# Teste 3: Configuração de Treinamento
print("\n" + "=" * 60)
print("TESTE 3: Configuração de Treinamento")
print("=" * 60)

trainer = ModelTrainer("code-analyzer-v1")

print(f"✓ Modelo: {trainer.model_name}")
print(f"  - Learning Rate: {trainer.training_config['learning_rate']}")
print(f"  - Batch Size: {trainer.training_config['batch_size']}")
print(f"  - Epochs: {trainer.training_config['epochs']}")
print(f"  - Max Sequence Length: {trainer.training_config['max_seq_length']}")

trainer.save_config("test_training_data/training_config.json" if Path("test_training_data").exists() else "training_config.json")

# Preparar dados
print("\nPreparing training data...")
data_split = trainer.prepare_training_data("test_training_data/training_data.jsonl" if Path("test_training_data/training_data.jsonl").exists() else "training_data.jsonl")
print(f"✓ Dados preparados:")
print(f"  - Treino: {len(data_split['train'])} exemplos")
print(f"  - Validação: {len(data_split['validation'])} exemplos")
print(f"  - Total: {data_split['total']} exemplos")

# Teste 4: Avaliador de Modelo
print("\n" + "=" * 60)
print("TESTE 4: Avaliador de Modelo")
print("=" * 60)

evaluator = ModelEvaluator("test_training_data/model" if Path("test_training_data").exists() else "model")
metrics = evaluator.evaluate(data_split["validation"])

print(f"✓ Métricas calculadas:")
for metric_name, metric_value in metrics.items():
    print(f"  - {metric_name}: {metric_value:.2%}")

report = evaluator.generate_report()
print(f"\n{report}")

# Teste 5: Sistema de Plugins
print("=" * 60)
print("TESTE 5: Sistema de Plugins")
print("=" * 60)

plugin_manager = PluginManager("test_plugins")

# Registrar plugin de exemplo
registry = PluginRegistry()
registry.register(
    "analyzer",
    "example",
    ExampleAnalyzerPlugin,
    {"version": "1.0.0", "description": "Example analyzer"},
)

print(f"✓ Plugin registrado: example_analyzer")

# Listar plugins
print(f"✓ Analisadores disponíveis: {registry.list_by_type('analyzer')}")

# Obter plugin
plugin_class = registry.get("analyzer", "example")
if plugin_class:
    plugin = plugin_class()
    result = plugin.analyze("def test(): pass", "test.py")
    print(f"✓ Plugin executado:")
    print(f"  - Resultado: {result}")

# Teste 6: Plugin Manager
print("\n" + "=" * 60)
print("TESTE 6: Plugin Manager")
print("=" * 60)

print(f"✓ Diretório de plugins: {plugin_manager.plugins_dir}")
print(f"✓ Analisadores carregados: {len(plugin_manager.analyzers)}")
print(f"✓ Exportadores carregados: {len(plugin_manager.exporters)}")

print("\n" + "=" * 60)
print("✓ TODOS OS TESTES DA FASE 4 CONCLUÍDOS!")
print("=" * 60)

print("\n📊 Resumo:")
print("- Dataset gerado com sucesso")
print("- Anotações criadas e salvas")
print("- Configuração de treinamento preparada")
print("- Métricas de avaliação calculadas")
print("- Sistema de plugins funcional")
print("\n✅ Fase 4 pronta para integração com IA!")
