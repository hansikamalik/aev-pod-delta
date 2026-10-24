import os


class Settings:
    APP_NAME = "AI Gateway Service"
    VERSION = "1.0.0"

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 8000))

    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # AI Context service (NL asset search). Empty = disabled, use local data.
    AI_CONTEXT_URL = os.getenv("AI_CONTEXT_URL", "").strip().rstrip("/")
    AI_CONTEXT_TIMEOUT = float(os.getenv("AI_CONTEXT_TIMEOUT", "3"))
    AI_CONTEXT_TOKEN = os.getenv("AI_CONTEXT_TOKEN", "").strip()


settings = Settings()
