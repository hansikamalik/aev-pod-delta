from pydantic import BaseModel, Field
from typing import Optional, Literal


MemoryType = Literal[
    "preference",
    "workflow",
    "role_context",
    "recent_topic"
]


class MemoryCreate(BaseModel):
    user_id: str
    conversation: str
    memory_type: MemoryType


class MemoryUpdate(BaseModel):
    user_id: str
    conversation: Optional[str] = None
    memory_type: Optional[MemoryType] = None


class MemoryDelete(BaseModel):
    user_id: str


class MemoryResponse(BaseModel):
    id: int
    user_id: str
    conversation: str
    memory_type: Optional[MemoryType] = None

    class Config:
        from_attributes = True


class AssetSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


# --------------------------------------------------
# PROMPT TEMPLATE SCHEMAS
# --------------------------------------------------

class TemplateCreate(BaseModel):
    template_name: str
    template_content: str


class TemplateUpdate(BaseModel):
    template_content: str