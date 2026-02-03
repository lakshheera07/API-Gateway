import time
import uuid
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from app.core.logging import setup_logging
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.gateway.rate_limiter import is_rate_limited


logger = setup_logging()

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # attach request ID to request state
        request.state.request_id = request_id

        # Rate limiting
        client_ip = request.client.host
        if is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        try:
            response: Response = await call_next(request)
        except Exception as e:
            logger.exception("Unhandled exception occurred",
                              extra={"request_id": request_id}
                )
            raise e
        
        # add custom headers to response
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=str(request.url.path),
            http_status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=str(request.url.path)
        ).observe(process_time_ms)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time_ms, 2))

        logger.bind(request_id=request_id).info("Request processed Successfully",
                     extra={"request_id": request_id,
                             "process_time": round(process_time_ms, 2),
                             "status_code": response.status_code,
                             "method": request.method,
                             "url": str(request.url),
                             "latency": round(process_time_ms, 2)}
            )
        return response