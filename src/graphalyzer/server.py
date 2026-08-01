"""Entry point do servidor da API."""

import argparse
import sys

from graphalyzer import __version__, config, console


def main(argv=None) -> int:
    """Sobe a API e o dashboard."""
    parser = argparse.ArgumentParser(
        prog="graphalyzer-api", description="Servidor da API do Graphalyzer"
    )
    parser.add_argument("--host", default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--reload", action="store_true", help="Recarrega ao salvar")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    console.setup(verbose=args.verbose)

    import uvicorn

    # 0.0.0.0 é o que se escuta, não o que se acessa: mostrar esse endereço
    # manda o usuário a uma URL que não abre.
    acessivel = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    url = f"http://{acessivel}:{args.port}"

    print(f"\nGraphalyzer {__version__}")
    print(f"📍 Dashboard: {url}")
    print(f"📚 Docs:      {url}/docs")
    if args.host == "0.0.0.0":
        print(
            "\n⚠️  Escutando em todas as interfaces. A API não tem autenticação"
            "\n   e lê arquivos do disco — só faça isso dentro de um container"
            "\n   publicando a porta como -p 127.0.0.1:PORTA:PORTA."
        )
    print()

    uvicorn.run(
        "graphalyzer.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=None,  # mantém o logging já configurado por console.setup
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
