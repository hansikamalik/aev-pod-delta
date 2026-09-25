"""
Basic config loader for the Integration Service.

Week 1 scope: just enough to load environment variables.
Real secrets (DB creds, vault tokens, etc.) get wired properly
in later weeks via HashiCorp Vault - don't put real secrets here.
"""
import os


class Settings:
    ENV: str = os.getenv("ENV", "development")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://localhost:5432/integration"
    )
    SERVICE_NAME: str = "integration-service"


settings = Settings()
