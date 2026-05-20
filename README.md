# Support ticket triage agent

A production-style **batch triage system** that ingests customer support tickets from CSV, grounds answers in an internal help-center corpus (HackerRank, Claude, and Visa content shipped with the repo), and emits **structured, reviewable predictions**—status, product area, customer-facing reply, justification, and request type—so operations teams can automate first-line handling without inventing policy.

**Origin:** Submitted as my entry to **HackerRank Orchestrate** (May 2026), a timed build around real-world agentic support workflows. Contest rules, schemas, and evaluation are in [`problem_statement.md`](problem_statement.md) and [`evalutation_criteria.md`](evalutation_criteria.md).

## What this product does

- **Deterministic batch pipeline** — one row in, one grounded prediction out; writes to `support_tickets/output.csv`.
- **Corpus-bound answers** — retrieval over local markdown in `data/` via Chroma + embeddings; no live web as a source of truth for responses (per challenge constraints).
- **Agent orchestration** — Google ADK sequential flow (retrieve, then structured format) with Pydantic output and safe fallback when parsing fails (see [`code/README.md`](code/README.md)).
- **Ops-ready configuration** — secrets via environment variables; optional repo-root `.env` loaded by `main.py` (`python-dotenv`).

## Stack

Python 3.11+, **Google ADK**, **Chroma**, **sentence-transformers** / EmbeddingGemma (details and model IDs in [`code/README.md`](code/README.md)).

## Documentation

| Doc | What it covers |
| --- | --- |
| [`code/README.md`](code/README.md) | Architecture, install, RAG index build, `main.py`, tests, troubleshooting |
| [`problem_statement.md`](problem_statement.md) | Task spec, I/O schema, constraints, submission context |
| [`evalutation_criteria.md`](evalutation_criteria.md) | Scoring rubric |

## Quickstart

Run from the **repository root** so `data/`, `support_tickets/`, and `code/.chroma` resolve correctly.

```bash
pip install .
python code/build_rag_index.py
python code/main.py
```

- **Input:** `support_tickets/support_tickets.csv` (for labeled regression rows, point `input_csv` in `main.py` at `sample_support_tickets.csv` — see [`code/README.md`](code/README.md)).
- **Output:** `support_tickets/output.csv`.

## Repository layout

```
.
├── AGENTS.md                       # AI-tool rules + transcript logging
├── problem_statement.md            # Challenge spec and I/O schema
├── README.md                       # Product overview (this file)
├── code/                           # Implementation (see code/README.md)
│   ├── README.md                   # Engineering deep-dive
│   ├── main.py                     # Batch entry point
│   └── agent_triager/              # ADK agent, tools, RAG
├── data/                           # Local help-center corpus
│   ├── hackerrank/
│   ├── claude/
│   └── visa/
└── support_tickets/
    ├── sample_support_tickets.csv  # Labeled examples
    ├── support_tickets.csv         # Challenge inputs
    └── output.csv                  # Agent predictions
```
