"""Regression test for bead .10's third acceptance criterion: a code
created through one app/store instance still resolves after the app is
"restarted" against the same on-disk database file.

This spawns real, separate subprocesses (one per "process") rather than
using ``importlib.reload`` in-process. Reload-based restart simulation
(see tests/test_db.py's ``db_module`` fixture) only reloads app.config
and app.db, not app.shortener -- it doesn't reliably prove there is no
process-lifetime cache anywhere in the stack, and its teardown leaking
state was flagged as a follow-up risk during review. A subprocess is a
genuine fresh process: no module-level state of any kind can survive
between the two calls below, so this actually exercises "no in-memory
dict is the source of truth" rather than just "app.db forgot its old
path".
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap


def _run_in_subprocess(db_path: str, code_snippet: str) -> str:
    """Run ``code_snippet`` in a brand-new interpreter with SNIPURL_DB set.

    Returns stdout, stripped. Raises an AssertionError with the captured
    stdout/stderr if the subprocess exits non-zero.
    """
    env = dict(os.environ)
    env["SNIPURL_DB"] = db_path
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code_snippet)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"subprocess failed (rc={result.returncode}):\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    return result.stdout.strip()


def test_code_created_before_a_restart_still_resolves_after_it():
    """A code created by one process resolves correctly in a later one."""
    tmp_dir = tempfile.mkdtemp(prefix="snipurl-restart-test-")
    db_path = os.path.join(tmp_dir, "restart.db")
    url = "https://example.com/restart-target"

    code = _run_in_subprocess(
        db_path,
        f"""
        from app.shortener import Shortener
        print(Shortener().shorten({url!r})["code"])
        """,
    )
    assert code, "first process did not return a code"

    # Simulate the app restarting: a brand-new process, brand-new
    # Shortener instance, same underlying SNIPURL_DB file.
    resolved = _run_in_subprocess(
        db_path,
        f"""
        from app.shortener import Shortener
        print(Shortener().resolve({code!r}))
        """,
    )
    assert resolved == url

    # And idempotency holds across the restart too: re-shortening the
    # same URL in the "new" process returns the original code rather
    # than minting a second one.
    reshortened_code = _run_in_subprocess(
        db_path,
        f"""
        from app.shortener import Shortener
        print(Shortener().shorten({url!r})["code"])
        """,
    )
    assert reshortened_code == code
