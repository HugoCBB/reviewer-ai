from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv

class Settings(BaseSettings):
    google_api_key: str = os.getenv('GOOGLE_API_KEY')

    github_token: str = os.getenv('GITHUB_TOKEN')
    github_webhook_secret: str = os.getenv('GITHUB_SECRET')

    redis_url: str = os.getenv("REDIS_URL") or "redis://localhost:6379/0"

    gemini_model: str = "gemini-1.5-pro"
    llm_temperature: float = 0.0
    max_diff_tokens: int = 4000  

    class Config:
        env_file = ".env"


settings = Settings()