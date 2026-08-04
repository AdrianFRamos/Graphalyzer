"""Testes da API — o caminho que o dashboard percorre de ponta a ponta."""

import pytest
from fastapi.testclient import TestClient

from pathlib import Path

from conftest import SAMPLE_PROJECT

from graphalyzer.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def analysis_id(client) -> str:
    response = client.post("/api/analyze", json={"project_path": str(SAMPLE_PROJECT)})
    assert response.status_code == 200, response.text
    return response.json()["analysis_id"]


def test_raiz_serve_o_dashboard(client):
    """`/` entrega o dashboard, não JSON — havia duas rotas disputando `/`."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_projeto_inexistente_responde_404(client):
    """404 não pode virar 500 ao ser engolido pelo tratamento genérico."""
    response = client.post("/api/analyze", json={"project_path": "nao/existe"})
    assert response.status_code == 404


def test_grafo_por_visualizacao(client, analysis_id):
    """As duas visualizações entregam arestas com tipo, e nenhuma órfã."""
    for view_type in ("file", "function"):
        data = client.get(
            f"/api/analysis/{analysis_id}/graph?view_type={view_type}"
        ).json()

        ids = {n["data"]["id"] for n in data["nodes"]}
        assert data["nodes"], f"visualização {view_type} sem nós"

        for edge in data["edges"]:
            assert edge["data"]["source"] in ids
            assert edge["data"]["target"] in ids
            assert edge["data"]["type"]

    função = client.get(
        f"/api/analysis/{analysis_id}/graph?view_type=function"
    ).json()
    tipos = {e["data"]["type"] for e in função["edges"]}
    assert "data_flow" in tipos, tipos


def test_detalhe_de_no_e_metricas(client, analysis_id):
    """Detalhe de nó traz assinatura; métricas respondem."""
    grafo = client.get(f"/api/analysis/{analysis_id}/graph?view_type=function").json()
    node_id = grafo["nodes"][0]["data"]["id"]

    detalhe = client.get(f"/api/analysis/{analysis_id}/node/{node_id}").json()
    assert detalhe["id"] == node_id
    assert "parameters" in detalhe and "complexity" in detalhe

    assert client.get(f"/api/analysis/{analysis_id}/metrics").status_code == 200


@pytest.mark.parametrize("export_format", ["json", "md", "html", "csv", "docs", "pdf"])
def test_export(client, analysis_id, export_format):
    """Todo formato exporta e devolve conteúdo."""
    response = client.get(f"/api/analysis/{analysis_id}/export/{export_format}")
    assert response.status_code == 200, response.text
    assert response.content


def test_export_formato_invalido(client, analysis_id):
    # `pdf` deixou de servir de exemplo aqui: virou formato suportado
    response = client.get(f"/api/analysis/{analysis_id}/export/docx")
    assert response.status_code == 400


def test_delete_remove_analise(client, analysis_id):
    assert client.delete(f"/api/analysis/{analysis_id}").status_code == 200
    assert client.get(f"/api/analysis/{analysis_id}").status_code == 404


def test_resposta_traz_o_caminho_resolvido(client):
    """A resposta devolve o caminho que foi de fato analisado.

    O frontend guarda o id da análise, mas a store do servidor é em memória e
    morre a cada reinício. Sem o caminho na resposta, não há como refazer a
    análise depois de um restart — o usuário fica preso num 404.
    """
    resposta = client.post(
        "/api/analyze", json={"project_path": str(SAMPLE_PROJECT)}
    ).json()

    assert resposta["project_path"], "resposta sem project_path"
    assert Path(resposta["project_path"]).is_dir()


def test_analise_desconhecida_responde_404(client):
    """Id que não existe mais é 404 — o frontend usa isso para revalidar."""
    assert client.get("/api/analysis/inexistente/graph").status_code == 404
