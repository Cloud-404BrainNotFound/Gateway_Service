from pydantic import BaseSettings

class Settings(BaseSettings):
    GATEWAY_PORT: int = 8080
    USER_SERVICE_URL: str = "http://localhost:8000"
    ORDER_SERVICE_URL: str = "http://localhost:8008"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()