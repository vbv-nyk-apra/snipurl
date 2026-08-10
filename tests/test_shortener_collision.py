"""Regression tests for short-code collision handling in app.shortener.

app.shortener.Shortener._generate_unique_code() probes for an existing code
before insert, but that probe-then-insert is not atomic: another request can
claim the same code in between. Previously that race surfaced as an
unhandled sqlite3.IntegrityError (PRIMARY KEY conflict on ``code``) once it
reached db.insert_link, which the shorten() caller only caught and recovered
from when the conflict was on the ``url`` UNIQUE constraint -- a code clash
re-raised straight to an HTTP 500. These tests force that race deterministically
by making db.insert_link raise IntegrityError on demand, after the uniqueness
probe has already passed -- exactly the window the real race exploits.
"""

from __future__ import annotations

import sqlite3

import pytest

from app import db
from app.shortener import Shortener


def test_shorten_retries_on_code_collision(monkeypatch):
    """A PRIMARY KEY (code) collision is retried with a fresh code, not raised."""
    codes = iter(["codeone", "codetwo"])
    monkeypatch.setattr("app.shortener.generate_code", lambda length=7: next(codes))

    real_insert_link = db.insert_link
    call_count = {"n": 0}

    def flaky_insert_link(code, url, db_path=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Simulate another request having just claimed this code
            # between our uniqueness probe and this INSERT.
            raise sqlite3.IntegrityError("UNIQUE constraint failed: links.code")
        return real_insert_link(code, url, db_path)

    monkeypatch.setattr("app.shortener.db.insert_link", flaky_insert_link)

    shortener = Shortener()
    result = shortener.shorten("https://example.com/collision-retry")

    assert result["code"] == "codetwo"
    assert call_count["n"] == 2
    assert db.get_by_url("https://example.com/collision-retry")["code"] == "codetwo"


def test_shorten_fails_cleanly_after_repeated_code_collisions(monkeypatch):
    """If every generated code collides, shorten() fails cleanly (no 500 leak)."""
    monkeypatch.setattr("app.shortener.generate_code", lambda length=7: "stuckco")

    def always_collides(code, url, db_path=None):
        raise sqlite3.IntegrityError("UNIQUE constraint failed: links.code")

    monkeypatch.setattr("app.shortener.db.insert_link", always_collides)

    shortener = Shortener()
    with pytest.raises(RuntimeError, match="unique short code"):
        shortener.shorten("https://example.com/always-collides")
