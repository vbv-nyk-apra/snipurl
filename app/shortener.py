"""URL shortening logic: code generation, validation, and storage."""

from __future__ import annotations

import os
import secrets
import sqlite3
import string
from urllib.parse import urlparse

from app import db

CODE_LENGTH = 7
CODE_ALPHABET = string.ascii_letters + string.digits


class InvalidURLError(ValueError):
    """Raised when a submitted URL is malformed or uses a disallowed scheme."""


def _default_base_url() -> str:
    return os.environ.get("SNIPURL_BASE_URL", "http://localhost:8080")


def validate_url(url: str) -> str:
    """Validate that ``url`` is a well-formed http(s) URL.

    Returns the URL unchanged if valid, otherwise raises InvalidURLError.
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string.")

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidURLError(f"URL could not be parsed: {exc}") from exc

    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(
            f"URL scheme must be 'http' or 'https', got '{parsed.scheme or ''}'."
        )

    if not parsed.netloc:
        raise InvalidURLError("URL must include a host.")

    return url


def generate_code(length: int = CODE_LENGTH) -> str:
    """Generate a random URL-safe code of the given length."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def is_valid_code_shape(code: str) -> bool:
    """Return True if ``code`` has the expected length and alphabet.

    Does not check whether the code is actually registered; callers should
    treat a shape-invalid code the same as an unknown one (404, not 500).
    """
    if not isinstance(code, str) or len(code) != CODE_LENGTH:
        return False
    return all(ch in CODE_ALPHABET for ch in code)


class Shortener:
    """URL shortener backed by the SQLite store in :mod:`app.db`.

    Maps long URLs <-> short codes. Idempotent: shortening the same URL
    twice returns the same code. The SQLite ``links`` table (and its UNIQUE
    constraint on ``url``) is the sole source of truth -- no in-memory dict
    is kept.
    """

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        base = self._base_url if self._base_url is not None else _default_base_url()
        return base.rstrip("/")

    def shorten(self, url: str) -> dict:
        """Create (or reuse) a short code for ``url``.

        Returns a dict with "code" and "short_url" keys.
        Raises InvalidURLError if the URL is malformed or non-http(s).
        """
        validate_url(url)

        existing = db.get_by_url(url)
        if existing is not None:
            code = existing["code"]
        else:
            code = self._insert_with_retry(url)

        return {"code": code, "short_url": f"{self.base_url}/{code}"}

    def resolve(self, code: str) -> str | None:
        """Return the long URL for ``code``, or None if not found or malformed."""
        if not is_valid_code_shape(code):
            return None
        row = db.get_by_code(code)
        return row["url"] if row is not None else None

    def _generate_unique_code(self) -> str:
        code = generate_code()
        while db.get_by_code(code) is not None:
            code = generate_code()
        return code

    def _insert_with_retry(self, url: str, max_attempts: int = 5) -> str:
        """Insert ``url`` under a freshly generated code, retrying on a
        code (PRIMARY KEY) collision.

        The uniqueness probe in :meth:`_generate_unique_code` narrows the
        window but doesn't close it: another request can still claim the
        same code between the probe and this INSERT. A URL (UNIQUE) clash
        means someone else concurrently stored this exact URL, so we return
        their code instead of retrying; a code clash is regenerated up to
        ``max_attempts`` times before failing cleanly.
        """
        last_error: sqlite3.IntegrityError | None = None
        for _ in range(max_attempts):
            code = self._generate_unique_code()
            try:
                db.insert_link(code, url)
                return code
            except sqlite3.IntegrityError as exc:
                existing = db.get_by_url(url)
                if existing is not None:
                    return existing["code"]
                last_error = exc

        raise RuntimeError(
            f"Could not generate a unique short code after {max_attempts} attempts"
        ) from last_error


# Module-level default store used by the FastAPI app.
shortener = Shortener()
