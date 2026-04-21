import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database.db",
)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
