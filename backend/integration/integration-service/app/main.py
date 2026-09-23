from fastapi import FastAPI

from app.routes import health

app = FastAPI(title="Integration Service")

app.include_router(health.router)


@app.get("/")
def root():
    return {"message": "Integration Service is running"}
