from fastapi import FastAPI, Response , HTTPException
from contextlib import asynccontextmanager
import uvicorn
from .core.middleware import RequestContextMiddleware
from .core.logging import setup_logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import httpx
from app.gateway.circuit_breaker import CircuitBreaker
from app.gateway.retry import retry_request
from datetime import datetime


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
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "API Gateway",
        "message": "API Gateway is operational and ready to process requests",
        "next_action": "You can start sending requests to the gateway endpoints"
    }

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
    return {
        "status": "failure_mode_enabled",
        "timestamp": datetime.now().isoformat(),
        "message": "Downstream service failure simulation is now ACTIVE",
        "what_is_happening": "All requests to /downstream will return HTTP 500 errors",
        "next_action": "Test your error handling and circuit breaker by calling /proxy or /downstream endpoints",
        "to_recover": "Call POST /simulate-recovery when ready to restore normal operation"
    }


@app.post("/simulate-recovery")
def disable_failure():
    failure_mode["enabled"] = False
    return {
        "status": "failure_mode_disabled",
        "timestamp": datetime.now().isoformat(),
        "message": "Downstream service failure simulation has been STOPPED",
        "what_is_happening": "The /downstream endpoint has been restored to normal operation",
        "next_action": "Resume normal testing or reopen the circuit breaker if it was previously opened",
        "note": "The circuit breaker state persists - you may need to wait for the timeout or manually reset it"
    }


@app.get("/downstream")
def mock_downstream():
    if failure_mode["enabled"]:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "downstream_unavailable",
                "timestamp": datetime.now().isoformat(),
                "message": "Downstream service is currently unavailable (failure mode enabled for testing)",
                "what_is_happening": "The mock downstream service has been intentionally disabled to simulate failures",
                "next_action": "Call POST /simulate-recovery to re-enable the downstream service or retry through /proxy for circuit breaker testing"
            }
        )
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "message": "Downstream service responded successfully",
        "data": "Downstream success",
        "next_action": "Process the response or make additional requests as needed"
    }

@app.get("/proxy")
async def proxy_request():
    breaker = CircuitBreaker("downstream_service")

    if breaker.is_open():
        raise HTTPException(
            status_code=503,
            detail={
                "status": "circuit_breaker_open",
                "timestamp": datetime.now().isoformat(),
                "message": "Circuit breaker is OPEN - downstream service is temporarily unavailable",
                "what_is_happening": "After multiple failures, the circuit breaker has opened to prevent cascading failures and allow the downstream service time to recover",
                "next_action": "Wait for the circuit breaker timeout to expire (check system configuration), then retry your request",
                "alternatives": "You can check POST /simulate-recovery to restore service manually or contact system administrator"
            }
        )

    try:
        response = await retry_request("http://127.0.0.1:8000/downstream")

        if response.status_code >= 500:
            breaker.record_failure()
            raise HTTPException(
                status_code=502,
                detail={
                    "status": "downstream_error",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Downstream service returned an error",
                    "what_is_happening": "The downstream service responded with HTTP 500 or higher. Failure has been recorded by the circuit breaker",
                    "failure_count": "Incrementing failure counter. Circuit may open if threshold is reached",
                    "next_action": "Retry your request after a brief delay, or check the /health endpoint to verify service status",
                    "note": "If failures persist, the circuit breaker will open to prevent further cascading failures"
                }
            )

        breaker.record_success()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message": "Request successfully proxied to downstream service",
            "data": response.json(),
            "circuit_breaker_status": "healthy",
            "next_action": "Process the response from the downstream service"
        }

    except Exception as e:
        breaker.record_failure()
        raise HTTPException(
            status_code=503,
            detail={
                "status": "request_failed",
                "timestamp": datetime.now().isoformat(),
                "message": "Failed to complete the proxied request",
                "what_is_happening": f"The proxy request encountered an error: {str(e)}",
                "next_action": "Retry the request. If the problem persists, check if the downstream service is running and accessible",
                "debugging": "Check logs for more details about what went wrong"
            }
        )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000,reload=True)