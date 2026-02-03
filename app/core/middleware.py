import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from .logging import setup_logging

logger = setup_logging()

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()


        # attach request ID to request state
        request.state.request_id = request_id

        try:
            response: Response = await call_next(request)
        except Exception as e:
            logger.exception("Unhandled exception occurred",
                              extra={"request_id": request_id}
                )
            raise e
        
        # add custom headers to response
        process_time_ms = (time.perf_counter() - start_time) * 1000
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