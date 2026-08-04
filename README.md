# Graphalyzer 🔍

Um **analisador de projetos** que gera grafos de dependências, visualiza fluxo de dados e cria documentação automática com suporte a IA — em **15 linguagens**.

## 🎯 Características

- ✅ **15 linguagens**: Python, Dart, TypeScript, JavaScript, Go, Java, Kotlin, Rust, C#, Ruby, PHP, Swift, C, C++
- ✅ **Análise Estática**: AST para extrair funções, classes, imports e dependências
- ✅ **Grafo de Dependências**: Visualiza relações entre arquivos, funções e classes
- ✅ **Fluxo de Dados**: Rastreia parâmetros, tipos de retorno e fluxo de variáveis
- ✅ **Análise com IA**: Integração com Claude/GPT para análise semântica automática
- ✅ **Múltiplos Formatos**: Exporta para JSON, Markdown, HTML interativo e CSV
- ✅ **Complexidade**: Calcula complexidade ciclomática de funções
- ✅ **Preparado para ML**: Estrutura pronta para treinar modelo próprio

## 📁 Arquitetura

Aplicação em camadas. Cada camada só depende das de dentro — a seta nunca volta.

```
domain  ←  analysis  ←  services  ←  api / cli
   ↑                        ↑
   └────  storage  ─────────┘
              ↑
             ai
```

```
graphalyzer/
├── pyproject.toml             # Pacote, dependências e entry points
├── src/graphalyzer/
│   ├── config.py             # Configuração (sobrescrevível por GRAPHALYZER_*)
│   ├── console.py            # Logging e encoding — só para entry points
│   │
│   ├── domain/               # Modelos puros, sem I/O
│   │   ├── models.py         #   Node, Edge, ProjectGraph
│   │   └── views.py          #   Grafo → Cytoscape
│   │
│   ├── analysis/             # AST → grafo
│   │   ├── parser.py         #   Arquivo → funções, classes, imports
│   │   ├── extractor.py      #   Chamadas, imports, complexidade
│   │   ├── data_flow.py      #   Variáveis de entrada/saída entre funções
│   │   ├── quality.py        #   Métricas de qualidade
│   │   └── builder.py        #   Tabela de símbolos + montagem do grafo
│   │
│   ├── ai/                   # Enriquecimento semântico
│   │   ├── analyzer.py       #   Claude / OpenAI / mock
│   │   └── training.py       #   Dataset e fine-tuning
│   │
│   ├── storage/              # Persistência e exportação
│   │   ├── exporters.py      #   JSON, Markdown, HTML, CSV
│   │   ├── reports.py        #   Relatórios de arquitetura e qualidade
│   │   └── cache.py          #   Cache SQLite com invalidação por mtime
│   │
│   ├── plugins/registry.py   # Analisadores e exportadores customizados
│   │
│   ├── services/analysis.py  # Orquestração — único ponto que combina camadas
│   │
│   ├── api/                  # Interface HTTP
│   │   ├── app.py            #   Fábrica da aplicação
│   │   ├── schemas.py        #   Contratos de entrada/saída
│   │   └── routes/           #   Endpoints por recurso
│   │
│   ├── web/                  # Dashboard compilado (gerado por frontend/)
│   ├── cli.py                # Entry point: graphalyzer
│   └── server.py             # Entry point: graphalyzer-api
│
├── Dockerfile                 # Build multi-stage (Node compila, Python roda)
├── docker-compose.yml         # Porta presa em 127.0.0.1, projeto read-only
│
├── frontend/                  # Fonte do dashboard (Vue 3 + Vite + PWA)
│   ├── src/components/       #   GraphCanvas, SidePanel, NodeDetails
│   ├── src/store.js          #   Estado reativo + persistência offline
│   └── vite.config.js        #   Build sai em src/graphalyzer/web/
│
├── tests/                     # Um arquivo por camada
├── scripts/                   # Demos manuais
├── docs/                      # Documentação adicional
└── examples/sample_project/   # Projeto de teste
```

**Regras da arquitetura:**

- `domain` não importa nada do projeto — é o núcleo.
- `analysis`, `ai` e `storage` só conhecem `domain`.
- `services` é o único lugar que combina camadas; toda regra de orquestração mora ali.
- `api` e `cli` são cascas finas: validam entrada, chamam `services`, formatam saída.
- Camadas internas usam `logging` e **nunca** escrevem em stdout — só os entry points imprimem.

> Ainda não ligados a nenhum fluxo: `plugins/registry.py` e `ai/training.py`.
> Existem e funcionam isolados, mas nem CLI nem API os invocam.

