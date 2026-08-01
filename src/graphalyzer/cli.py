"""Interface de linha de comando.

Só interface: valida argumentos, chama `services.analysis` e imprime o
resultado. Nenhuma regra de análise mora aqui.
"""

import argparse
import sys
from pathlib import Path

from graphalyzer import __version__, config, console
from graphalyzer.services import analysis as service

ALL_FORMATS = list(service.EXPORTERS)


def build_parser() -> argparse.ArgumentParser:
    """Monta o parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="graphalyzer",
        description="Analisa um projeto Python e gera o grafo de dependências e fluxo de dados.",
    )
    parser.add_argument("project_path", help="Caminho do projeto Python a analisar")
    parser.add_argument(
        "-o",
        "--output",
        default=config.DEFAULT_OUTPUT_DIR,
        help=f"Diretório de saída (padrão: {config.DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=ALL_FORMATS + ["all"],
        default="all",
        help="Formato de exportação (padrão: all)",
    )
    parser.add_argument(
        "-ai",
        "--ai-analysis",
        action="store_true",
        help="Executar análise semântica com IA (requer API key)",
    )
    parser.add_argument(
        "--ai-provider",
        choices=["claude", "openai"],
        default=config.DEFAULT_AI_PROVIDER,
        help=f"Provedor de IA (padrão: {config.DEFAULT_AI_PROVIDER})",
    )
    parser.add_argument(
        "--ai-model",
        default=config.DEFAULT_AI_MODEL,
        help=f"Modelo de IA (padrão: {config.DEFAULT_AI_MODEL})",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignora o cache e reanalisa do zero",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detalhado")
    parser.add_argument("--version", action="version", version=f"graphalyzer {__version__}")
    return parser


def main(argv=None) -> int:
    """Ponto de entrada da CLI. Devolve o código de saída."""
    args = build_parser().parse_args(argv)
    console.setup(verbose=args.verbose)

    formats = ALL_FORMATS if args.format == "all" else [args.format]

    print(f"\n{'=' * 60}")
    print(f"Graphalyzer {__version__}")
    print(f"{'=' * 60}\n")
    print(f"📁 Projeto: {Path(args.project_path).absolute()}")
    print(f"📤 Saída:   {Path(args.output).absolute()}")
    print(f"📊 Formato: {', '.join(formats)}\n")

    try:
        analysis = service.analyze_project(
            args.project_path,
            use_ai=args.ai_analysis,
            ai_provider=args.ai_provider,
            ai_model=args.ai_model,
            use_cache=not args.no_cache,
        )
    except NotADirectoryError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    written = service.export_graph(analysis.graph, args.output, formats)
    graph = analysis.graph

    edges_by_type = {}
    for edge in graph.edges:
        edges_by_type[edge.type.value] = edges_by_type.get(edge.type.value, 0) + 1

    print(f"\n{'=' * 60}")
    print("✓ ANÁLISE CONCLUÍDA")
    print(f"{'=' * 60}\n")
    print("📊 Estatísticas:")
    print(f"   Arquivos: {graph.file_count}")
    print(f"   Funções:  {graph.function_count}")
    print(f"   Classes:  {graph.class_count}")
    print(f"   Arestas:  {len(graph.edges)}")
    for edge_type, count in sorted(edges_by_type.items()):
        print(f"      {edge_type}: {count}")

    print("\n📂 Arquivos gerados:")
    for path in written:
        print(f"   {path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
