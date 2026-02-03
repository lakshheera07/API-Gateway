from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_request_id_header_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != ""

def test_process_time_header_present_and_latency():
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    latency = float(response.headers["X-Process-Time"])
    assert latency >= 0