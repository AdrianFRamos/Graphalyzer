"""Testes do dashboard PWA servido pelo backend.

O service worker só controla a aplicação se for servido a partir da raiz.
Servir o build em /static quebraria o PWA silenciosamente — a página abriria
normal e só falharia offline, que é justamente quando ninguém está olhando.
"""

import json

import pytest
from fastapi.testclient import TestClient

from graphalyzer import config
from graphalyzer.api.app import create_app

pytestmark = pytest.mark.skipif(
    not (config.WEB_DIR / "index.html").is_file(),
    reason="frontend não compilado (cd frontend && npm install && npm run build)",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_dashboard_na_raiz(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.parametrize(
    "caminho",
    ["/sw.js", "/manifest.webmanifest", "/registerSW.js", "/icon-192.png"],
)
def test_arquivos_do_pwa_na_raiz(client, caminho):
    """Service worker e manifest precisam estar na raiz, não sob um prefixo."""
    assert client.get(caminho).status_code == 200


def test_manifest_valido(client):
    """Sem estes campos o navegador recusa a instalação do app."""
    manifest = json.loads(client.get("/manifest.webmanifest").content)

    assert manifest["name"]
    assert manifest["start_url"] == "/"
    assert manifest["display"] in ("standalone", "fullscreen", "minimal-ui")

    tamanhos = {icone["sizes"] for icone in manifest["icons"]}
    assert {"192x192", "512x512"} <= tamanhos, tamanhos
    assert any("maskable" in i.get("purpose", "") for i in manifest["icons"])


def test_api_vence_o_mount_da_raiz(client):
    """O dashboard é montado em `/` — as rotas da API não podem ser engolidas."""
    assert client.get("/health").json()["status"] == "ok"
    assert client.post("/api/analyze", json={"project_path": "nao/existe"}).status_code == 404


def test_assets_versionados_sao_servidos(client):
    """O HTML referencia /assets/... — se não forem servidos, a página fica em branco."""
    html = client.get("/").text

    referencias = [
        parte.split('"')[0]
        for parte in html.split('src="')[1:] + html.split('href="')[1:]
        if parte.startswith("/assets/")
    ]
    assert referencias, "index.html não referencia nenhum asset"

    for caminho in referencias:
        assert client.get(caminho).status_code == 200, caminho
