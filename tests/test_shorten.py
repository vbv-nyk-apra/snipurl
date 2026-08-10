import string

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CODE_LENGTH = 7
CODE_ALPHABET = set(string.ascii_letters + string.digits)


def test_shorten_happy_path_returns_valid_code_and_short_url():
    response = client.post("/shorten", json={"url": "https://example.com/happy-path"})

    assert response.status_code == 201

    body = response.json()
    code = body["code"]

    assert len(code) == CODE_LENGTH
    assert set(code) <= CODE_ALPHABET
    assert body["short_url"].endswith(code)


def test_shorten_is_idempotent_for_the_same_url():
    url = "https://example.com/idempotent-path"

    first_response = client.post("/shorten", json={"url": url})
    second_response = client.post("/shorten", json={"url": url})

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["code"] == second_response.json()["code"]


def test_shorten_rejects_malformed_url_with_422():
    response = client.post("/shorten", json={"url": "not-a-url"})

    assert response.status_code == 422


def test_shorten_rejects_non_http_scheme_with_422():
    response = client.post("/shorten", json={"url": "ftp://example.com/file"})

    assert response.status_code == 422
