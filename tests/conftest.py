"""Shared pytest setup for the snipurl test suite.

Points the app's SQLite storage at an isolated, temporary database file
(via the ``SNIPURL_DB`` environment variable) before any ``app.*`` module
gets imported by test collection, instead of letting tests write to the
real ``./snipurl.db`` used by the running application.
"""

from __future__ import annotations

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="snipurl-tests-")
os.environ.setdefault("SNIPURL_DB", os.path.join(_tmp_dir, "test_snipurl.db"))
