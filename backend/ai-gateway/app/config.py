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

    # JWT Cryptographic Trust Boundary (Pod Alpha -> Pod Delta)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "aev-pod-alpha-development-secret-key-32bytes-min")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "aev-pod-alpha")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "aev-pod-delta")
    JWT_AUTH_REQUIRED = os.getenv("JWT_AUTH_REQUIRED", "false").lower() == "true"


settings = Settings()
