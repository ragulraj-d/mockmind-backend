from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = "firebase-service-account.json"

    class Config:
        env_file = ".env"


settings = Settings()
