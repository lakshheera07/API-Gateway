from fastapi import FastAPI
import uvicorn
import logging
from core.middleware import RequestContextMiddleware

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="My API Gateway")

app.add_middleware(RequestContextMiddleware)    


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000,reload=True)