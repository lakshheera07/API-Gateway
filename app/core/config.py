from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    redis_host: str = "localhost"
    redis_port: int = 6379

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SEC: int = 60

    CIRCUIT_FAILURE_THRESHOLD: int = 5
    CIRCUIT_RECOVERY_TIMEOUT: int = 30

settings = Settings()
