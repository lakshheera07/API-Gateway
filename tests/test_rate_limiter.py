from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_request_allowed_under_rate_limit():
    with patch("app.core.middleware.is_rate_limited") as mock_limit:
        mock_limit.return_value = False

        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_request_blocked_when_rate_limited():
    with patch("app.core.middleware.is_rate_limited") as mock_limit:
        mock_limit.return_value = True

        response = client.get("/health")

        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded"
