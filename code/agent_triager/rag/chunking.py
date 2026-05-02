from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from config import RAG_CHUNK_OVERLAP_CHARS, RAG_CHUNK_SIZE_CHARS

_HEADING = re.compile(r"^#{2,3}\s+.+$", re.MULTILINE)


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    section_heading: str


def _stable_chunk_id(source_key: str) -> str:
    return hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:32]


def chunk_markdown(
    rel_path: str,
    title: str,
    body: str,
) -> list[TextChunk]:
    sections: list[str] = []
    matches = list(_HEADING.finditer(body))
    if not matches:
        sections = [body] if body else []
    else:
        if matches[0].start() > 0:
            sections.append(body[: matches[0].start()].strip())
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            sections.append(body[start:end].strip())

    out: list[TextChunk] = []
    for si, section in enumerate(sections):
        heading_line = section.splitlines()[0] if section else ""
        heading = heading_line if heading_line.startswith("#") else f"# {title}"
        text = section if section else ""
        if len(text) <= RAG_CHUNK_SIZE_CHARS:
            if text:
                cid = _stable_chunk_id(f"{rel_path}|{si}|0|{text[:200]}")
                out.append(TextChunk(chunk_id=cid, text=text, section_heading=heading))
            continue
        # sliding windows for oversized sections
        step = max(1, RAG_CHUNK_SIZE_CHARS - RAG_CHUNK_OVERLAP_CHARS)
        for w, start in enumerate(range(0, len(text), step)):
            piece = text[start : start + RAG_CHUNK_SIZE_CHARS]
            if not piece:
                break
            cid = _stable_chunk_id(f"{rel_path}|{si}|{w}|{piece[:200]}")
            out.append(TextChunk(chunk_id=cid, text=piece, section_heading=heading))
    return out
