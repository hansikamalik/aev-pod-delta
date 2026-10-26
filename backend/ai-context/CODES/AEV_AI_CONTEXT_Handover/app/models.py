from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, func
)
from pgvector.sqlalchemy import Vector

from app.database import Base


class AIMemory(Base):
    __tablename__ = "ai_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    conversation = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding = Column(Vector(384), nullable=True)
    memory_type = Column(String(50), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(String(255), nullable=False)
    asset_type = Column(String(100), nullable=True)
    operating_system = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    risk_score = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    embedding = Column(Vector(384), nullable=True)

    owner_user_id = Column(String(100), nullable=True, index=True)
    tenant_id = Column(String(100), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )
    embedding_updated_at = Column(DateTime(timezone=True), nullable=True)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    template_content = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())