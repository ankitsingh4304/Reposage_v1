# syntax=docker/dockerfile:1

# ---- Stage 1: build the React frontend ------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Empty VITE_API_URL = same-origin API calls (FastAPI serves the UI).
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---- Stage 2: Python runtime ----------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    XDG_CACHE_HOME=/opt/cache \
    TOKENIZERS_PARALLELISM=false

# git is required at runtime to clone repositories for ingestion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so cold starts don't download it.
# Embeddings run on ONNX via fastembed (no torch), so the app fits in 512 MB.
ARG EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV EMBED_MODEL=${EMBED_MODEL} \
    FASTEMBED_CACHE_PATH=/opt/hf-cache/fastembed
# Memory-lean defaults for 512 MB / fractional-CPU hosts (peak ~380 MB while indexing).
# Raise EMBED_BATCH_SIZE / EMBED_THREADS on bigger machines for faster indexing.
ENV EMBED_BATCH_SIZE=8 \
    EMBED_THREADS=1 \
    MALLOC_ARENA_MAX=2
RUN python -c "import os; from fastembed import TextEmbedding; TextEmbedding(os.environ['EMBED_MODEL'])"
# tree-sitter-language-pack fetches grammars on first use; CHUNKER=treesitter needs python.
RUN python -c "import tree_sitter_language_pack as t; t.download(['python'])"

COPY config.py ./
COPY src/ ./src/
COPY app/ ./app/
COPY --from=frontend /frontend/dist ./frontend/dist
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# The entrypoint starts as root only to fix volume ownership, then drops to appuser.
# Hugging Face Spaces runs the container as uid 1000 directly, which is appuser.
# Cloned repos, Chroma vectors and per-user index metadata live in /app/data.
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data /opt/hf-cache /opt/cache

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# Single worker: pipelines (and their models) are cached in-process per user.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
