# Project Analyzer - Resumo do Projeto

## 📋 Visão Geral

**Project Analyzer** é um sistema completo para análise de projetos Python que gera grafos de dependências, visualiza fluxo de dados e cria documentação automática com suporte a IA.

## 🎯 Objetivo

Criar um analisador similar ao Obsidian que:
- Mapeia automaticamente a arquitetura do código
- Visualiza dependências em grafos interativos
- Rastreia fluxo de dados entre funções
- Integra análise com IA (Claude/GPT)
- Prepara estrutura para treinar modelo próprio

## 📁 Estrutura do Projeto

```
project_analyzer/
├── core/                           # Núcleo de análise
│   ├── data_models.py             # Modelos de dados (Node, Edge, Graph)
│   ├── parser.py                  # Parser Python com AST
│   ├── extractor.py               # Extrator de dependências
│   ├── graph_builder.py           # Construtor de grafo
│   ├── data_flow_analyzer.py      # Análise de fluxo de dados
│   ├── quality_analyzer.py        # Análise de qualidade
│   └── plugin_system.py           # Sistema de plugins
│
├── ai/                             # Análise com IA
│   ├── analyzer.py                # Interface abstrata + implementações
│   └── training_pipeline.py       # Pipeline para treinar modelo próprio
│
├── storage/                        # Persistência e exportação
│   ├── cache.py                   # Cache com SQLite
│   ├── exporters.py               # Exportadores (JSON, MD, HTML, CSV)
│   └── reports.py                 # Gerador de relatórios
│
├── api/                            # API FastAPI
│   └── app.py                     # 9 endpoints RESTful
│
├── frontend/                       # Interface web
│   ├── index.html                 # Dashboard
│   ├── styles.css                 # Design responsivo
│   └── app.js                     # Lógica interativa
│
├── examples/                       # Projetos de teste
│   └── sample_project/            # Calculadora com testes
│
├── tests/                          # Testes unitários
├── main.py                         # CLI principal
├── run_api.py                      # Script para iniciar API
├── requirements.txt                # Dependências
├── README.md                       # Documentação principal
├── API_GUIDE.md                    # Guia da API
└── PROJECT_SUMMARY.md             # Este arquivo
```

## 🔧 Componentes Principais

### 1. Análise Estática (Core)
- **Parser**: Extrai funções, classes, imports usando AST
- **Extractor**: Identifica dependências e fluxo de dados
- **Graph Builder**: Constrói grafo de dependências completo
- **Quality Analyzer**: Detecta problemas de qualidade
- **Data Flow Analyzer**: Rastreia fluxo de variáveis

### 2. Análise com IA (AI)
- **LLM Analyzer**: Integração com Claude/OpenAI
- **Training Pipeline**: Gera dataset para treinar modelo próprio
- **Annotation Tool**: Ferramenta para anotar dados manualmente
- **Model Trainer**: Suporta fine-tuning com OpenAI/Hugging Face

### 3. Persistência (Storage)
- **Cache**: SQLite com hash SHA256 para detectar mudanças
- **Exporters**: JSON, Markdown, HTML interativo, CSV
- **Reports**: Métricas de arquitetura, qualidade e dependências

### 4. API (FastAPI)
- 9 endpoints RESTful
- CORS habilitado
- Suporte a múltiplos formatos de exportação
- Documentação automática em /docs

### 5. Interface Web
- Dashboard com Cytoscape.js
- Visualização interativa de grafos
- Alternância entre vistas (arquivo/função)
- Painel de detalhes de nós
- Métricas em tempo real

## 📊 Fases Completadas

### ✅ Fase 1: Arquitetura e Requisitos
- Definição de escopo
- Design de arquitetura em 6 camadas
- Seleção de tecnologias

### ✅ Fase 2: Núcleo de Análise Estática
- Parser Python com AST
- Extrator de dependências
- Construtor de grafo
- Modelos de dados robustos

### ✅ Fase 3: Análise Avançada
- Análise de fluxo de dados
- Análise de qualidade de código
- Análise de segurança
- Análise de performance
- Sistema de cache

### ✅ Fase 4: IA e Pipeline de Treinamento
- Interface abstrata para IA
- Integração com Claude/OpenAI
- Gerador de dataset (JSONL, CSV, JSON)
- Ferramenta de anotação manual
- Pipeline de treinamento com OpenAI/Hugging Face
- Sistema de plugins

### ✅ Fase 5: Interface Web e API
- API FastAPI com 9 endpoints
- Dashboard web interativo
- Visualização de grafos com Cytoscape.js
- Exportação em 4 formatos
- Documentação da API

### 🔄 Fase 6: Validação e Documentação (Em Progresso)
- Testes de integração
- Documentação completa
- Guias de uso
- Exemplos práticos

## 🚀 Como Usar

### CLI
```bash
# Análise básica
python main.py /caminho/do/projeto -o output -f all

# Com análise de IA
python main.py /caminho/do/projeto -ai --ai-provider claude
```

### API
```bash
# Iniciar servidor
python run_api.py

# Acessar interface
# Browser: http://localhost:5000
# Docs: http://localhost:5000/docs
```

### Como Biblioteca
```python
from core.graph_builder import GraphBuilder
from storage.exporters import HTMLExporter

builder = GraphBuilder("meu_projeto")
graph = builder.build()

exporter = HTMLExporter(graph)
exporter.export("output.html")
```

## 📈 Métricas Coletadas

### Arquitetura
- Complexidade ciclomática
- Acoplamento
- Coesão
- Número de nós e arestas

### Qualidade
- Cobertura de documentação
- Cobertura de type hints
- Complexidade média
- Problemas encontrados

### Dependências
- Nós mais conectados
- Nós isolados
- Cadeias de dependência
- Dependências transitivas

## 🔌 Extensibilidade

### Sistema de Plugins
```python
from core.plugin_system import AnalyzerPlugin

class MeuAnalyzer(AnalyzerPlugin):
    @property
    def name(self):
        return "meu_analyzer"
    
    def analyze(self, code, filename):
        # Sua lógica aqui
        return {}
```

### Novos Exportadores
```python
from storage.exporters import Exporter

class MeuExporter(Exporter):
    def export(self, output_path):
        # Sua lógica aqui
        pass
```

## 🔐 Segurança

- Validação de entrada (caminho de projeto)
- Sem acesso a arquivos fora do projeto
- Cache com hash SHA256
- Sem armazenamento de credenciais

## 🐛 Testes

```bash
# Testes da Fase 3
python test_phase3.py

# Testes da Fase 4
python test_phase4.py
```

## 📚 Documentação

- **README.md**: Documentação principal
- **API_GUIDE.md**: Guia completo da API
- **PROJECT_SUMMARY.md**: Este arquivo

## 🎓 Próximos Passos

1. **Banco de Dados**: Migrar de memória para PostgreSQL
2. **Autenticação**: Adicionar OAuth2
3. **WebSocket**: Atualizações em tempo real
4. **Histórico**: Manter histórico de análises
5. **Compartilhamento**: Compartilhar análises entre usuários
6. **Modelo Próprio**: Treinar modelo customizado
7. **CLI Avançada**: Mais opções e configurações
8. **Integração IDE**: Plugins para VS Code, PyCharm

## 📦 Dependências

```
anthropic>=0.7.0
openai>=1.0.0
flask>=3.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

MIT

## 👨‍💻 Desenvolvido por

**Manus AI**

---

**Status**: MVP Completo ✅
**Versão**: 1.0.0
**Data**: 31 de Julho de 2024
