from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/citations", tags=["Citations"])

class CitationRequest(BaseModel):
    text: str
    source_documents: List[str]

class CitationResponse(BaseModel):
    status: str
    citations: List[str]
    matched_count: int

@router.post("/", response_model=CitationResponse)
async def generate_citations(payload: CitationRequest):
    try:
        matched_citations = [doc for doc in payload.source_documents if doc.lower() in payload.text.lower()]
        
        return {
            "status": "success",
            "citations": matched_citations,
            "matched_count": len(matched_citations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    