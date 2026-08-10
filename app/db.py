"""SQLite-backed persistence for shortened links.

Importing this module creates the database file and the ``links`` schema if
they do not already exist -- no manual migration step is required. The
database path comes from :data:`app.config.DB_PATH`, which in turn honours
the ``SNIPURL_DB`` environment variable (defaulting to ``./snipurl.db``).

The ``url`` column has a schema-level UNIQUE constraint, so inserting a
duplicate URL raises ``sqlite3.IntegrityError`` regardless of what Python-side
checks a caller does (or skips).

:mod:`app.shortener` wires these helpers up as the storage layer for the
``/shorten`` and ``/{code}`` endpoints.
"""

from __future__ import annotations

import sqlite3

from app.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    code TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    clicks INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a new connection to the links database.

    ``db_path`` defaults to :data:`app.config.DB_PATH`.
    """
    path = db_path if db_path is not None else DB_PATH
    return sqlite3.connect(path)


def init_db(db_path: str | None = None) -> None:
    """Create the links table (and the containing file) if absent."""
    conn = get_connection(db_path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_link(code: str, url: str, db_path: str | None = None) -> None:
    """Insert a new (code, url) pair.

    Raises ``sqlite3.IntegrityError`` if ``code`` or ``url`` already exist,
    since both columns are constrained (PRIMARY KEY / UNIQUE) at the schema
    level.
    """
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO links (code, url) VALUES (?, ?)", (code, url))
        conn.commit()
    finally:
        conn.close()


def get_by_code(code: str, db_path: str | None = None) -> sqlite3.Row | None:
    """Return the row for ``code``, or None if it isn't stored."""
    conn = get_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM links WHERE code = ?", (code,))
        return cur.fetchone()
    finally:
        conn.close()


def get_by_url(url: str, db_path: str | None = None) -> sqlite3.Row | None:
    """Return the row for ``url``, or None if it isn't stored."""
    conn = get_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM links WHERE url = ?", (url,))
        return cur.fetchone()
    finally:
        conn.close()


# Create the schema (and the database file) as soon as this module is
# imported, so callers never have to run a manual migration step.
init_db()
