from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from config import RAG_EMBED_BATCH_SIZE, RAG_EMBED_MODEL, RAG_EMBED_QUERY_PREFIX


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(RAG_EMBED_MODEL)


def _encode_kwargs() -> dict:
    return {"normalize_embeddings": True, "show_progress_bar": False}


def _rows_to_list(v) -> list[list[float]]:
    arr = np.asarray(v)
    if arr.ndim == 1:
        return [arr.astype(float).tolist()]
    return [arr[i].astype(float).tolist() for i in range(arr.shape[0])]


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    kw = _encode_kwargs()
    bs = max(1, RAG_EMBED_BATCH_SIZE)
    rows: list[list[float]] = []

    if hasattr(model, "encode_document"):
        for i in range(0, len(texts), bs):
            chunk = texts[i : i + bs]
            raw = model.encode_document(chunk, batch_size=len(chunk), **kw)
            rows.extend(_rows_to_list(raw))
        return rows

    for i in range(0, len(texts), bs):
        chunk = texts[i : i + bs]
        raw = model.encode(chunk, batch_size=len(chunk), **kw)
        rows.extend(_rows_to_list(raw))
    return rows


def embed_query(q: str) -> list[float]:
    model = get_model()
    kw = _encode_kwargs()
    text = q.strip()
    if RAG_EMBED_QUERY_PREFIX:
        text = f"{RAG_EMBED_QUERY_PREFIX}{text}"

    if hasattr(model, "encode_query"):
        raw = model.encode_query(text, **kw)
        return _rows_to_list(raw)[0]

    raw = model.encode([text], batch_size=1, **kw)
    return _rows_to_list(raw)[0]