## 🌍 Linguagens suportadas

| Linguagem | Extensões | Motor |
| --- | --- | --- |
| Python | `.py` | `ast` da stdlib |
| Dart | `.dart` | tree-sitter |
| TypeScript | `.ts` `.tsx` `.mts` | tree-sitter |
| JavaScript | `.js` `.jsx` `.mjs` | tree-sitter |
| Go | `.go` | tree-sitter |
| Java | `.java` | tree-sitter |
| Kotlin | `.kt` `.kts` | tree-sitter |
| Rust | `.rs` | tree-sitter |
| C# | `.cs` | tree-sitter |
| Ruby | `.rb` | tree-sitter |
| PHP | `.php` | tree-sitter |
| Swift | `.swift` | tree-sitter |
| C / C++ | `.c` `.h` `.cpp` `.hpp` | tree-sitter |

Um repositório com várias linguagens entra **todo no mesmo grafo** — o backend
Python e o app Flutter aparecem juntos.

Python usa o `ast` da stdlib de propósito: resolve escopo, defaults e
anotações com precisão que uma gramática genérica não alcança, e o fluxo de
dados dele infere também o tipo da variável de origem. Nas demais linguagens o
tipo vem do parâmetro de destino (peso 0.6 na aresta, contra 0.8 do Python).

### Acrescentar uma linguagem

É uma entrada em `analysis/languages/specs.py`, não um analisador novo:

```python
"elixir": LanguageSpec(
    name="elixir",
    label="Elixir",
    extensions=(".ex", ".exs"),
    functions=("call",),
    classes=("call",),
    imports=("call",),
    calls=("call",),
    parameter_lists=("arguments",),
    parameters=("identifier",),
),
```

## 🚀 Instalação

Requer Python 3.10+.

```bash
# Núcleo: análise em todas as linguagens + exportação
pip install -e .

# Com API e dashboard
pip install -e ".[api]"

# Com IA e ferramentas de desenvolvimento
pip install -e ".[api,ai,dev]"
```

## 💻 Uso

### CLI

```bash
# Analisar um projeto
graphalyzer /caminho/do/projeto

# Escolher saída e formato
graphalyzer /caminho/do/projeto -o meu_output -f markdown

# Com análise semântica por IA
graphalyzer /caminho/do/projeto -ai --ai-provider claude
```

Formatos: `json`, `markdown`, `html`, `csv`, `docs`, `pdf` ou `all` (padrão).

### Dashboard e API

```bash
graphalyzer-api
```

Dashboard em `http://127.0.0.1:5000`, documentação da API em `/docs`.
Para mudar a porta: `graphalyzer-api --port 8080` ou `GRAPHALYZER_PORT=8080`.

> A API lê arquivos arbitrários do disco e não tem autenticação. Por isso
> escuta apenas em `127.0.0.1`. Não exponha na rede.

### Exemplo

```bash
graphalyzer examples/sample_project -o analysis_output -f all
```

## 🖥️ Dashboard (PWA)

O dashboard é um app Vue 3 instalável. O build sai direto em
`src/graphalyzer/web/`, que é o que a API serve — por isso já vem pronto e
**Node só é necessário para alterar o frontend**.

```bash
cd frontend
npm install
npm run build      # gera o dashboard em src/graphalyzer/web/
npm run dev        # desenvolvimento, com proxy para a API na 5000
```

### Instalável e offline

Abra `http://127.0.0.1:5000` e use "Instalar aplicativo" no navegador.

A análise **precisa** do servidor local — é ele que lê o disco. O que funciona
offline é a consulta: o app guarda a última análise no dispositivo e a restaura
ao abrir sem conexão, com o grafo, as métricas e os detalhes de nó já visitados.
Para uma ferramenta de documentação é o caso de uso que importa — consultar o
que já foi analisado.

O Cytoscape é empacotado no bundle, não vem de CDN. Sem isso o modo offline
não existiria.

## ⚡ Cache

Ligado por padrão. A segunda análise do mesmo projeto reaproveita o grafo
guardado em SQLite, e o resultado sobrevive a reinício do container.

```
1a analise :   53.5s   (constroi o grafo)
2a analise :    3.3s   (do cache)          → 16x
apos restart:   2.6s   (do cache)
```

**Invalidação** por impressão digital do projeto: caminho, tamanho e data de
modificação de cada arquivo de código. Não lê o conteúdo — se lesse, verificar
custaria o mesmo que analisar e o cache não pagaria o próprio custo. Pastas de
dependência (`node_modules`, `build`, `.dart_tool`...) ficam de fora, senão um
`npm install` invalidaria tudo.

