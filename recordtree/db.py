from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from collections.abc import Iterator


def connect(database_path: Path) -> sqlite3.Connection:
    raise NotImplementedError


def initialize_schema(conn: sqlite3.Connection) -> None:
    raise NotImplementedError


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
