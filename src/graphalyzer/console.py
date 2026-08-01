"""Configuração de saída para os entry points (CLI e API).

As camadas internas usam `logging` e nunca escrevem em stdout — só as
interfaces decidem como e se algo aparece para o usuário.
"""

import logging
import sys


def setup(verbose: bool = False) -> None:
    """Prepara console e logging. Chamar uma vez, no início de um entry point."""
    # O console do Windows abre em cp1252 e estoura em qualquer "✓" impresso.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and (getattr(stream, "encoding", "") or "").lower() != "utf-8":
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError):
                pass  # stream redirecionado: segue com o encoding atual

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
