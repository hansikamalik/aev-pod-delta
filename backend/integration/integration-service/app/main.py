from fastapi import FastAPI

from app.routes import health, integrations

app = FastAPI(
    title="AEV Integration Service",
    description="Manages configuration, health checks, and sync cycles for all enterprise security connectors.",
    version="1.0.0",
)

# Health & liveness
app.include_router(health.router)

# Connector & Integration Management
app.include_router(
    integrations.router,
    prefix="/api/v1/integrations",
    tags=["Integrations"],
)


@app.get("/")
def root():
    return {
        "service": "AEV Integration Service",
        "status": "online",
        "docs_url": "/docs",
    }
