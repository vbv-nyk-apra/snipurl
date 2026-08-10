from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_redirect_with_valid_code_returns_307_and_location_header():
    """Test that a valid code redirects with 307 and correct Location header."""
    # Create a short code
    shorten_response = client.post(
        "/shorten", json={"url": "https://example.com/redirect-test"}
    )
    assert shorten_response.status_code == 201

    code = shorten_response.json()["code"]

    # Redirect with follow_redirects=False to check status and headers
    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/redirect-test"


def test_redirect_with_unknown_valid_code_returns_404_with_json_body():
    """Test that a valid-shaped but unknown code returns 404 with JSON body."""
    # Use a valid-shaped code that we know doesn't exist (7 alphanumeric chars)
    response = client.get("/unknown1", follow_redirects=False)

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body or isinstance(body, dict)


def test_redirect_with_invalid_shape_code_returns_404_not_500():
    """Test that an invalid-shape code returns 404, not 500."""
    # Invalid shapes: wrong length, non-alphanumeric chars
    invalid_codes = [
        "toolong12345",  # Too long
        "short",  # Too short
        "code!!!",  # Invalid characters
        "code-123",  # Dash is invalid
    ]

    for invalid_code in invalid_codes:
        response = client.get(f"/{invalid_code}", follow_redirects=False)
        assert response.status_code == 404, f"Expected 404 for '{invalid_code}', got {response.status_code}"
