"""URL shortening logic: code generation, validation, and storage."""

from __future__ import annotations

import os
import secrets
import string
from urllib.parse import urlparse

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
    """In-memory URL shortener store.

    Maps long URLs <-> short codes. Idempotent: shortening the same URL
    twice returns the same code. Replaced by SQLite-backed storage later.
    """

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url
        self._url_to_code: dict[str, str] = {}
        self._code_to_url: dict[str, str] = {}

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

        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            code = existing_code
        else:
            code = self._generate_unique_code()
            self._url_to_code[url] = code
            self._code_to_url[code] = url

        return {"code": code, "short_url": f"{self.base_url}/{code}"}

    def resolve(self, code: str) -> str | None:
        """Return the long URL for ``code``, or None if not found or malformed."""
        if not is_valid_code_shape(code):
            return None
        return self._code_to_url.get(code)

    def _generate_unique_code(self) -> str:
        code = generate_code()
        while code in self._code_to_url:
            code = generate_code()
        return code


# Module-level default store used by the FastAPI app.
shortener = Shortener()
