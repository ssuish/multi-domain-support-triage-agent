from __future__ import annotations


def format_query_hits(raw: dict) -> list[dict]:
    ids = (raw.get("ids") or [[]])[0]
    texts = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    hits: list[dict] = []
    for i, chunk_id in enumerate(ids):
        meta = dict(metas[i] or {})
        hits.append(
            {
                "chunk_id": chunk_id,
                "text": texts[i],
                "rel_path": meta.get("rel_path", ""),
                "source_url": meta.get("source_url", ""),
                "title": meta.get("title", ""),
                "corpus": meta.get("corpus", ""),
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return hits
