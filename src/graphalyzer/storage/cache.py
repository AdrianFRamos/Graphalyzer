"""Cache de análises em SQLite.

Evita reanalisar um projeto que não mudou. A verificação precisa ser muito
mais barata que a análise, senão o cache não paga o próprio custo.
"""

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from graphalyzer import config

logger = logging.getLogger(__name__)


class AnalysisCache:
    """Guarda grafos já construídos, indexados por projeto."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "analysis.db"
        self._init_db()

    # Subir este número descarta caches gravados por versões antigas
    SCHEMA_VERSION = 3

    _ESQUEMA = """
        CREATE TABLE projects (
            project_path TEXT PRIMARY KEY,
            project_hash TEXT NOT NULL,
            graph_json TEXT NOT NULL,
            has_ai INTEGER NOT NULL DEFAULT 0,
            timestamp DATETIME NOT NULL
        );

        -- Respostas da IA endereçadas pelo conteúdo do pedido: arquivo que não
        -- mudou não é reanalisado, mesmo que o grafo inteiro tenha sido.
        CREATE TABLE ai_results (
            chave TEXT PRIMARY KEY,
            resultado TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        );
    """

    def _init_db(self) -> None:
        """Cria o esquema, descartando um cache de formato antigo.

        `CREATE TABLE IF NOT EXISTS` não migra nada: com um banco de versão
        anterior no disco, toda consulta falharia por coluna inexistente.
        Cache é descartável — recriar custa uma análise, migrar custa código.
        """
        with sqlite3.connect(self.db_path) as conn:
            versao = conn.execute("PRAGMA user_version").fetchone()[0]

            if versao != self.SCHEMA_VERSION:
                if versao:
                    logger.info(
                        "Cache em formato antigo (v%s); recriando na v%s",
                        versao,
                        self.SCHEMA_VERSION,
                    )
                for tabela in ("projects", "files", "analyses", "ai_results"):
                    conn.execute(f"DROP TABLE IF EXISTS {tabela}")
                conn.executescript(self._ESQUEMA)
                conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
                conn.commit()
                return

            # Versão bate, mas o banco pode estar vazio (primeira execução)
            existe = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'"
            ).fetchone()
            if not existe:
                conn.executescript(self._ESQUEMA)
                conn.commit()

    def fingerprint(self, project_path: str) -> str:
        """Impressão digital do projeto: caminho, tamanho e mtime dos arquivos.

        Ler o conteúdo de cada arquivo para gerar o hash custaria tanto quanto
        analisar — o cache só compensa se a verificação for barata. Tamanho e
        data de modificação detectam qualquer edição real; o risco teórico é
        uma alteração que preserve os dois, que na prática não ocorre.

        ponytail: se algum dia isso incomodar, hashear o conteúdo só dos
        arquivos cujo mtime mudou seria o próximo passo.
        """
        from graphalyzer.analysis.languages import supported_extensions

        extensoes = tuple(supported_extensions())
        raiz = Path(project_path)
        partes = []

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not config.deve_ignorar(d)]

            for nome in sorted(files):
                if not nome.endswith(extensoes):
                    continue
                caminho = Path(root) / nome
                try:
                    info = caminho.stat()
                except OSError:
                    continue
                relativo = caminho.relative_to(raiz).as_posix()
                partes.append(f"{relativo}:{info.st_size}:{int(info.st_mtime)}")

        return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()

    def get(
        self, project_path: str, require_ai: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Grafo em cache, se o projeto não mudou desde que foi guardado.

        `require_ai` evita devolver um grafo sem enriquecimento semântico para
        quem pediu análise com IA.
        """
        with sqlite3.connect(self.db_path) as conn:
            linha = conn.execute(
                "SELECT graph_json, project_hash, has_ai FROM projects WHERE project_path = ?",
                (str(project_path),),
            ).fetchone()

        if not linha:
            return None

        graph_json, hash_guardado, has_ai = linha

        if require_ai and not has_ai:
            return None

        if hash_guardado != self.fingerprint(project_path):
            logger.info("Cache invalidado: %s mudou", project_path)
            return None

        try:
            return json.loads(graph_json)
        except json.JSONDecodeError:
            logger.warning("Cache corrompido para %s; será reanalisado", project_path)
            return None

    def store(self, project_path: str, graph_json: str, has_ai: bool = False) -> None:
        """Guarda o grafo com a impressão digital atual do projeto."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (project_path, project_hash, graph_json, has_ai, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(project_path),
                    self.fingerprint(project_path),
                    graph_json,
                    int(has_ai),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def ai_get(self, chave: str) -> Optional[Dict[str, Any]]:
        """Resposta da IA já paga para este mesmo conteúdo."""
        with sqlite3.connect(self.db_path) as conn:
            linha = conn.execute(
                "SELECT resultado FROM ai_results WHERE chave = ?", (chave,)
            ).fetchone()

        if not linha:
            return None
        try:
            return json.loads(linha[0])
        except json.JSONDecodeError:
            return None

    def ai_store(self, chave: str, resultado: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ai_results (chave, resultado, timestamp) "
                "VALUES (?, ?, ?)",
                (chave, json.dumps(resultado, ensure_ascii=False), datetime.now().isoformat()),
            )
            conn.commit()

    def clear(self, project_path: Optional[str] = None) -> int:
        """Limpa o cache de um projeto ou inteiro. Devolve quantos saíram."""
        with sqlite3.connect(self.db_path) as conn:
            if project_path:
                cursor = conn.execute(
                    "DELETE FROM projects WHERE project_path = ?", (str(project_path),)
                )
            else:
                cursor = conn.execute("DELETE FROM projects")
            conn.commit()
            return cursor.rowcount

    def statistics(self) -> Dict[str, int]:
        """Quantos projetos em cache e quanto espaço ocupam."""
        with sqlite3.connect(self.db_path) as conn:
            projetos = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            tamanho = conn.execute(
                "SELECT COALESCE(SUM(LENGTH(graph_json)), 0) FROM projects"
            ).fetchone()[0]

        return {"cached_projects": projetos, "cache_bytes": tamanho}
