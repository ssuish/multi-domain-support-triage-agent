from pathlib import Path

import chromadb

from config import RAG_COLLECTION_NAME, RAG_PERSIST_DIR

repo_root = Path(__file__).resolve().parents[1]

client = chromadb.PersistentClient(path=str(repo_root / RAG_PERSIST_DIR))
col = client.get_collection(RAG_COLLECTION_NAME)

print(col.count())
