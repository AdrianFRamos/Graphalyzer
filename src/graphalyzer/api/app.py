"""Aplicação FastAPI: monta rotas, CORS e o dashboard estático."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from graphalyzer import __version__, config
from graphalyzer.api.routes import analysis, cache


def create_app() -> FastAPI:
    """Cria a aplicação. Fábrica em vez de instância global para os testes
    poderem montar uma app limpa sem tocar em estado de módulo."""
    app = FastAPI(
        title="Graphalyzer API",
        description="Análise de projetos Python com visualização em grafo",
        version=__version__,
    )

    # A API lê arquivos arbitrários do disco e devolve o código-fonte deles.
    # Com allow_origins=["*"] qualquer site aberto no navegador conseguiria ler
    # o disco do usuário através dela; a lista fica restrita à origem local.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(analysis.router)
    app.include_router(cache.router)

    @app.get("/health", tags=["meta"])
    async def health():
        """Health check."""
        return {"status": "ok", "version": __version__}

    # O dashboard é montado na raiz e por último: as rotas da API acima já foram
    # registradas e continuam vencendo. Precisa ser na raiz porque o service
    # worker do PWA só controla o escopo a partir de onde é servido — em
    # /static ele não conseguiria interceptar a navegação da aplicação.
    if (config.WEB_DIR / "index.html").is_file():
        app.mount(
            "/",
            StaticFiles(directory=str(config.WEB_DIR), html=True),
            name="dashboard",
        )
    else:

        @app.get("/", include_in_schema=False)
        async def dashboard_ausente():
            """O frontend ainda não foi compilado."""
            return {
                "message": "Dashboard não compilado.",
                "como_resolver": "cd frontend && npm install && npm run build",
                "docs": "/docs",
            }

    return app


app = create_app()
