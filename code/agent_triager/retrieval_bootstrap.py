from __future__ import annotations

from pathlib import Path

from config import RAG_LOW_CONFIDENCE_RETRY_TOP_K, RAG_PERSIST_DIR, RAG_TOP_K
from agent_triager.rag.hits import format_query_hits
from agent_triager.schema import SupportTicketInput
from paths import REPO_ROOT

_COMPANY_ALIASES: dict[str, str] = {
    "hackerrank": "hackerrank",
    "claude": "claude",
    "visa": "visa",
    "none": "none",
    "other": "none",
}


def normalize_company(company: str | None) -> str:
    raw = (company or "").strip()
    if not raw:
        return "none"

    lowered = raw.lower()
    if lowered in _COMPANY_ALIASES:
        return _COMPANY_ALIASES[lowered]

    for key, value in (
        ("hackerrank", "hackerrank"),
        ("claude", "claude"),
        ("visa", "visa"),
    ):
        if key in lowered:
            return value

    return "none"


def corpus_filter_for_company(normalized_company: str) -> str | None:
    if normalized_company in ("hackerrank", "claude", "visa"):
        return normalized_company
    return None


def bootstrap_retrieve(
    ticket: SupportTicketInput,
    *,
    top_k: int | None = None,
    use_corpus_filter: bool = True,
    repo_root: Path | None = None,
) -> list[dict]:
    from agent_triager.rag.index import query_index

    root = repo_root or REPO_ROOT
    persist = (root / RAG_PERSIST_DIR).resolve()
    if not persist.exists():
        raise Exception(
            "RAG index missing; from repo root run: python scripts/build_rag_index.py"
        )

    query = f"{ticket.subject} {ticket.issue}".strip()
    normalized = normalize_company(ticket.company)
    corpus = corpus_filter_for_company(normalized) if use_corpus_filter else None
    k = top_k if top_k is not None else RAG_TOP_K
    raw = query_index(root, query, k, corpus)
    return format_query_hits(raw)


def bootstrap_retrieve_retry(ticket: SupportTicketInput, *, repo_root: Path | None = None) -> list[dict]:
    return bootstrap_retrieve(
        ticket,
        top_k=RAG_LOW_CONFIDENCE_RETRY_TOP_K,
        use_corpus_filter=False,
        repo_root=repo_root,
    )
