# 📖 Guia de Uso Prático - Project Analyzer

## 🎯 Objetivos deste Guia

Este guia fornece exemplos práticos de como usar o Project Analyzer em diferentes cenários.

## 📋 Índice

1. [Instalação](#instalação)
2. [Uso via CLI](#uso-via-cli)
3. [Uso via API Web](#uso-via-api-web)
4. [Uso como Biblioteca](#uso-como-biblioteca)
5. [Análise com IA](#análise-com-ia)
6. [Treinamento de Modelo](#treinamento-de-modelo)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Instalação

### Pré-requisitos

- Python 3.8+
- pip ou poetry
- 500MB de espaço em disco

### Passos

```bash
# 1. Clonar repositório
git clone <repo-url>
cd project_analyzer

# 2. Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Verificar instalação
python main.py --version
```

---

## 💻 Uso via CLI

### Exemplo 1: Análise Básica

Analisar um projeto e gerar todos os formatos:

```bash
python main.py ~/meu_projeto -o output -f all
```

**Resultado:**
```
✓ Análise concluída com sucesso!
📊 Estatísticas do Projeto:
   - Arquivos: 15
   - Funções: 120
   - Classes: 25
   - Dependências: 450
📂 Arquivos gerados em: /home/user/project_analyzer/output
```

**Arquivos gerados:**
- `output/analysis.json` - Grafo completo
- `output/analysis.md` - Documentação
- `output/analysis.html` - Dashboard interativo
- `output/analysis_nodes.csv` - Tabela de nós
- `output/analysis_edges.csv` - Tabela de dependências

### Exemplo 2: Exportar Apenas JSON

```bash
python main.py ~/meu_projeto -o output -f json
```

Útil para integração com outras ferramentas.

### Exemplo 3: Análise com IA (Claude)

```bash
# Definir chave de API
export ANTHROPIC_API_KEY="sk-ant-..."

# Executar análise
python main.py ~/meu_projeto -o output -ai --ai-provider claude
```

**Resultado adicional:**
- Cada função tem `ai_summary` e `ai_category`
- Documentação gerada automaticamente

### Exemplo 4: Análise com IA (OpenAI)

```bash
# Definir chave de API
export OPENAI_API_KEY="sk-..."

# Executar análise
python main.py ~/meu_projeto -o output -ai --ai-provider openai --ai-model gpt-4
```

### Exemplo 5: Projeto de Exemplo

```bash
# Analisar projeto de teste
python main.py examples/sample_project -o analysis_output -f all

# Abrir dashboard
open analysis_output/analysis.html
```

---

## 🌐 Uso via API Web

### Iniciar Servidor

```bash
python run_api.py
```

**Output:**
```
============================================================
Project Analyzer - API Server
============================================================

🚀 Iniciando servidor...
📍 URL: http://localhost:5000
📚 Documentação: http://localhost:5000/docs

Pressione Ctrl+C para parar o servidor
```

### Acessar Interface

1. **Dashboard**: http://localhost:5000
2. **Documentação**: http://localhost:5000/docs

### Exemplo 1: Analisar via cURL

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/home/user/meu_projeto",
    "use_ai": false
  }'
```

**Response:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "project_name": "meu_projeto",
  "file_count": 15,
  "function_count": 120,
  "class_count": 25,
  "edge_count": 450,
  "timestamp": "2024-07-31T11:40:36.841621"
}
```

### Exemplo 2: Obter Grafo

```bash
curl http://localhost:5000/api/analysis/550e8400-e29b-41d4-a716-446655440000/graph?view_type=function
```

### Exemplo 3: Exportar para JSON

```bash
curl http://localhost:5000/api/analysis/550e8400-e29b-41d4-a716-446655440000/export/json \
  -o analysis.json
```

### Exemplo 4: Usar Python Requests

```python
import requests

# Analisar
response = requests.post('http://localhost:5000/api/analyze', json={
    'project_path': '/home/user/meu_projeto',
    'use_ai': False
})
analysis_id = response.json()['analysis_id']

# Obter grafo
response = requests.get(
    f'http://localhost:5000/api/analysis/{analysis_id}/graph',
    params={'view_type': 'function'}
)
graph = response.json()

print(f"Nós: {len(graph['nodes'])}")
print(f"Arestas: {len(graph['edges'])}")
```

---

## 📚 Uso como Biblioteca

### Exemplo 1: Análise Básica

```python
from core.graph_builder import GraphBuilder
from storage.exporters import HTMLExporter

# Construir grafo
builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Exibir estatísticas
print(f"Arquivos: {graph.file_count}")
print(f"Funções: {graph.function_count}")
print(f"Classes: {graph.class_count}")

# Exportar para HTML
exporter = HTMLExporter(graph)
exporter.export("output.html")
```

### Exemplo 2: Análise de Qualidade

```python
from core.graph_builder import GraphBuilder
from storage.reports import QualityReportGenerator

builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Gerar relatório de qualidade
quality_gen = QualityReportGenerator(graph)
metrics = quality_gen.generate()

print(f"Documentação: {metrics.documentation_coverage:.1%}")
print(f"Type Hints: {metrics.type_hints_coverage:.1%}")
print(f"Complexidade Média: {metrics.average_complexity:.2f}")
```

### Exemplo 3: Análise de Arquitetura

```python
from core.graph_builder import GraphBuilder
from storage.reports import ArchitectureAnalyzer, ReportFormatter

builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Analisar arquitetura
analyzer = ArchitectureAnalyzer(graph)
metrics = analyzer.analyze()

# Gerar relatório
report = ReportFormatter.format_architecture_report(metrics)
print(report)
```

### Exemplo 4: Análise de Dependências

```python
from core.graph_builder import GraphBuilder
from storage.reports import DependencyReporter

builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Analisar dependências
reporter = DependencyReporter(graph)

# Nós mais conectados
most_connected = reporter.get_most_connected_nodes(10)
print("Nós mais conectados:")
for node_id, connections in most_connected[:5]:
    print(f"  {node_id}: {connections} conexões")

# Nós isolados
isolated = reporter.get_isolated_nodes()
print(f"\nNós isolados: {len(isolated)}")
```

### Exemplo 5: Análise com IA

```python
from core.graph_builder import GraphBuilder
from ai.analyzer import LLMAnalyzer
from core.data_models import NodeType

builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Criar analisador IA
ai = LLMAnalyzer(provider="claude", model="claude-3-sonnet-20240229")

# Analisar funções
functions = [n for n in graph.nodes.values() if n.type == NodeType.FUNCTION]

for func in functions[:5]:  # Primeiras 5 funções
    result = ai.analyze_function(func.name, func.source_code, func.docstring)
    print(f"\n{func.name}:")
    print(f"  Resumo: {result.summary}")
    print(f"  Categoria: {result.category}")
```

---

## 🤖 Análise com IA

### Configurar Chaves de API

**Claude (Anthropic):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**OpenAI:**
```bash
export OPENAI_API_KEY="sk-..."
```

### Modelos Disponíveis

**Claude:**
- `claude-3-opus-20240229` (mais poderoso)
- `claude-3-sonnet-20240229` (padrão, bom custo-benefício)
- `claude-3-haiku-20240307` (mais rápido)

**OpenAI:**
- `gpt-4` (mais poderoso)
- `gpt-4-turbo-preview`
- `gpt-3.5-turbo` (mais rápido)

### Exemplo: Análise Completa com IA

```python
from core.graph_builder import GraphBuilder
from ai.analyzer import LLMAnalyzer
from storage.exporters import MarkdownExporter
from core.data_models import NodeType

# Construir grafo
builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Analisar com IA
ai = LLMAnalyzer(provider="claude")

for node in graph.nodes.values():
    if node.type == NodeType.FUNCTION:
        result = ai.analyze_function(
            node.name,
            node.source_code,
            node.docstring
        )
        node.ai_summary = result.summary
        node.ai_category = result.category

# Exportar com análise IA
exporter = MarkdownExporter(graph)
exporter.export("documentation.md")
```

---

## 🎓 Treinamento de Modelo

### Gerar Dataset

```python
from ai.training_pipeline import DatasetGenerator
from core.graph_builder import GraphBuilder

# Construir grafo
builder = GraphBuilder("/home/user/meu_projeto")
graph = builder.build()

# Gerar dataset
generator = DatasetGenerator("training_data")
generator.add_examples_from_graph(graph)

# Exportar
generator.export_jsonl("training_data.jsonl")
generator.export_csv("training_data.csv")
generator.export_json("training_data.json")

# Ver estatísticas
stats = generator.get_statistics()
print(f"Exemplos: {stats['total_examples']}")
print(f"Categorias: {stats['categories']}")
```

### Treinar com OpenAI

```python
from ai.training_pipeline import ModelTrainer

trainer = ModelTrainer("meu_modelo_v1")

# Treinar
job_id = trainer.train_with_openai("training_data.jsonl")
print(f"Job ID: {job_id}")
print("Verifique o status em: https://platform.openai.com/fine_tuning/jobs")
```

### Treinar com Hugging Face

```python
from ai.training_pipeline import ModelTrainer

trainer = ModelTrainer("meu_modelo_v1")

# Treinar
model_path = trainer.train_with_huggingface(
    "training_data.jsonl",
    model="bert-base-uncased"
)
print(f"Modelo salvo em: {model_path}")
```

---

## 🐛 Troubleshooting

### Problema: "Módulo não encontrado"

**Solução:**
```bash
pip install -r requirements.txt
```

### Problema: "Porta 5000 já em uso"

**Solução:**
```bash
# Encontrar processo
lsof -i :5000

# Matar processo
kill -9 <PID>

# Ou usar porta diferente
python run_api.py --port 8000
```

### Problema: "Arquivo não encontrado"

**Solução:**
Use caminho absoluto:
```bash
python main.py /home/user/meu_projeto  # ✓ Correto
python main.py ~/meu_projeto           # ✓ Correto
python main.py ./meu_projeto           # ✗ Pode falhar
```

### Problema: "Sem permissão de leitura"

**Solução:**
```bash
chmod +r -R /caminho/do/projeto
```

### Problema: "ANTHROPIC_API_KEY não definida"

**Solução:**
```bash
# Verificar se está definida
echo $ANTHROPIC_API_KEY

# Definir
export ANTHROPIC_API_KEY="sk-ant-..."

# Ou usar em Python
import os
os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-...'
```

### Problema: "Análise muito lenta"

**Solução:**
- Excluir diretórios grandes: `venv/`, `node_modules/`, `.git/`
- Usar `-f json` em vez de `-f all`
- Desabilitar análise com IA: remover flag `-ai`

### Problema: "Erro de memória"

**Solução:**
- Analisar projetos menores primeiro
- Aumentar limite de memória do Python:
```bash
python -c "import sys; print(sys.maxsize)"
```

---

## 📞 Suporte

Para mais ajuda:

1. Consulte [API_GUIDE.md](API_GUIDE.md)
2. Veja [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
3. Abra uma issue no GitHub
4. Consulte os exemplos em `examples/`

---

**Última Atualização**: 31 de Julho de 2024
