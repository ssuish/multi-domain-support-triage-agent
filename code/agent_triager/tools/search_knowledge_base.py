import json
from pathlib import Path

from config import RAG_PERSIST_DIR, RAG_TOP_K
from agent_triager.rag.hits import format_query_hits
from agent_triager.rag.index import query_index


def _repo_root_from_tools() -> Path:
    return Path(__file__).resolve().parents[3]


def search_knowledge_base(
    query: str,
    top_k: int | None = None,
    corpus: str | None = None,
) -> str:
    """Runs semantic search over the local markdown corpus (Chroma + EmbeddingGemma).

    Args:
        query (str): Natural-language query to retrieve relevant chunks.
        top_k (int | None, optional): Maximum hits to return. Defaults to ``RAG_TOP_K`` when omitted.
        corpus (str | None, optional): If set, restrict results to this corpus tag. Defaults to no filter.
    """
    repo_root = _repo_root_from_tools()
    persist = (repo_root / RAG_PERSIST_DIR).resolve()
    if not persist.exists():
        raise Exception(
            "RAG index missing; from repo root run: python scripts/build_rag_index.py"
        )

    k = top_k if top_k is not None else RAG_TOP_K
    raw = query_index(repo_root, query.strip(), k, corpus)
    hits = format_query_hits(raw)
    return json.dumps(hits, ensure_ascii=False)
