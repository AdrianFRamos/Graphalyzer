"""Graphalyzer — grafo de dependências e fluxo de dados de projetos Python.

Camadas, de dentro para fora (cada uma só depende das de dentro):

    domain    modelos puros (Node, Edge, ProjectGraph) — sem I/O
    analysis  AST → grafo (parser, extractor, fluxo de dados, qualidade)
    ai        enriquecimento semântico via LLM
    storage   persistência e exportação (JSON, Markdown, HTML, CSV, cache)
    services  orquestração — o único ponto que combina as camadas acima
    api/cli   interfaces; não contêm regra de análise, só chamam services
"""

__version__ = "1.0.0"
