import os

# Must be set before any app module is imported so pydantic-settings picks them up.
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("GITHUB_TOKEN", "test-github-token")
os.environ.setdefault("GITHUB_SECRET", "test-webhook-secret")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-deepseek-key")
