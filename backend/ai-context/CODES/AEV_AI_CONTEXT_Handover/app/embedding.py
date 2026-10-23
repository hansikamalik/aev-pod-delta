"""Embedding helper with lazy model loading.

The model loads on the first embedding request rather than at API import time.
Pre-cache the model in deployments without outbound network access.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def generate_embedding(text: str):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding text must be a non-empty string")
    return _get_model().encode(text).tolist()
