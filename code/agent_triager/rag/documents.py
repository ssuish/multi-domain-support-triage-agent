from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import frontmatter

from config import RAG_DATA_DIR


@dataclass(frozen=True)
class CorpusDoc:
    rel_path: str
    corpus: str
    title: str
    source_url: str
    body: str
    doc_type: str


def iter_corpus_docs(repo_root: Path) -> Iterator[CorpusDoc]:
    data_root = (repo_root / RAG_DATA_DIR).resolve()
    for path in sorted(data_root.rglob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        parts = path.relative_to(data_root).parts
        corpus = parts[0] if parts else ""

        post = frontmatter.load(path)
        meta = post.metadata or {}
        title = str(meta.get("title") or path.stem)
        source_url = str(meta.get("source_url") or "")
        body = post.content or ""
        doc_type = "hub" if path.name == "index.md" else "article"

        yield CorpusDoc(
            rel_path=rel,
            corpus=corpus,
            title=title,
            source_url=source_url,
            body=body.strip(),
            doc_type=doc_type,
        )