Editar, adicionar ou remover qualquer arquivo invalida na hora.

```bash
graphalyzer /caminho --no-cache          # ignora e reanalisa
curl -X POST http://127.0.0.1:5000/api/cache/clear
curl http://127.0.0.1:5000/api/cache/stats
```

Na API: `{"project_path": "...", "use_cache": false}`. A resposta traz
`from_cache`, então dá para saber se veio pronto.

> Um grafo guardado sem análise de IA não é devolvido para quem pediu com IA.

## 🤖 Análise por IA

Opcional. Com uma chave configurada, a IA resume **cada arquivo** e avalia a
**organização do projeto** — e o resultado entra na documentação exportada.

### Configurando a chave

No dashboard, painel **Análise por IA** na barra lateral. Ou por variável de
ambiente, que é a forma de persistir:

```bash
ANTHROPIC_API_KEY=sk-ant-...    # ou OPENAI_API_KEY
```

**A chave enviada pelo dashboard fica só na memória do processo.** Não vai para
disco, log, cache nem resposta de API — nem mascarada — e some ao reiniciar o
servidor. Isso é deliberado: gravá-la transformaria um segredo de sessão em
segredo persistido, com backup e tudo. O navegador também não a guarda.

### O que a IA acrescenta

| Onde | O quê |
| --- | --- |
| Responsabilidade de cada arquivo | Uma frase sobre o papel dele, quando não há docstring |
| Notas de implementação | Observação sobre acoplamento, risco ou padrão notável |
| Visão geral do projeto | Organização, pontos de atenção e sugestões — no índice e na capa do PDF |

O que é enviado ao modelo é a **estrutura extraída** (assinaturas, imports,
relações), não o código-fonte inteiro: mais barato e menos exposto.

### Custo

Uma chamada por **arquivo**, não por função — a diferença entre ~100 e vários
milhares num projeto real. As respostas são endereçadas pelo conteúdo do
pedido: arquivo que não mudou não é reanalisado, mesmo que o resto do projeto
tenha mudado. As chamadas rodam em paralelo (6 por vez).

Sem chave, a análise segue normalmente — só perde o enriquecimento. Nada é
inventado no lugar.

## 📘 Documentação gerada

O produto final da extração: um documento por arquivo de código, com a mesma
estrutura em qualquer formato.

```bash
graphalyzer /caminho/do/projeto -f pdf      # documento único, com capa e sumário
graphalyzer /caminho/do/projeto -f docs     # um Markdown por arquivo + índice
```

Cada documento traz:

| Seção | De onde sai |
| --- | --- |
| **Responsabilidade** | Docstring do módulo, resumo da IA ou a estrutura extraída |
| **Inputs** | Imports e os parâmetros das rotinas públicas, com tipo |
| **Processamento** | Classes e funções numeradas, com complexidade ciclomática |
| **Outputs** | Tipos de retorno e as variáveis que alimentam outros arquivos |
| **Relacionamentos** | Arquivos ligados por import, chamada ou fluxo de dados |
| **Notas** | Complexidade, cobertura de docstring, rotinas internas |

O modelo do documento é montado uma vez e renderizado depois, então Markdown e
PDF **nunca divergem no conteúdo** — só na apresentação. O Markdown usa links
padrão (`[nome](nome.md)`), que funcionam em qualquer visualizador, inclusive
no Obsidian, sem depender dele.

> Nada é inventado. Sem docstring, a responsabilidade descreve o que foi
> extraído ("Define 2 classes") em vez de supor a intenção do código.

## 🐳 Docker

```bash
docker compose up -d --build
```

Dashboard em `http://127.0.0.1:5000`. Imagem final de 205 MB, sem Node —
o frontend é compilado num estágio descartado.

### Analisando os seus projetos

O container só enxerga o que você montar. Aponte o volume para o projeto e,
no dashboard, informe o caminho **de dentro do container**:

```yaml
volumes:
  - /caminho/no/host/meu-projeto:/projects/meu-projeto:ro
```

```
Caminho no dashboard:  /projects/meu-projeto
```

Pela CLI, sem subir servidor:

```bash
docker run --rm   -v /caminho/no/host/meu-projeto:/projects/meu-projeto:ro   -v graphalyzer-data:/data   graphalyzer:latest   graphalyzer /projects/meu-projeto -o /data/out -f all
```

### Segurança

O container é a camada de isolamento que faltava — mas **a publicação da porta
é o que realmente protege**:

