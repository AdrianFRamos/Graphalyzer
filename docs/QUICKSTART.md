# 🚀 Quick Start - Project Analyzer

Comece em 5 minutos!

## 1️⃣ Instalação (2 min)

```bash
# Clonar e entrar no diretório
git clone <repo-url>
cd project_analyzer

# Instalar dependências
pip install -r requirements.txt
```

## 2️⃣ Primeiro Uso (1 min)

### Opção A: CLI

```bash
# Analisar projeto de exemplo
python main.py examples/sample_project -o output -f all

# Abrir resultado
open output/analysis.html  # macOS
# ou
xdg-open output/analysis.html  # Linux
# ou
start output\analysis.html  # Windows
```

### Opção B: API Web

```bash
# Iniciar servidor
python run_api.py

# Acessar em browser
# http://localhost:5000
```

## 3️⃣ Analisar Seu Projeto (2 min)

```bash
# Substituir /seu/projeto pelo caminho real
python main.py /seu/projeto -o output -f all
```

## 📊 Resultados

Você terá:
- `output/analysis.json` - Dados completos
- `output/analysis.md` - Documentação
- `output/analysis.html` - Dashboard interativo
- `output/analysis_nodes.csv` - Tabela de nós
- `output/analysis_edges.csv` - Tabela de dependências

## 🎯 Próximos Passos

1. Explorar o dashboard HTML
2. Ler [USAGE_GUIDE.md](USAGE_GUIDE.md) para mais exemplos
3. Consultar [API_GUIDE.md](API_GUIDE.md) para integração

## 💡 Dicas

- Use `-ai` para análise com IA (requer API key)
- Use `-f json` para apenas JSON (mais rápido)
- Use `--help` para ver todas as opções

```bash
python main.py --help
```

## 🆘 Problemas?

1. Verifique se Python 3.8+ está instalado: `python --version`
2. Reinstale dependências: `pip install -r requirements.txt --force-reinstall`
3. Consulte [USAGE_GUIDE.md](USAGE_GUIDE.md) na seção Troubleshooting

---

**Pronto para começar?** 🎉
