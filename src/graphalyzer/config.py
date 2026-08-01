"""Configuração da aplicação.

Valores que antes estavam repetidos entre CLI, API e frontend. Tudo aqui é
sobrescrevível por variável de ambiente `GRAPHALYZER_*` — sem arquivo de
configuração enquanto uma variável de ambiente resolver.
"""

import os
from pathlib import Path

# 127.0.0.1, não 0.0.0.0: a API lê arquivos arbitrários do disco e não tem
# autenticação — expor isso na rede entrega o sistema de arquivos.
HOST = os.getenv("GRAPHALYZER_HOST", "127.0.0.1")
PORT = int(os.getenv("GRAPHALYZER_PORT", "5000"))

# O frontend só é servido pela própria API, então a origem permitida é ela mesma.
CORS_ORIGINS = [f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"]

DEFAULT_AI_PROVIDER = os.getenv("GRAPHALYZER_AI_PROVIDER", "claude")
DEFAULT_AI_MODEL = os.getenv("GRAPHALYZER_AI_MODEL", "claude-sonnet-5")

DEFAULT_OUTPUT_DIR = "analysis_output"
CACHE_DIR = os.getenv("GRAPHALYZER_CACHE_DIR", ".graphalyzer_cache")

# Raiz onde os projetos ficam montados (usada no Docker). Existindo, um caminho
# inválido responde listando o que está de fato disponível — sem isso o usuário
# digita o caminho do host e só recebe "não encontrado".
PROJECTS_ROOT = Path(os.getenv("GRAPHALYZER_PROJECTS_ROOT", "/projects"))

# Pasta do host que corresponde a PROJECTS_ROOT dentro do container. Declarada,
# permite aceitar o caminho do jeito que o usuário conhece (`C:\Users\...`) e
# traduzir para o caminho de dentro — sem isso ele precisa converter à mão.
HOST_ROOT = os.getenv("GRAPHALYZER_HOST_ROOT", "")

# Pastas de dependência e de build. Varrer estas é o que faz uma análise
# demorar minutos e encher o grafo de código que não é do projeto.
EXCLUDE_DIRS = [
    # Controle de versão e caches
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # Python
    ".venv",
    "venv",
    "site-packages",
    "dist",
    "egg-info",
    # JavaScript e TypeScript
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "coverage",
    # Dart e Flutter
    ".dart_tool",
    ".flutter-plugins",
    "Pods",
    "ephemeral",
    # JVM, .NET, Go, Rust
    ".gradle",
    "target",
    "obj",
    "bin",
    "vendor",
    # Genéricos
    "build",
    "out",
]

# Arquivos estáticos do dashboard, empacotados junto com o código
WEB_DIR = Path(__file__).parent / "web"
