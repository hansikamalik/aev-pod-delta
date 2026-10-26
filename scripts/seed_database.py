"""
Database seeder for Module 4 Backend (Pod Delta).
Seeds assets, AI memory, and prompt templates from the canonical dataset
into PostgreSQL with pgvector embeddings.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "aev_unified_handover_dataset.json"


def text_to_vector_384(text: str) -> str:
    """Generate a deterministic 384-dimensional normalized vector embedding from text."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    vec: List[float] = []
    for _ in range(384):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        val = (seed / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0
        vec.append(val)

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    normalized = [round(x / norm, 6) for x in vec]
    return "[" + ",".join(str(x) for x in normalized) + "]"


def seed():
    db_url = os.getenv("DATABASE_URL", "postgresql://aev:secret@localhost:5432/aevdb")
    print(f"Connecting to database: {db_url}...")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # 2. Clear existing demo data
            cur.execute("TRUNCATE TABLE assets, ai_memory, prompt_templates RESTART IDENTITY CASCADE;")

            # 3. Seed Assets
            assets = data.get("assets", [])
            semantic_cat = {item["asset_id"]: item for item in data.get("ai_context_store", {}).get("semantic_catalog", [])}
            print(f"Seeding {len(assets)} assets...")

            for a in assets:
                aid = a["id"]
                name = a["name"]
                atype = a["type"]
                os_name = a.get("operating_system", "Linux")
                ip = a.get("ip_address", "10.0.1.1")
                risk = a.get("risk_score", 50)
                owner = a.get("owner", "secops-team")
                sem = semantic_cat.get(aid, {})
                desc = f"{name} ({atype}). {sem.get('semantic_keywords', '')}. {sem.get('risk_context', '')}"
                vec = text_to_vector_384(desc)

                cur.execute(
                    """
                    INSERT INTO assets (
                        asset_name, asset_type, operating_system, ip_address,
                        risk_score, description, embedding, owner_user_id, tenant_id,
                        created_at, updated_at, embedding_updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                    """,
                    (name, atype, os_name, ip, risk, desc, vec, owner, "tenant-fintech-global"),
                )

            # 4. Seed User Memories
            memories = data.get("ai_context_store", {}).get("user_memories", [])
            print(f"Seeding {len(memories)} user memories...")
            for m in memories:
                uid = m.get("user_id", "default_user")
                note = m.get("memory_note", "")
                mtype = m.get("memory_type", "preference")
                vec = text_to_vector_384(note)
                cur.execute(
                    """
                    INSERT INTO ai_memory (user_id, conversation, memory_type, embedding, created_at, last_used_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    """,
                    (uid, note, mtype, vec),
                )

            # 5. Seed Prompt Templates
            templates = data.get("ai_context_store", {}).get("prompt_templates", [])
            print(f"Seeding {len(templates)} prompt templates...")
            for t in templates:
                cur.execute(
                    """
                    INSERT INTO prompt_templates (template_name, version, template_content, is_active, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (t.get("name", t.get("template_name")), t.get("version", 1), t.get("content", t.get("template_text")), t.get("is_active", True)),
                )

            conn.commit()

    print("✔ Database successfully seeded with canonical dataset & pgvector embeddings!")


if __name__ == "__main__":
    seed()
