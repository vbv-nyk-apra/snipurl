"""Application configuration read from the environment."""

from __future__ import annotations

import os

#: Path to the SQLite database file. Overridable via the SNIPURL_DB
#: environment variable; defaults to ./snipurl.db in the current working
#: directory.
DB_PATH = os.environ.get("SNIPURL_DB", "./snipurl.db")
