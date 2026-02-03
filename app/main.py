from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from .core.middleware import RequestContextMiddleware
from .core.logging import setup_logging


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


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000,reload=True)