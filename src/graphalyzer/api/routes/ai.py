"""Endpoints de configuração da IA.

A chave entra por aqui e fica **só na memória do processo**. Nenhuma rota
devolve o valor, nem mascarado: o que se pode saber é se existe e de onde veio.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from graphalyzer import config
from graphalyzer.ai import credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ia"])


class ChaveRequest(BaseModel):
    """Chave enviada pelo usuário. Nunca é ecoada de volta."""

    provedor: str = Field("claude", description="claude ou openai")
    chave: str = Field(..., min_length=8, repr=False)


class StatusResponse(BaseModel):
    provedor: str
    configurada: bool
    origem: str  # sessao | ambiente | nenhuma
    sdk_disponivel: bool
    modelo: str


def _status(provedor: str) -> StatusResponse:
    s = credentials.status(provedor)
    return StatusResponse(
        provedor=s.provedor,
        configurada=s.configurada,
        origem=s.origem,
        sdk_disponivel=s.sdk_disponivel,
        modelo=config.DEFAULT_AI_MODEL,
    )


@router.get("/status", response_model=StatusResponse)
async def status_da_ia(provedor: str = config.DEFAULT_AI_PROVIDER) -> StatusResponse:
    """Se há chave configurada e de onde ela vem — nunca o valor."""
    if provedor not in credentials.VARIAVEIS:
        raise HTTPException(status_code=400, detail="Provedor desconhecido")
    return _status(provedor)


@router.put("/key", response_model=StatusResponse)
async def definir_chave(pedido: ChaveRequest) -> StatusResponse:
    """Registra a chave para esta sessão do servidor.

    Some ao reiniciar, de propósito: gravar em disco transformaria um segredo
    de sessão em segredo persistido, com backup e tudo. Para persistir, use a
    variável de ambiente.
    """
    try:
        credentials.definir_chave(pedido.provedor, pedido.chave)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not credentials.sdk_disponivel(pedido.provedor):
        logger.warning(
            "Chave de %s registrada, mas o SDK não está instalado", pedido.provedor
        )

    return _status(pedido.provedor)


@router.delete("/key", response_model=StatusResponse)
async def esquecer_chave(provedor: str = config.DEFAULT_AI_PROVIDER) -> StatusResponse:
    """Remove a chave da sessão. Não afeta a variável de ambiente."""
    if provedor not in credentials.VARIAVEIS:
        raise HTTPException(status_code=400, detail="Provedor desconhecido")

    credentials.limpar_chave(provedor)
    return _status(provedor)
