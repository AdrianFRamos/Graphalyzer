# Project Analyzer - Guia da API

## 🚀 Iniciando o Servidor

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
python run_api.py
```

O servidor estará disponível em `http://localhost:5000`

## 📚 Documentação Interativa

Acesse a documentação interativa em: `http://localhost:5000/docs`

## 🔌 Endpoints da API

### 1. Analisar Projeto

**POST** `/api/analyze`

Analisa um projeto Python e gera grafo de dependências.

**Request Body:**
```json
{
  "project_path": "/caminho/do/projeto",
  "use_ai": false,
  "ai_provider": "claude",
  "ai_model": "claude-3-sonnet-20240229"
}
```

**Response:**
```json
{
  "analysis_id": "uuid-string",
  "status": "completed",
  "project_name": "meu_projeto",
  "file_count": 10,
  "function_count": 50,
  "class_count": 15,
  "edge_count": 200,
  "timestamp": "2024-07-31T11:40:36.841621"
}
```

### 2. Obter Detalhes da Análise

**GET** `/api/analysis/{analysis_id}`

Retorna informações sobre uma análise realizada.

**Response:**
```json
{
  "analysis_id": "uuid-string",
  "project_name": "meu_projeto",
  "project_path": "/caminho/do/projeto",
  "file_count": 10,
  "function_count": 50,
  "class_count": 15,
  "edge_count": 200,
  "timestamp": "2024-07-31T11:40:36.841621"
}
```

### 3. Obter Grafo em Formato Cytoscape

**GET** `/api/analysis/{analysis_id}/graph?view_type={type}`

Retorna grafo em formato compatível com Cytoscape.js.

**Parâmetros:**
- `view_type`: `file`, `function` ou `all`

**Response:**
```json
{
  "nodes": [
    {
      "data": {
        "id": "file::calculator.py",
        "label": "calculator",
        "type": "file",
        "color": "#28a745"
      }
    }
  ],
  "edges": [
    {
      "data": {
        "source": "file::calculator.py",
        "target": "func::calculator.py::add",
        "label": "contains"
      }
    }
  ]
}
```

### 4. Obter Detalhes de um Nó

**GET** `/api/analysis/{analysis_id}/node/{node_id}`

Retorna informações detalhadas sobre um nó específico.

**Response:**
```json
{
  "id": "func::calculator.py::add",
  "name": "add",
  "type": "function",
  "file_path": "calculator.py",
  "line_number": 5,
  "docstring": "Adds two numbers",
  "source_code": "def add(a: int, b: int) -> int:\n    return a + b",
  "parameters": [
    {
      "name": "a",
      "type": "int",
      "default": null
    },
    {
      "name": "b",
      "type": "int",
      "default": null
    }
  ],
  "return_type": "int",
  "complexity": 1,
  "ai_summary": "Simple addition function",
  "ai_category": "utility",
  "incoming_edges": 2,
  "outgoing_edges": 0
}
```

### 5. Obter Métricas

**GET** `/api/analysis/{analysis_id}/metrics`

Retorna métricas de arquitetura e qualidade.

**Response:**
```json
{
  "architecture": {
    "total_nodes": 50,
    "total_edges": 200,
    "average_connections": 4.0,
    "cyclomatic_complexity": 2.5,
    "coupling": 0.15,
    "cohesion": 0.85
  },
  "quality": {
    "documented_functions": 45,
    "total_functions": 50,
    "documentation_coverage": 0.9,
    "type_hints_coverage": 0.8,
    "average_complexity": 2.5
  },
  "dependencies": {
    "most_connected": [
      {
        "node_id": "func::main.py::process",
        "connections": 15
      }
    ],
    "isolated_count": 2
  }
}
```

### 6. Exportar Análise

**GET** `/api/analysis/{analysis_id}/export/{format}`

Exporta análise em diferentes formatos.

**Formatos suportados:**
- `json` - Grafo completo em JSON
- `md` - Documentação em Markdown
- `html` - Dashboard interativo em HTML
- `csv` - Tabelas em CSV

**Exemplo:**
```bash
curl http://localhost:5000/api/analysis/uuid-string/export/json > analysis.json
```

### 7. Deletar Análise

**DELETE** `/api/analysis/{analysis_id}`

Remove uma análise da memória.

**Response:**
```json
{
  "message": "Análise deletada"
}
```

### 8. Obter Estatísticas do Cache

**GET** `/api/cache/stats`

Retorna estatísticas do sistema de cache.

**Response:**
```json
{
  "cached_projects": 5,
  "cached_files": 50,
  "cached_analyses": 10,
  "in_memory_analyses": 3
}
```

### 9. Limpar Cache

**POST** `/api/cache/clear`

Limpa o cache de análises.

**Query Parameters (opcional):**
- `project_path` - Limpar cache de projeto específico

**Response:**
```json
{
  "message": "Cache limpo"
}
```

## 🌐 Interface Web

A interface web está disponível em `http://localhost:5000`

### Funcionalidades:

1. **Análise de Projeto**: Insira o caminho do projeto e clique em "Analisar"
2. **Visualização de Grafo**: Veja o grafo de dependências interativo
3. **Alternância de Visualização**: Mude entre vista de arquivos, funções ou tudo
4. **Layouts**: Escolha entre diferentes layouts (COSE, Grid, Círculo, Concêntrico)
5. **Detalhes de Nó**: Clique em um nó para ver detalhes completos
6. **Métricas**: Veja métricas de arquitetura e qualidade
7. **Exportação**: Exporte análise em JSON, Markdown, HTML ou CSV

## 📝 Exemplos de Uso

### Analisar Projeto com cURL

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "examples/sample_project",
    "use_ai": false
  }'
```

### Obter Grafo com Python

```python
import requests

response = requests.get(
    'http://localhost:5000/api/analysis/{analysis_id}/graph',
    params={'view_type': 'function'}
)
graph_data = response.json()
print(graph_data)
```

### Exportar para JSON

```bash
curl http://localhost:5000/api/analysis/{analysis_id}/export/json \
  -o analysis.json
```

## 🔐 Segurança

- A API não valida caminhos de projeto (use em ambiente confiável)
- Não há autenticação (adicione em produção)
- Análises são armazenadas em memória (perdidas ao reiniciar)

## 🐛 Troubleshooting

### Porta 5000 já em uso

```bash
# Encontrar processo usando porta 5000
lsof -i :5000

# Matar processo
kill -9 <PID>
```

### Erro ao importar módulos

```bash
# Verificar se está no diretório correto
cd /path/to/project_analyzer

# Reinstalar dependências
pip install -r requirements.txt
```

### Erro CORS

A API está configurada para aceitar requisições de qualquer origem. Se ainda tiver problemas, verifique o navegador e console.

## 📊 Estrutura de Dados

### Node ID Format

- Arquivo: `file::{file_path}`
- Função: `func::{file_path}::{function_name}`
- Classe: `class::{file_path}::{class_name}`
- Método: `method::{file_path}::{class_name}::{method_name}`

### Edge Types

- `import` - Import entre arquivos
- `calls` - Chamada de função
- `uses` - Uso/contenção
- `inherits` - Herança de classe
- `returns_to` - Retorno de função

## 🚀 Próximos Passos

1. Adicionar autenticação
2. Integrar banco de dados (PostgreSQL/MongoDB)
3. Suporte para WebSocket (atualizações em tempo real)
4. Análise com IA integrada
5. Histórico de análises
6. Compartilhamento de análises
