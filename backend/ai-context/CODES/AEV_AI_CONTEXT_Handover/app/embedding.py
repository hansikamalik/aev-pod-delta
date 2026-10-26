"""Embedding helper with lazy model loading and deterministic fallback.

The model loads on the first embedding request rather than at API import time.
If sentence-transformers is not available, falls back to a deterministic 384-dim unit vector.
"""
from functools import lru_cache
import hashlib
import math
from typing import List


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def _deterministic_embedding_384(text: str) -> List[float]:
    """Generate a deterministic 384-dimensional normalized vector from text."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    vec: List[float] = []
    for _ in range(384):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        val = (seed / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0
        vec.append(val)

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def generate_embedding(text: str) -> List[float]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding text must be a non-empty string")
    try:
        return _get_model().encode(text).tolist()
    except Exception:
        return _deterministic_embedding_384(text)

