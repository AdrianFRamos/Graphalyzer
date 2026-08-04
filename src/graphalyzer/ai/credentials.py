"""Guarda da chave de API.

A chave vive só na memória do processo. Não vai para disco, log, cache nem
resposta de API — nem mascarada. Some quando o servidor reinicia, e isso é
deliberado: é a diferença entre um segredo em memória e um segredo vazado.

Quem preferir persistência usa variável de ambiente, que é responsabilidade do
ambiente, não da aplicação.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# provedor -> variável de ambiente correspondente
VARIAVEIS = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

_EM_MEMORIA: dict = {}


@dataclass(frozen=True)
class StatusDaIA:
    """O que é seguro contar sobre a configuração — nunca a chave."""

    provedor: str
    configurada: bool
    origem: str  # "sessao", "ambiente" ou "nenhuma"
    sdk_disponivel: bool


def definir_chave(provedor: str, chave: str) -> None:
    """Guarda a chave para esta sessão do processo."""
    if provedor not in VARIAVEIS:
        raise ValueError(f"Provedor desconhecido: {provedor}")

    valor = (chave or "").strip()
    if not valor:
        raise ValueError("Chave vazia")

    _EM_MEMORIA[provedor] = valor
    # Sem o valor no log: um log de aplicação costuma acabar em arquivo
    logger.info("Chave de %s registrada para esta sessão", provedor)


def limpar_chave(provedor: str) -> bool:
    """Esquece a chave da sessão. Não afeta a variável de ambiente."""
    return _EM_MEMORIA.pop(provedor, None) is not None


def obter_chave(provedor: str) -> Optional[str]:
    """Chave em uso: a da sessão tem prioridade sobre a do ambiente."""
    if provedor in _EM_MEMORIA:
        return _EM_MEMORIA[provedor]
    return os.getenv(VARIAVEIS.get(provedor, ""), "") or None


def sdk_disponivel(provedor: str) -> bool:
    """O pacote do provedor está instalado?"""
    modulo = "anthropic" if provedor == "claude" else "openai"
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False


def status(provedor: str) -> StatusDaIA:
    """Situação da configuração, sem expor segredo."""
    if provedor in _EM_MEMORIA:
        origem = "sessao"
    elif os.getenv(VARIAVEIS.get(provedor, ""), ""):
        origem = "ambiente"
    else:
        origem = "nenhuma"

    return StatusDaIA(
        provedor=provedor,
        configurada=origem != "nenhuma",
        origem=origem,
        sdk_disponivel=sdk_disponivel(provedor),
    )