```yaml
ports:
  - "127.0.0.1:5000:5000"   # correto
# - "5000:5000"             # expõe na rede: leitura de disco sem autenticação
```

Dentro do container o processo escuta em `0.0.0.0` porque, isolado na rede do
container, é a única forma de a porta publicada alcançá-lo. As demais travas:

- roda como usuário sem privilégio (`uid 1000`), não root;
- código a analisar montado somente leitura;
- `/data` é a única área gravável;
- `no-new-privileges`, e teto de 2 GB de memória.

## 📊 Saídas Geradas

### JSON
Grafo completo em formato JSON com todos os nós, arestas e metadados.

```json
{
  "project_name": "sample_project",
  "project_path": "/path/to/project",
  "nodes": {
    "file::calculator.py": {
      "id": "file::calculator.py",
      "name": "calculator",
      "type": "file",
      ...
    }
  },
  "edges": [...]
}
```

### Markdown
Documentação legível em Markdown com estatísticas, funções, classes e dependências.

### HTML Interativo
Dashboard com grafo interativo usando Cytoscape.js. Permite:
- Visualizar nós e arestas
- Clicar para selecionar
- Sidebar com lista de arquivos, funções e classes
- Estatísticas do projeto

### CSV
Exportação tabulada para análise em Excel/Sheets:
- `analysis_nodes.csv`: Todos os nós com metadados
- `analysis_edges.csv`: Todas as dependências

## 🤖 Análise com IA

### Modelos Suportados

**Claude (Anthropic)**
- `claude-opus-5`
- `claude-sonnet-5` (padrão)
- `claude-haiku-4-5-20251001`

**OpenAI**
- qualquer modelo aceito pelo endpoint `chat.completions`

### Variáveis de Ambiente

```bash
# Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."
```

## 📈 Métricas Coletadas

- **Complexidade Ciclomática**: Mede a complexidade de cada função
- **Dependências**: Rastreia imports e chamadas de função
- **Fluxo de Dados**: Parâmetros → Retornos
- **Categorização**: Classifica componentes (utility, core, api, test)
- **Cobertura**: Estatísticas de arquivos, funções e classes

## 🔮 Próximas Fases

### Fase 2: Análise Estática ✅ (Completo)
- [x] Parser AST Python
- [x] Extrator de dependências
- [x] Construtor de grafo
- [x] Cálculo de complexidade

### Fase 3: Análise com IA ✅ (Completo)
- [x] Interface abstrata para IA
- [x] Integração Claude/OpenAI
- [x] Análise semântica de funções/classes

### Fase 4: Visualização ✅ (Completo)
- [x] Dashboard web local
- [x] Grafo interativo (Cytoscape.js)
- [x] Alternância arquivo ↔ função
- [x] Pop-up do nó com assinatura, entradas e saídas, e navegação entre nós
- [x] Arestas de fluxo de dados com nome e tipo da variável
- [ ] Filtros e busca

### Fase 5: API Local ✅ (Completo)
- [x] FastAPI backend
- [x] Endpoints REST
- [ ] WebSocket para atualizações em tempo real
- [ ] Upload de projetos
- [x] Cache SQLite ligado, com invalidação por mtime

### Fase 6: Treinamento de Modelo Próprio 📋 (Planejado)
- [ ] Gerador de dataset
- [ ] Interface de anotação
- [ ] Pipeline de fine-tuning
- [ ] Avaliação de modelo

## 🧪 Testes

```bash
pytest
```

Um arquivo por camada: `test_domain.py`, `test_parser.py`, `test_builder.py`, `test_api.py`.

## 📝 Exemplos de Uso

### Analisar e Exportar Tudo

```bash
graphalyzer my_project -o analysis -f all
```

Gera:
- `analysis/analysis.json` - Grafo completo
- `analysis/analysis.md` - Documentação
- `analysis/analysis.html` - Dashboard interativo
- `analysis/analysis_nodes.csv` - Nós em CSV
- `analysis/analysis_edges.csv` - Arestas em CSV

### Análise com IA e Markdown

```bash
graphalyzer my_project -o docs -f markdown -ai
```

Gera documentação com resumos gerados por IA.

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙋 Suporte

Para dúvidas ou problemas:

1. Verifique a documentação
2. Abra uma issue no GitHub
3. Consulte os exemplos em `examples/`

## 🎓 Referências

- [AST - Abstract Syntax Trees (Python Docs)](https://docs.python.org/3/library/ast.html)
- [Cytoscape.js - Graph Visualization](https://js.cytoscape.org/)
- [Anthropic Claude API](https://www.anthropic.com/api)
- [OpenAI API](https://openai.com/api/)

