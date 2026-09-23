from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Simple liveness check. docker-compose, CI, and (later)
    monitoring all hit this to confirm the service is up.
    """
    return {"status": "ok", "service": settings.SERVICE_NAME}
