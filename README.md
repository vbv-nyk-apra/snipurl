# snipurl

A small URL shortener service built with FastAPI and SQLite.

Create a short code for a long URL, follow the short code to be redirected,
and see how many times each code has been used.

## Current capabilities

- `GET /health` -- liveness check, returns `{"status": "ok"}`.
- `POST /shorten` -- accepts `{"url": "..."}`, validates it is a well-formed
  `http(s)` URL, and returns `{"code": ..., "short_url": ...}`. Shortening
  the same URL twice (including concurrently) returns the same code.
- `GET /{code}` -- redirects (307) to the stored URL for a valid code, or
  returns a JSON 404 if the code is unknown or malformed.
- Persistence is SQLite-backed (see `docs/architecture.md`); there is no
  in-memory fallback, so stored links survive an application restart.

## Not yet implemented

The following are designed for but not yet built -- see the open backlog for
details:

- Rate limiting on `/shorten` by client IP.
- A click-analytics endpoint.
- Containerization (Dockerfile/docker-compose) and a quickstart with curl
  examples.
- An end-to-end integration test suite exercising the service over real
  HTTP.

## Configuration

- `SNIPURL_DB` -- path to the SQLite database file (default `./snipurl.db`).
- `SNIPURL_BASE_URL` -- base URL used when building `short_url` in responses
  (default `http://localhost:8080`).

See `docs/architecture.md` for design decisions and rationale.
