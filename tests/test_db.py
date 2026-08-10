"""Tests for the SQLite storage module (app.db / app.config)."""

from __future__ import annotations

import importlib
import sqlite3

import pytest


@pytest.fixture
def db_module(tmp_path):
    """Provide app.db against a fresh, isolated database file.

    This deliberately avoids reloading app.config/app.db: reloading mutates
    module-level global state (app.db's cached DB_PATH) for the remainder of
    the pytest session, which previously caused unrelated tests elsewhere in
    the suite (e.g. test_shorten.py/test_redirect.py) to silently write into
    this fixture's leftover tmp_path database instead of their own. Every
    helper in app.db already accepts an explicit db_path, so tests pass the
    isolated path directly instead of relying on process-wide state.
    """
    db_file = tmp_path / "test_snipurl.db"

    import app.db as db

    db.init_db(str(db_file))

    yield db, db_file


def test_import_creates_file_and_schema(db_module):
    """Importing (and thus initialising) app.db creates the file and table."""
    db, db_file = db_module

    assert db_file.exists()

    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='links'"
        )
        assert cur.fetchone() is not None
    finally:
        conn.close()


def test_snipurl_db_env_var_overrides_default(monkeypatch):
    """SNIPURL_DB, when unset, falls back to the ./snipurl.db default."""
    import app.config as config

    monkeypatch.delenv("SNIPURL_DB", raising=False)
    importlib.reload(config)
    assert config.DB_PATH == "./snipurl.db"

    monkeypatch.setenv("SNIPURL_DB", "/tmp/custom-snipurl.db")
    importlib.reload(config)
    assert config.DB_PATH == "/tmp/custom-snipurl.db"

    monkeypatch.delenv("SNIPURL_DB", raising=False)
    importlib.reload(config)


def test_insert_and_lookup_helpers(db_module):
    db, db_file = db_module

    db.insert_link("abc1234", "https://example.com/one", str(db_file))

    by_code = db.get_by_code("abc1234", str(db_file))
    assert by_code["url"] == "https://example.com/one"

    by_url = db.get_by_url("https://example.com/one", str(db_file))
    assert by_url["code"] == "abc1234"


def test_lookup_helpers_return_none_when_missing(db_module):
    db, db_file = db_module

    assert db.get_by_code("missing", str(db_file)) is None
    assert db.get_by_url("https://not-stored.example", str(db_file)) is None


def test_duplicate_url_insert_raises_integrity_error(db_module):
    db, db_file = db_module

    db.insert_link("code0001", "https://dup.example", str(db_file))
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_link("code0002", "https://dup.example", str(db_file))
