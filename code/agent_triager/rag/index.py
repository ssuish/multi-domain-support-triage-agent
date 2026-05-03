from __future__ import annotations

from pathlib import Path

import chromadb

from config import RAG_COLLECTION_NAME, RAG_EMBED_BATCH_SIZE, RAG_PERSIST_DIR
from agent_triager.rag.chunking import chunk_markdown
from agent_triager.rag.documents import iter_corpus_docs
from agent_triager.rag.embeddings import embed_query, embed_texts


def get_collection(repo_root: Path) -> chromadb.Collection:
    client = chromadb.PersistentClient(
        path=str((repo_root / RAG_PERSIST_DIR).resolve())
    )
    return client.get_or_create_collection(
        name=RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(repo_root: Path) -> tuple[int, int]:
    col = get_collection(repo_root)
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    n_source_files = 0

    for doc in iter_corpus_docs(repo_root):
        n_source_files += 1
        for c in chunk_markdown(doc.rel_path, doc.title, doc.body):
            ids.append(c.chunk_id)
            docs.append(c.text)
            metas.append(
                {
                    "rel_path": doc.rel_path,
                    "corpus": doc.corpus,
                    "title": doc.title,
                    "source_url": doc.source_url or "",
                    "section_heading": c.section_heading,
                    "doc_type": doc.doc_type,
                }
            )

    batch = max(32, RAG_EMBED_BATCH_SIZE * 4)
    for i in range(0, len(ids), batch):
        emb = embed_texts(docs[i : i + batch])
        col.upsert(
            ids=ids[i : i + batch],
            documents=docs[i : i + batch],
            metadatas=metas[i : i + batch],
            embeddings=emb,
        )

    return n_source_files, col.count()


def query_index(
    repo_root: Path,
    query: str,
    top_k: int,
    corpus: str | None,
) -> dict:
    col = get_collection(repo_root)
    q_emb = embed_query(query)
    where = {"corpus": corpus} if corpus else None
    return col.query(query_embeddings=[q_emb], n_results=top_k, where=where)
