import time
from app.cache.redis_client import get_redis_client
from app.core.config import settings

redis_client = get_redis_client()

def is_rate_limited(client_ip: str) ->bool:
    
    key = f"rate_limit:{client_ip}"
    current_ts = int(time.time())

    pipeline = redis_client.pipeline()
    pipeline.zremrangebyscore(key, 0 , current_ts - settings.RATE_LIMIT_WINDOW_SEC)
    pipeline.zadd(key, {str(current_ts): current_ts})
    pipeline.zcard(key)
    pipeline.expire(key, settings.RATE_LIMIT_WINDOW_SEC + 1)
    _, _, request_count, _ = pipeline.execute()

    return request_count > settings.RATE_LIMIT_REQUESTS



