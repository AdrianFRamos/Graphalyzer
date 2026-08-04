"""Testes da integração com IA.

O foco é o que dá errado em silêncio: chave vazando por algum caminho, e a
análise inventando conteúdo quando a IA não está disponível.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from conftest import build_graph

from graphalyzer.ai import credentials
from graphalyzer.api.app import create_app

CHAVE_FALSA = "sk-ant-chave-de-teste-nao-real-0000"


@pytest.fixture(autouse=True)
def sessao_limpa(monkeypatch):
    """Cada teste começa sem chave, de sessão ou de ambiente."""
    monkeypatch.setattr(credentials, "_EM_MEMORIA", {})
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def client():
    return TestClient(create_app())


def test_status_sem_chave(client):
    dados = client.get("/api/ai/status").json()
    assert dados["configurada"] is False
    assert dados["origem"] == "nenhuma"


def test_definir_chave_muda_o_status(client):
    resposta = client.put(
        "/api/ai/key", json={"provedor": "claude", "chave": CHAVE_FALSA}
    )
    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["configurada"] is True
    assert dados["origem"] == "sessao"


def test_nenhuma_rota_devolve_a_chave(client):
    """A chave não pode aparecer em resposta alguma, nem mascarada."""
    client.put("/api/ai/key", json={"provedor": "claude", "chave": CHAVE_FALSA})

    for rota in ("/api/ai/status", "/api/ai/key"):
        corpo = client.get(rota).text if rota.endswith("status") else ""
        assert CHAVE_FALSA not in corpo

    corpo = client.put(
        "/api/ai/key", json={"provedor": "claude", "chave": CHAVE_FALSA}
    ).text
    assert CHAVE_FALSA not in corpo
    # Nem um pedaço reconhecível
    assert CHAVE_FALSA[-8:] not in corpo


def test_chave_nao_vai_para_o_log(client, caplog):
    """Log de aplicação costuma virar arquivo; segredo não entra nele."""
    with caplog.at_level(logging.DEBUG):
        client.put("/api/ai/key", json={"provedor": "claude", "chave": CHAVE_FALSA})

    registrado = "\n".join(r.getMessage() for r in caplog.records)
    assert CHAVE_FALSA not in registrado
    assert CHAVE_FALSA[-8:] not in registrado


def test_chave_da_sessao_vence_a_do_ambiente(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "do-ambiente")
    assert credentials.obter_chave("claude") == "do-ambiente"
    assert credentials.status("claude").origem == "ambiente"

    credentials.definir_chave("claude", "da-sessao")
    assert credentials.obter_chave("claude") == "da-sessao"
    assert credentials.status("claude").origem == "sessao"


def test_esquecer_chave_nao_apaga_o_ambiente(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "do-ambiente")
    client.put("/api/ai/key", json={"provedor": "claude", "chave": CHAVE_FALSA})

    dados = client.delete("/api/ai/key?provedor=claude").json()
    assert dados["configurada"] is True
    assert dados["origem"] == "ambiente"


def test_provedor_desconhecido_e_rejeitado(client):
    assert client.get("/api/ai/status?provedor=magia").status_code == 400
    with pytest.raises(ValueError):
        credentials.definir_chave("magia", CHAVE_FALSA)


def test_chave_vazia_e_rejeitada(client):
    assert (
        client.put("/api/ai/key", json={"provedor": "claude", "chave": "   "}).status_code
        == 422
    )


def test_sem_chave_a_analise_segue_sem_ia():
    """IA indisponível degrada a documentação, não derruba a análise."""
    from graphalyzer.services.analysis import enrich_with_ai

    graph = build_graph({"a.py": "def f(x: int) -> int:\n    return x\n"})
    assert enrich_with_ai(graph, "claude", "claude-sonnet-5") == 0

    # E nada de resumo inventado
    assert all(n.ai_summary is None for n in graph.nodes.values())


def test_resposta_da_ia_e_aplicada_aos_arquivos(monkeypatch):
    """Com IA, o resumo vai para o nó de arquivo — que é o que a doc usa."""
    from graphalyzer.ai import documentation
    from graphalyzer.domain.models import NodeType

    graph = build_graph({"servico.py": "def cobrar(valor: float) -> None:\n    pass\n"})

    class IAFalsa(documentation.DocumentationAI):
        def __init__(self):
            self.provider, self.model, self.client = "claude", "x", object()

        def _perguntar(self, prompt, max_tokens=700):
            return json.dumps(
                {
                    "responsabilidade": "Processa cobranças.",
                    "categoria": "dominio",
                    "observacoes": "Sem tratamento de erro.",
                }
            )

    monkeypatch.setattr(documentation, "DocumentationAI", lambda **kw: IAFalsa())

    from graphalyzer.services.analysis import enrich_with_ai

    assert enrich_with_ai(graph, "claude", "claude-sonnet-5") == 1

    arquivo = next(
        n for n in graph.nodes.values() if n.type == NodeType.FILE
    )
    assert arquivo.ai_summary == "Processa cobranças."
    assert arquivo.ai_category == "dominio"
    assert arquivo.metadata["ai_observacoes"] == "Sem tratamento de erro."


def test_resumo_da_ia_vira_responsabilidade_na_documentacao():
    """O elo que estava quebrado: o resumo precisa chegar ao documento."""
    from graphalyzer.domain.models import NodeType
    from graphalyzer.storage.docs import ConstrutorDeDocumentacao

    graph = build_graph({"sem_doc.py": "def f():\n    pass\n"})
    arquivo = next(n for n in graph.nodes.values() if n.type == NodeType.FILE)
    arquivo.ai_summary = "Orquestra o envio de notificações."

    doc = ConstrutorDeDocumentacao(graph).documentos()[0]
    assert doc.responsabilidade == "Orquestra o envio de notificações."
