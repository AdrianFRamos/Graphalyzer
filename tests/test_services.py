"""Testes da camada de orquestração."""

import pytest

from graphalyzer import config
from graphalyzer.services.analysis import resolve_project_path


@pytest.fixture
def projetos_montados(tmp_path, monkeypatch):
    """Simula o /projects do container com dois projetos dentro."""
    raiz = tmp_path / "projects"
    (raiz / "GBOrganiza").mkdir(parents=True)
    (raiz / "Graphalyzer").mkdir()

    monkeypatch.setattr(config, "PROJECTS_ROOT", raiz)
    # Raiz do host inexistente nesta máquina: é a situação dentro do container,
    # onde o caminho do Windows não resolve. Usar um caminho real aqui não
    # testaria nada — ele existiria e passaria direto.
    monkeypatch.setattr(config, "HOST_ROOT", "Z:/maquina-do-usuario")
    return raiz


def test_traduz_caminho_do_windows(projetos_montados):
    """O caminho do host vira o caminho de dentro do container.

    É o erro que o usuário encontra primeiro: digitar o caminho do Windows num
    app que roda em container e receber "não encontrado".
    """
    resolvido = resolve_project_path(r"Z:\maquina-do-usuario\GBOrganiza")
    assert resolvido == projetos_montados / "GBOrganiza"


def test_traduz_com_barra_normal(projetos_montados):
    resolvido = resolve_project_path("Z:/maquina-do-usuario/Graphalyzer")
    assert resolvido == projetos_montados / "Graphalyzer"


def test_traduz_ignorando_maiusculas(projetos_montados):
    """Caminho do Windows não distingue maiúsculas."""
    resolvido = resolve_project_path(r"z:\MAQUINA-DO-USUARIO\GBOrganiza")
    assert resolvido == projetos_montados / "GBOrganiza"


def test_localiza_pelo_nome_quando_a_raiz_do_host_nao_bate(projetos_montados):
    """Caminho de outra origem, mas com nome que casa com um projeto montado."""
    resolvido = resolve_project_path(r"Y:\outra\origem\GBOrganiza")
    assert resolvido == projetos_montados / "GBOrganiza"


def test_caminho_existente_passa_intacto(projetos_montados, tmp_path):
    """Caminho que já existe não é reescrito."""
    real = tmp_path / "local"
    real.mkdir()
    assert resolve_project_path(str(real)) == real


def test_projeto_inexistente_continua_falhando(projetos_montados):
    """Sem correspondência, o caminho volta como veio para o erro ser claro."""
    resolvido = resolve_project_path(r"Z:\maquina-do-usuario\NaoExiste")
    assert not resolvido.is_dir()
