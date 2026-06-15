FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY code/ ./code/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY support_tickets/ ./support_tickets/

# CPU-only PyTorch keeps the image smaller on a VPS.
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e .

# Bake the Chroma index and download the embedding model at build time.
RUN python scripts/build_rag_index.py

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "code/app.py"]
