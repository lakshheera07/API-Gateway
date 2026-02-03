from fastapi import FastAPI, Response , HTTPException
from contextlib import asynccontextmanager
import uvicorn
from .core.middleware import RequestContextMiddleware
from .core.logging import setup_logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import httpx
from app.gateway.circuit_breaker import CircuitBreaker


logger = setup_logging().bind(request_id="system")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("API Gateway startup complete")
    yield
    # Shutdown
    logger.info("API Gateway shutting down")

app = FastAPI(title="My API Gateway", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
        )
# Mock downstream service failure simulation

failure_mode = {"enabled": False}


@app.post("/simulate-failure")
def enable_failure():
    failure_mode["enabled"] = True
    return {"failure_mode": "ON"}


@app.post("/simulate-recovery")
def disable_failure():
    failure_mode["enabled"] = False
    return {"failure_mode": "OFF"}


@app.get("/downstream")
def mock_downstream():
    if failure_mode["enabled"]:
        raise HTTPException(status_code=500, detail="Downstream failure")
    return {"message": "Downstream success"}

@app.get("/proxy")
async def proxy_request():
    breaker = CircuitBreaker("downstream_service")

    if breaker.is_open():
        raise HTTPException(status_code=503, detail="Circuit open")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8000/downstream")

        if response.status_code >= 500:
            breaker.record_failure()
            raise HTTPException(status_code=502, detail="Downstream error")

        breaker.record_success()
        return response.json()

    except Exception:
        breaker.record_failure()
        raise


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000,reload=True)