import json
from pathlib import Path

from config import RAG_PERSIST_DIR, RAG_TOP_K
from agent_triager.rag.index import query_index


def _repo_root_from_tools() -> Path:
    return Path(__file__).resolve().parents[3]


def search_knowledge_base(
    query: str,
    top_k: int | None = None,
    corpus: str | None = None,
) -> str:
    """Runs semantic search over the local markdown corpus (Chroma + BGE embeddings).

    Args:
        query (str): Natural-language query to retrieve relevant chunks.
        top_k (int | None, optional): Maximum hits to return. Defaults to ``RAG_TOP_K`` when omitted.
        corpus (str | None, optional): If set, restrict results to this corpus tag. Defaults to no filter.
    """
    repo_root = _repo_root_from_tools()
    persist = (repo_root / RAG_PERSIST_DIR).resolve()
    if not persist.exists():
        raise Exception(
            "RAG index missing; from repo root run: python code/build_rag_index.py"
        )

    k = top_k if top_k is not None else RAG_TOP_K
    raw = query_index(repo_root, query.strip(), k, corpus)
    ids = (raw.get("ids") or [[]])[0]
    texts = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    hits = []
    for i, cid in enumerate(ids):
        meta = dict(metas[i] or {})
        hits.append(
            {
                "chunk_id": cid,
                "text": texts[i],
                "rel_path": meta.get("rel_path", ""),
                "source_url": meta.get("source_url", ""),
                "title": meta.get("title", ""),
                "corpus": meta.get("corpus", ""),
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return json.dumps(hits, ensure_ascii=False)
