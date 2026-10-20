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
    FASTEMBED_CACHE_PATH=/opt/models \
    TOKENIZERS_PARALLELISM=false

# git is required at runtime to clone repositories for ingestion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# No PyTorch: FastEmbed runs the embedding model on ONNX Runtime.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so cold starts don't download it.
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
ENV EMBED_MODEL=${EMBED_MODEL}
COPY config.py ./
COPY scripts/ ./scripts/
RUN python scripts/download_models.py

COPY src/ ./src/
COPY app/ ./app/
COPY --from=frontend /frontend/dist ./frontend/dist
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# The entrypoint starts as root only to fix volume ownership, then drops to appuser.
# Hugging Face Spaces runs the container as uid 1000 directly, which is appuser.
# Cloned repos (deleted after indexing) and, without QDRANT_URL, local Qdrant files
# live in /app/data.
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && mkdir -p /opt/hf-cache /opt/cache \
    && chown -R appuser:appuser /app/data /opt/hf-cache /opt/cache /opt/models

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# Single worker: pipelines (and their models) are cached in-process per user.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
