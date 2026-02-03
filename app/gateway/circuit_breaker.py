import time
from app.cache.redis_client import get_redis_client
from app.core.config import settings

redis_client = get_redis_client()


class CircuitBreaker:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.failure_key = f"circuit:{service_name}:failures"
        self.state_key = f"circuit:{service_name}:state"
        self.opened_at_key = f"circuit:{service_name}:opened_at"

    def is_open(self) -> bool:
        state = redis_client.get(self.state_key)

        if state == "OPEN":
            opened_at = redis_client.get(self.opened_at_key)
            if opened_at and (
                time.time() - float(opened_at)
            ) > settings.CIRCUIT_RECOVERY_TIMEOUT:
                redis_client.set(self.state_key, "HALF_OPEN")
                return False
            return True

        return False

    def record_failure(self):
        failures = redis_client.incr(self.failure_key)

        if failures >= settings.CIRCUIT_FAILURE_THRESHOLD:
            redis_client.set(self.state_key, "OPEN")
            redis_client.set(self.opened_at_key, time.time())

    def record_success(self):
        redis_client.set(self.failure_key, 0)
        redis_client.set(self.state_key, "CLOSED")
