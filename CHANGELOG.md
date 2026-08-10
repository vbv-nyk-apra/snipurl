# Changelog

## snipurl: scaffold, shorten/redirect, and SQLite persistence

Sprint goal: build the snipurl URL shortener end to end -- scaffold, create
short codes, redirect through them, persist links durably, and (as
stretch scope) add rate limiting, click analytics, containerization, and an
integration test suite.

Delivered this sprint: the FastAPI scaffold with a health endpoint;
`POST /shorten` with URL validation, code generation, and idempotent
behaviour (including under concurrent requests for the same URL); `GET
/{code}` redirect with uniform 404 handling for unknown and malformed
codes; and a SQLite-backed storage layer with no in-memory fallback, whose
schema is created automatically on import. Two correctness issues surfaced
and were fixed during the sprint: a test fixture that leaked global
database-path state across the suite via module reloading, and a short-code
generation race that could otherwise surface as an unhandled server error
under concurrent writers -- both are now covered by dedicated regression
tests.

Carried forward (not yet implemented): rate limiting on code creation,
click-analytics endpoint, Dockerfile/docker-compose and a quickstart README,
and an end-to-end integration test suite over real HTTP. These remain
tracked as open backlog for a future sprint.

```
Budget ceiling: not set (no --budget flag) -- unlimited for this run.
Tracked spend (priced dispatches only): $10.7102.
Remaining budget: unknown/unbounded.
Integ-test-runner spend: $0.0000 -- no integ-test-runner dispatch ran this sprint (no playbook found, or deploy never succeeded).
Pricing source: all 36 priced dispatch(es) used real per-member rates (get_member_model_pricing).
Note: dispatches using an unpriced model id are not reflected above (see N10, feedback-reassessment.md) -- this figure is a lower bound on actual spend, not a complete total, and is reported honestly rather than fabricated.
```
