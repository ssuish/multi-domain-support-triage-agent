from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config import RAG_EMBED_MODEL


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(RAG_EMBED_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]


def embed_query(q: str) -> list[float]:
    return embed_texts([q])[0]
