"""
Sistema de plugins para extensibilidade.
Permite adicionar analisadores e exportadores customizados.
"""

import logging

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import importlib.util
import sys

logger = logging.getLogger(__name__)


class AnalyzerPlugin(ABC):
    """Interface base para plugins de análise."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Versão do plugin."""
        pass

    @abstractmethod
    def analyze(self, code: str, filename: str) -> Dict[str, Any]:
        """Analisa código."""
        pass


class ExporterPlugin(ABC):
    """Interface base para plugins de exportação."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do plugin."""
        pass

    @property
    @abstractmethod
    def format(self) -> str:
        """Formato de exportação."""
        pass

    @abstractmethod
    def export(self, graph, output_path: str) -> None:
        """Exporta grafo."""
        pass


class PluginManager:
    """Gerencia plugins."""

    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(exist_ok=True)
        self.analyzers: Dict[str, AnalyzerPlugin] = {}
        self.exporters: Dict[str, ExporterPlugin] = {}

    def load_plugin(self, plugin_path: str) -> Optional[Any]:
        """Carrega um plugin."""
        plugin_path = Path(plugin_path)

        if not plugin_path.exists():
            logger.error(f"❌ Plugin não encontrado: {plugin_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location("plugin", plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["plugin"] = module
            spec.loader.exec_module(module)

            # Procurar por classes de plugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type):
                    if issubclass(attr, AnalyzerPlugin) and attr != AnalyzerPlugin:
                        plugin_instance = attr()
                        self.analyzers[plugin_instance.name] = plugin_instance
                        logger.info(f"✓ Analyzer plugin carregado: {plugin_instance.name}")

                    elif issubclass(attr, ExporterPlugin) and attr != ExporterPlugin:
                        plugin_instance = attr()
                        self.exporters[plugin_instance.format] = plugin_instance
                        logger.info(f"✓ Exporter plugin carregado: {plugin_instance.format}")

            return module

        except Exception as e:
            logger.error(f"❌ Erro ao carregar plugin: {e}")
            return None

    def load_plugins_from_directory(self) -> int:
        """Carrega todos os plugins do diretório."""
        count = 0

        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.name != "__init__.py":
                if self.load_plugin(str(plugin_file)):
                    count += 1

        return count

    def get_analyzer(self, name: str) -> Optional[AnalyzerPlugin]:
        """Obtém um analisador."""
        return self.analyzers.get(name)

    def get_exporter(self, format: str) -> Optional[ExporterPlugin]:
        """Obtém um exportador."""
        return self.exporters.get(format)

    def list_analyzers(self) -> List[str]:
        """Lista analisadores disponíveis."""
        return list(self.analyzers.keys())

    def list_exporters(self) -> List[str]:
        """Lista exportadores disponíveis."""
        return list(self.exporters.keys())

    def run_analyzer(self, analyzer_name: str, code: str, filename: str) -> Optional[Dict[str, Any]]:
        """Executa um analisador."""
        analyzer = self.get_analyzer(analyzer_name)
        if analyzer:
            return analyzer.analyze(code, filename)
        return None

    def run_exporter(self, format: str, graph, output_path: str) -> bool:
        """Executa um exportador."""
        exporter = self.get_exporter(format)
        if exporter:
            exporter.export(graph, output_path)
            return True
        return False


class PluginRegistry:
    """Registro de plugins disponíveis."""

    def __init__(self):
        self.plugins: Dict[str, Dict[str, Any]] = {}

    def register(self, plugin_type: str, name: str, plugin_class: type, metadata: Dict[str, Any] = None) -> None:
        """Registra um plugin."""
        key = f"{plugin_type}:{name}"
        self.plugins[key] = {
            "type": plugin_type,
            "name": name,
            "class": plugin_class,
            "metadata": metadata or {},
        }

    def get(self, plugin_type: str, name: str) -> Optional[type]:
        """Obtém classe de plugin."""
        key = f"{plugin_type}:{name}"
        return self.plugins.get(key, {}).get("class")

    def list_by_type(self, plugin_type: str) -> List[str]:
        """Lista plugins por tipo."""
        return [
            name.split(":", 1)[1]
            for name in self.plugins.keys()
            if name.startswith(f"{plugin_type}:")
        ]

    def get_metadata(self, plugin_type: str, name: str) -> Dict[str, Any]:
        """Obtém metadados do plugin."""
        key = f"{plugin_type}:{name}"
        return self.plugins.get(key, {}).get("metadata", {})


# Exemplo de plugin customizado
class ExampleAnalyzerPlugin(AnalyzerPlugin):
    """Plugin de análise de exemplo."""

    @property
    def name(self) -> str:
        return "example_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def analyze(self, code: str, filename: str) -> Dict[str, Any]:
        """Analisa código."""
        return {
            "plugin": self.name,
            "filename": filename,
            "lines": len(code.split("\n")),
            "has_docstring": '"""' in code or "'''" in code,
        }


class ExampleExporterPlugin(ExporterPlugin):
    """Plugin de exportação de exemplo."""

    @property
    def name(self) -> str:
        return "example_exporter"

    @property
    def format(self) -> str:
        return "example"

    def export(self, graph, output_path: str) -> None:
        """Exporta grafo."""
        with open(output_path, "w") as f:
            f.write(f"# Example Export\n")
            f.write(f"Project: {graph.project_name}\n")
            f.write(f"Nodes: {len(graph.nodes)}\n")
            f.write(f"Edges: {len(graph.edges)}\n")
