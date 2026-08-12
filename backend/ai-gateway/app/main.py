from fastapi import FastAPI
from pydantic import BaseModel

try:
    from app.config import settings
    from app.client import ask_gpt
except ImportError:
    from config import settings
    from client import ask_gpt

app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "1.0"),
)


class QueryRequest(BaseModel):
    question: str


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Gateway Service"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AI Gateway Service"
    }


@app.post("/copilot/query")
def query(request: QueryRequest):
    """
    Main AI Copilot query endpoint (Week 1).
    Routes user question to active LLM engine (Gemma 4 / OpenAI / Mock).
    """
    answer = ask_gpt(request.question)
    return {
        "question": request.question,
        "answer": answer
    }
