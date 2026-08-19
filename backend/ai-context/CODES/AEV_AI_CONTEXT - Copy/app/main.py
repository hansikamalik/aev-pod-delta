from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import engine, Base, get_db
from app.models import AIMemory, Asset, PromptTemplate
from app.schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryDelete,
    AssetSearchRequest,
    TemplateCreate,
    TemplateUpdate
)
from app.embedding import generate_embedding


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AEV AI Context Service",
    description=(
        "AI Context Service with Memory CRUD, User Isolation, "
        "Memory Types, Template Versioning and Asset Vector Search"
    ),
    version="4.0.0"
)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to AEV AI Context Service"
    }


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }


# --------------------------------------------------
# CREATE MEMORY
# --------------------------------------------------

@app.post("/memory")
def create_memory(
    data: MemoryCreate,
    db: Session = Depends(get_db)
):
    try:
        embedding_vector = generate_embedding(
            data.conversation
        )

        new_memory = AIMemory(
            user_id=data.user_id,
            conversation=data.conversation,
            memory_type=data.memory_type,
            embedding=embedding_vector
        )

        db.add(new_memory)
        db.commit()
        db.refresh(new_memory)

        return {
            "message": "Memory and embedding saved successfully",
            "id": new_memory.id,
            "user_id": new_memory.user_id,
            "conversation": new_memory.conversation,
            "memory_type": new_memory.memory_type,
            "embedding_dimension": len(embedding_vector)
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# GET ALL MEMORY
# --------------------------------------------------

@app.get("/memory")
def get_all_memory(
    db: Session = Depends(get_db)
):
    memories = db.query(AIMemory).all()

    return [
        {
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type,
            "created_at": memory.created_at,
            "last_used_at": memory.last_used_at,
            "has_embedding": memory.embedding is not None
        }
        for memory in memories
    ]


# --------------------------------------------------
# GET USER MEMORY
# --------------------------------------------------

@app.get("/memory/user/{user_id}")
def get_user_memory(
    user_id: str,
    db: Session = Depends(get_db)
):
    memories = (
        db.query(AIMemory)
        .filter(AIMemory.user_id == user_id)
        .all()
    )

    return [
        {
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type,
            "created_at": memory.created_at,
            "last_used_at": memory.last_used_at,
            "has_embedding": memory.embedding is not None
        }
        for memory in memories
    ]


# --------------------------------------------------
# UPDATE MEMORY
# --------------------------------------------------

@app.put("/memory/{memory_id}")
def update_memory(
    memory_id: int,
    data: MemoryUpdate,
    db: Session = Depends(get_db)
):
    memory = (
        db.query(AIMemory)
        .filter(
            AIMemory.id == memory_id,
            AIMemory.user_id == data.user_id
        )
        .first()
    )

    if not memory:
        raise HTTPException(
            status_code=404,
            detail="Memory not found for this user"
        )

    try:
        if data.conversation is not None:
            memory.conversation = data.conversation
            memory.embedding = generate_embedding(
                data.conversation
            )

        if data.memory_type is not None:
            memory.memory_type = data.memory_type

        memory.last_used_at = func.now()

        db.commit()
        db.refresh(memory)

        return {
            "message": "Memory updated successfully",
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# DELETE MEMORY
# --------------------------------------------------

@app.delete("/memory/{memory_id}")
def delete_memory(
    memory_id: int,
    data: MemoryDelete,
    db: Session = Depends(get_db)
):
    memory = (
        db.query(AIMemory)
        .filter(
            AIMemory.id == memory_id,
            AIMemory.user_id == data.user_id
        )
        .first()
    )

    if not memory:
        raise HTTPException(
            status_code=404,
            detail="Memory not found for this user"
        )

    try:
        db.delete(memory)
        db.commit()

        return {
            "message": "Memory deleted successfully"
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# ASSET VECTOR SEARCH
# --------------------------------------------------

@app.post("/copilot/asset-search")
def asset_search(
    data: AssetSearchRequest,
    db: Session = Depends(get_db)
):
    try:
        query_embedding = generate_embedding(
            data.query
        )

        distance = Asset.embedding.cosine_distance(
            query_embedding
        )

        rows = (
            db.query(
                Asset,
                distance.label("distance")
            )
            .filter(Asset.embedding.is_not(None))
            .order_by(distance)
            .limit(data.limit)
            .all()
        )

        results = []

        for asset, distance_value in rows:
            similarity_score = (
                1 - float(distance_value)
            )

            results.append({
                "id": asset.id,
                "asset_name": asset.asset_name,
                "asset_type": asset.asset_type,
                "operating_system": asset.operating_system,
                "ip_address": asset.ip_address,
                "risk_score": asset.risk_score,
                "description": asset.description,
                "similarity_score": round(
                    similarity_score,
                    4
                )
            })

        return {
            "query": data.query,
            "total_results": len(results),
            "results": results
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# CREATE PROMPT TEMPLATE - VERSION 1
# --------------------------------------------------

@app.post("/templates")
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db)
):
    existing = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name
            == data.template_name
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Template already exists. "
                "Use update endpoint to create a new version."
            )
        )

    try:
        template = PromptTemplate(
            template_name=data.template_name,
            version=1,
            template_content=data.template_content,
            is_active=True
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return {
            "message": "Template created successfully",
            "id": template.id,
            "template_name": template.template_name,
            "version": template.version,
            "template_content": template.template_content,
            "is_active": template.is_active
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# UPDATE TEMPLATE - CREATE NEW VERSION
# --------------------------------------------------

@app.put("/templates/{template_name}")
def update_template(
    template_name: str,
    data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    current_template = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name
            == template_name,
            PromptTemplate.is_active == True
        )
        .order_by(
            PromptTemplate.version.desc()
        )
        .first()
    )

    if not current_template:
        raise HTTPException(
            status_code=404,
            detail="Template not found"
        )

    try:
        current_template.is_active = False

        new_template = PromptTemplate(
            template_name=template_name,
            version=current_template.version + 1,
            template_content=data.template_content,
            is_active=True
        )

        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        return {
            "message": "New template version created successfully",
            "template_name": new_template.template_name,
            "version": new_template.version,
            "template_content": new_template.template_content,
            "is_active": new_template.is_active
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# GET TEMPLATE VERSION HISTORY
# --------------------------------------------------

@app.get("/templates/{template_name}/versions")
def get_template_versions(
    template_name: str,
    db: Session = Depends(get_db)
):
    templates = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name
            == template_name
        )
        .order_by(
            PromptTemplate.version.asc()
        )
        .all()
    )

    if not templates:
        raise HTTPException(
            status_code=404,
            detail="Template not found"
        )

    return [
        {
            "id": template.id,
            "template_name": template.template_name,
            "version": template.version,
            "template_content": template.template_content,
            "is_active": template.is_active,
            "created_at": template.created_at
        }
        for template in templates
    ]