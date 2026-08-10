# snipurl architecture

## Overview

snipurl is a small FastAPI service that shortens URLs to fixed-length codes,
persists the mapping in SQLite, and redirects clients that follow a short
code back to the original URL. The service is intentionally minimal: a
single FastAPI app module, a thin storage module, and a shortening/validation
module in between.

## Module layout and responsibilities

- `app/config.py` -- reads process configuration from the environment. This
  is the single source of truth for the database path (`SNIPURL_DB`,
  defaulting to `./snipurl.db`). Nothing else should read `os.environ`
  directly for settings that belong here.
- `app/db.py` -- the SQLite storage layer. It owns the schema
  (`links(code PRIMARY KEY, url UNIQUE, clicks, created_at)`) and exposes
  small, explicit functions (`get_connection`, `init_db`, `insert_link`,
  `get_by_code`, `get_by_url`) that each open and close their own
  connection. Every function accepts an optional `db_path` override so
  callers (including tests) can point at an isolated database without
  mutating global state.
- `app/shortener.py` -- business logic: URL validation, code generation, and
  the `Shortener` class that ties validation and storage together for the
  `/shorten` and `/{code}` behaviours.
- `app/main.py` -- the FastAPI routes themselves, kept intentionally thin:
  each route validates input, delegates to `shortener`, and translates
  domain errors into HTTP responses.

## Key design decisions

**SQLite is the sole source of truth; no in-memory cache.** Early designs
for this kind of service are tempted to keep an in-memory dict for speed and
write-through to SQLite for durability. This service does not do that: every
lookup and insert goes straight to SQLite. The `url` column's UNIQUE
constraint is relied on as the actual idempotency guarantee (see below)
rather than being belt-and-suspenders alongside an in-memory check that could
drift out of sync with the database, especially across multiple worker
processes.

**Idempotency and collision-safety live in the database's constraints, not
just in Python.** `insert_link` does no "does this exist already" check
before inserting -- it relies on `code TEXT PRIMARY KEY` and
`url TEXT UNIQUE` to reject duplicates atomically. `Shortener.shorten`
generates a code, probes for an existing row, and only falls back to a
generate-and-insert-with-retry path when there isn't a hit already. The
probe-then-insert sequence has an inherent TOCTOU window under concurrent
writers, which is handled explicitly (see "Collision handling" below) rather
than assumed away.

**Malformed-but-well-formed-looking input degrades to 404, not 500.** A short
code that has the right length and alphabet but was never actually issued,
and a short code that is simply the wrong shape, are treated identically by
the redirect route: both produce a 404. `is_valid_code_shape` exists
specifically so a shape check can short-circuit before ever touching the
database, keeping the "unknown code" and "malformed code" paths uniform for
callers.

**Schema creation is a side effect of import, not a separate migration
step.** `app/db.py` calls `init_db()` at module import time. This keeps the
service dependency-free for a schema with a single table, at the cost of
making "does the file exist yet" implicitly tied to "has this module been
imported". Storage functions accepting an explicit `db_path` is what makes
this tolerable for testing (see "Testing approach" below) -- without that
escape hatch, import-time side effects and test isolation would be in direct
tension.

## Collision handling under concurrent writers

Short-code generation is randomized (`secrets.choice` over an
alphanumeric alphabet at a fixed length), so collisions are rare but
possible, and become likely enough to test deterministically once multiple
writers race on the same code. The uniqueness probe in
`_generate_unique_code` (checking `get_by_code` before returning a candidate)
narrows the collision window but cannot close it, because another writer can
still claim the same code between the probe and the actual `INSERT`.

The chosen resolution: catch the `sqlite3.IntegrityError` from the `INSERT`
and disambiguate by which constraint fired.

- If the losing writer's URL now resolves to a different writer's code (a
  `url` UNIQUE clash), the two writers were racing to shorten the *same*
  URL -- return the winning writer's code rather than erroring, preserving
  idempotency even under a race.
- If it was a `code` PRIMARY KEY clash instead, regenerate and retry, up to a
  bounded number of attempts, before failing with a clean, explicit error
  rather than letting a raw `IntegrityError` become an unhandled 500.

This means idempotency ("shortening the same URL twice returns the same
code") holds even when two requests for the same URL are in flight at once,
not just under sequential access.

## Testing approach

- Tests never touch the real `./snipurl.db`. `tests/conftest.py` points
  `SNIPURL_DB` at a fresh temp directory before any `app.*` module is
  imported by collection, so the application's own default-path behaviour
  is exercised safely.
- Fixtures that need an isolated database pass `db_path` explicitly into
  every `app.db` call rather than reloading `app.config`/`app.db` via
  `importlib.reload`. Reloading mutates *process-wide* module state (the
  cached `DB_PATH`), which leaks between tests in ways that are easy to miss
  in an individual test's diff but which corrupt unrelated tests elsewhere in
  the same suite. Prefer passing configuration explicitly at the call site
  over relying on module-reload-based isolation.
- Restart/persistence behaviour (i.e. "data written before a restart is
  still there after one") is tested by spawning a real subprocess rather
  than using `importlib.reload` to simulate a fresh process. A reload does
  not reproduce the actual conditions of a process restart (fresh
  interpreter, fresh module globals, fresh file handles), so a claim like
  "survives restart" is only trustworthy if it is tested against an actual
  new process.

## Known gaps (scoped but not yet built)

The service as shipped covers create/redirect/persist. The following are
designed-for but not yet implemented, and are tracked as open backlog rather
than silently dropped:

- Rate limiting on code creation per client IP.
- A click-analytics endpoint (counting redirects and exposing per-code
  stats).
- Containerization (Dockerfile/compose) and an accompanying quickstart
  README with curl examples.
- An end-to-end integration test suite that exercises the service over real
  HTTP against a live server process, including sustained-load behaviour.
- Hardening SQLite for concurrent writers beyond the single-row collision
  retry described above (e.g. under the load patterns the integration suite
  is meant to exercise).
