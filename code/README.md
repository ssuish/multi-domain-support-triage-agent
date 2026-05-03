# Support ticket triager (Google ADK)

Terminal agent for the HackerRank Orchestrate challenge. It reads `support_tickets/support_tickets.csv`, runs a **two-step** [Google ADK](https://google.github.io/adk-docs/) pipeline per row (retrieve → structured answer), and writes `support_tickets/output.csv`.

## Architecture

- **Orchestration:** `SequentialAgent` in `agent_triager/agent.py` — `retrieval_agent` then `format_agent`.
- **Models:** Both sub-agents use `gemini-flash-latest` (configure credentials for the Google GenAI / ADK stack in your environment).
- **Retrieval:** `search_knowledge_base` queries a **local** Chroma index over the repo’s `data/` markdown corpus (semantic search via `sentence-transformers`, model from `config.py`).
- **Output:** Structured `PredictionOut` (Pydantic) stored in session state as `triage_result`, then flattened to CSV columns in `main.py`.

## Write-up Blog

> Will be available in `docs/` it will focus on local RAG implementation and comparison of SBERT vs Embedding-Gemma models.

## Requirements

- **Python** ≥ 3.11 (see repo root `pyproject.toml`).
- **Disk / network (first run):** Building the index and loading the embedding model download weights; allow time and bandwidth once.
- **API access:** Gemini (or whatever your ADK install expects) must be available via environment variables — do not commit keys. `main.py` loads the repo-root `.env` via `python-dotenv`.

## Install

From the **repository root** (not only `code/`):

```bash
cd /path/to/hackerrank-orchestrate-may26
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .            # or: pip install -r requirements.txt if you maintain one
```

## Build the RAG Index

-   Use this build the RAG Index first before running the agent. It uses `google/embeddinggemma-300m` as the embedding model.

```bash
python code/build_rag_index.py
```

## Run the batch processing triager

- Always run from repo root so paths to data/, support_tickets/, and code/.chroma resolve correctly.

```bash
python code/main.py
```

## Test

- For testing the application.

```bash
pytest
```

