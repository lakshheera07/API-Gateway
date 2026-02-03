from unittest.mock import patch
import time
from app.gateway.circuit_breaker import CircuitBreaker
from app.core.config import settings


def test_circuit_starts_closed():
    with patch("app.gateway.circuit_breaker.redis_client") as mock_redis:
        mock_redis.get.return_value = None

        breaker = CircuitBreaker("test_service")

        assert breaker.is_open() is False


def test_circuit_opens_after_threshold():
    with patch("app.gateway.circuit_breaker.redis_client") as mock_redis:
        # Simulate increasing failure count
        mock_redis.incr.side_effect = list(
            range(1, settings.CIRCUIT_FAILURE_THRESHOLD + 1)
        )
        mock_redis.get.return_value = None

        breaker = CircuitBreaker("test_service")

        for _ in range(settings.CIRCUIT_FAILURE_THRESHOLD):
            breaker.record_failure()

        mock_redis.set.assert_any_call(
            "circuit:test_service:state", "OPEN"
        )


def test_open_circuit_blocks_requests():
    with patch("app.gateway.circuit_breaker.redis_client") as mock_redis:
        mock_redis.get.side_effect = ["OPEN", str(time.time())]

        breaker = CircuitBreaker("test_service")

        assert breaker.is_open() is True


def test_circuit_moves_to_half_open_after_timeout():
    with patch("app.gateway.circuit_breaker.redis_client") as mock_redis:
        old_time = time.time() - (settings.CIRCUIT_RECOVERY_TIMEOUT + 5)

        mock_redis.get.side_effect = ["OPEN", str(old_time)]

        breaker = CircuitBreaker("test_service")

        assert breaker.is_open() is False
        mock_redis.set.assert_any_call(
            "circuit:test_service:state", "HALF_OPEN"
        )


def test_success_resets_circuit():
    with patch("app.gateway.circuit_breaker.redis_client") as mock_redis:
        breaker = CircuitBreaker("test_service")

        breaker.record_success()

        mock_redis.set.assert_any_call(
            "circuit:test_service:failures", 0
        )
        mock_redis.set.assert_any_call(
            "circuit:test_service:state", "CLOSED"
        )
