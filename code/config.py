RAG_DATA_DIR = "data"
RAG_PERSIST_DIR = "code/.chroma"
RAG_COLLECTION_NAME = "support_kb"
RAG_EMBED_MODEL = "google/embeddinggemma-300m"
RAG_EMBED_QUERY_PREFIX = ""
RAG_EMBED_BATCH_SIZE = 4
RAG_TOP_K = 5
RAG_CHUNK_SIZE_CHARS = 1500
RAG_CHUNK_OVERLAP_CHARS = 150

# Retrieval confidence gate (Chroma cosine distance: lower = better match).
# Tune by running bootstrap retrieval on sample_support_tickets.csv and comparing
# distance distributions for obvious FAQ rows vs off-topic rows (e.g. Iron Man actor).
RAG_MIN_HITS = 1
RAG_MAX_BEST_DISTANCE = 0.45
RAG_MAX_MEAN_TOP3_DISTANCE = 0.55
RAG_LOW_CONFIDENCE_RETRY_TOP_K = 10
