from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint_returns_200_and_ok():
    """Test that the health endpoint returns 200 and {"status": "ok"}."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
