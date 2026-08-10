# Sprint Analysis: feat/snipurl

Scope issue id(s): snipurl-b7u.
Base branch: main.
Cycles run: 5.

## Progress

Closed-bead count history (per cycle evaluation): [2, 2, 5, 8, 13].
High-water-mark closed count this sprint: 16.
Final closed count: 13.
Final open-at-goal-priority count: 10.

## Deploy/Integration outcomes

No deploy failures recorded this sprint.
No integration test failures recorded this sprint.

## Reviewer-proposed newTask rejections

None.

## Final verdict

FAIL -- Reviewed net diff main..feat/snipurl (16 files, +675). WHAT IS ACTUALLY THERE AND GOOD: all 13 closed beads are genuinely reflected in the diff. Scaffold/health (app/main.py:14-16, pyproject.toml, tests/test_health.py). POST /shorten (app/main.py:19-24, app/shortener.py validate_url/generate_code, tests/test_shorten.py covers happy path, idempotency, malformed URL 422, non-http scheme 422). GET /{code} (app/main.py:27-32 with 307 + JSON 404, app/shortener.py:is_valid_code_shape so a malformed code is 404 not 500, tests/test_redirect.py covers all three). SQLite store (app/db.py with code PRIMARY KEY / url UNIQUE and import-time init_db(), app/shortener.py holds no in-memory dict). snipurl-b7u.1 is genuinely fixed: tests/test_db.py's db_module fixture no longer reloads app.config/app.db and passes db_path explicitly (verified empirically -- after a full run app.db.DB_PATH still points at the conftest temp DB, /tmp/snipurl-tests-*/test_snipurl.db, and no ./snipurl.db is created in the repo). snipurl-b7u.2 is genuinely fixed: app/shortener.py:_insert_with_retry retries the PRIMARY-KEY-collision path and returns the concurrent writer's code on a url UNIQUE clash, with tests/test_shortener_collision.py forcing the race deterministically at the exact probe-then-insert window, plus an exhaustion test. tests/test_restart_persistence.py uses real subprocesses rather than importlib.reload, which is the right call for the AC3 claim on bead ...-5-d917ae56.10. No security issues; no secrets; the diff contains no temp/tool files. WHY THIS IS STILL A FAIL: the epic's own Definition of Done is not met. snipurl-b7u requires (a) all children closed, (b) 'docker compose up' bringing the service up on port 8080, (c) the integration playbook passing end to end. There is no Dockerfile, no docker-compose.yml, and no README in the diff; there is no integration harness; there is no rate limiting and no click-analytics endpoint. Ten beads at goal priority P1 remain open, including snipurl-1786342235161-9-2b07412f (Docker/compose/README), snipurl-1786342235082-8-6aaa640a (integration suite), snipurl-1786342234926-6-82ec9cc8 (rate limit), snipurl-1786342235003-7-ecfceef4 (analytics), and the parent snipurl-1786342234848-5-d917ae56 with its still-open [test] child .11. After 5 cycles the sprint delivered roughly half the epic. No reopens: every closed bead is defensible against its own criteria, so the gap is unstarted scope, not bad work. Secondary findings are filed as newTasks below. Note on the working tree: tracked files are clean apart from the expected .beads/*.jsonl sprint churn, but the checkout carries untracked clutter (__pycache__/, snipurl.egg-info/, uv.lock, sprint.log, .claude/settings.local.json) with no .gitignore to keep it out of a future 'git add' -- filed below.

## Regression pass (once per sprint, informational)

Regression pass: not run this sprint (no regression-test-playbook.md, or the probe failed).
