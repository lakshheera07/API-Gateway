from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_endpoint_exists():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

def test_request_metrics_increment():
    # trigger request
    client.get("/health")

    response = client.get("/metrics")
    metrics = response.text

    assert response.status_code == 200
    assert "http_requests_total" in metrics
    assert "http_request_latency_ms_bucket" in metrics
    assert "http_request_latency_ms_count" in metrics
    assert "http_request_latency_ms_sum" in metrics

