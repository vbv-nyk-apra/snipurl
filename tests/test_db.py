"""Tests for the SQLite storage module (app.db / app.config)."""

from __future__ import annotations

import importlib
import sqlite3

import pytest


@pytest.fixture
def db_module(tmp_path, monkeypatch):
    """Reload app.config/app.db against a fresh, isolated database file."""
    db_file = tmp_path / "test_snipurl.db"
    monkeypatch.setenv("SNIPURL_DB", str(db_file))

    import app.config as config
    import app.db as db

    importlib.reload(config)
    importlib.reload(db)

    yield db, db_file

    # Restore app.config's module state without re-triggering app.db's
    # import-time init_db() against the real default path.
    monkeypatch.delenv("SNIPURL_DB", raising=False)
    importlib.reload(config)


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
    db, _ = db_module

    db.insert_link("abc1234", "https://example.com/one")

    by_code = db.get_by_code("abc1234")
    assert by_code["url"] == "https://example.com/one"

    by_url = db.get_by_url("https://example.com/one")
    assert by_url["code"] == "abc1234"


def test_lookup_helpers_return_none_when_missing(db_module):
    db, _ = db_module

    assert db.get_by_code("missing") is None
    assert db.get_by_url("https://not-stored.example") is None


def test_duplicate_url_insert_raises_integrity_error(db_module):
    db, _ = db_module

    db.insert_link("code0001", "https://dup.example")
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_link("code0002", "https://dup.example")
