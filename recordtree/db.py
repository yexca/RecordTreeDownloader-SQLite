from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
import sqlite3


def connect(database_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    schema = files("recordtree").joinpath("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    _migrate_schema(conn)
    conn.execute(
        """
        INSERT INTO schema_meta (key, value, updated_at)
        VALUES ('schema_version', '2', datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """
    )
    conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    download_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(downloads)").fetchall()
    }
    if "request_json" not in download_columns:
        conn.execute("ALTER TABLE downloads ADD COLUMN request_json TEXT")


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
