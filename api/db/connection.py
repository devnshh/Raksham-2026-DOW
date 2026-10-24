"""
SQLite Connection Manager for SATARK Backend.
Configures WAL mode, thread safety, and auto-initialization.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from api.config import DB_PATH

_SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"
_lock = threading.Lock()


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with WAL mode and row factory."""
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with auto-commit/rollback."""
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Initializes the SQLite database with the SQL schema and applies migrations."""
    with _lock:
        conn = get_db_connection(db_path)
        try:
            with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)

            # Idempotent column migrations for payees table
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(payees);")
            existing_cols = {row["name"] for row in cursor.fetchall()}

            if "display_name" not in existing_cols:
                conn.execute("ALTER TABLE payees ADD COLUMN display_name TEXT;")
            if "first_seen_at" not in existing_cols:
                conn.execute("ALTER TABLE payees ADD COLUMN first_seen_at TEXT;")
            if "verified" not in existing_cols:
                conn.execute("ALTER TABLE payees ADD COLUMN verified INTEGER DEFAULT 0;")
            if "is_merchant" not in existing_cols:
                conn.execute("ALTER TABLE payees ADD COLUMN is_merchant INTEGER DEFAULT 0;")

            conn.commit()
        finally:
            conn.close()

