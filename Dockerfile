# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Etapa 1: compila o dashboard. Node existe só aqui — não vai para a imagem
# final, que fica com Python e os arquivos estáticos já prontos.
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build/frontend

# package*.json antes do resto do código: enquanto as dependências não mudarem,
# esta camada (a lenta) vem do cache
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# O vite.config.js aponta a saída para ../src/graphalyzer/web
RUN npm run build


# ---------------------------------------------------------------------------
# Etapa 2: imagem final
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # 0.0.0.0 é seguro AQUI e só aqui: o processo escuta apenas na rede do
    # container. Quem controla a exposição real é a publicação da porta —
    # use sempre `-p 127.0.0.1:5000:5000`, nunca `-p 5000:5000`, porque a API
    # lê arquivos arbitrários e não tem autenticação.
    GRAPHALYZER_HOST=0.0.0.0 \
    GRAPHALYZER_PORT=5000 \
    # Fora de /app, que pertence ao root: o processo roda sem privilégio
    GRAPHALYZER_CACHE_DIR=/data/cache

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Substitui o build versionado pelo recém-compilado
COPY --from=frontend /build/src/graphalyzer/web ./src/graphalyzer/web

RUN pip install --no-cache-dir ".[api]"

# Usuário sem privilégio. /data é a única área gravável; /projects recebe o
# código a analisar, montado somente leitura.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /projects \
    && chown -R app:app /data

USER app
WORKDIR /data

EXPOSE 5000

# Sem curl na imagem slim; urllib já vem com o Python
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=4).status == 200 else 1)"

CMD ["graphalyzer-api"]
