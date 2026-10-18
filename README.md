---
title: RepoSage
colorFrom: green
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---

# RepoSage

Ask questions about any GitHub repository in plain English and get answers grounded
in the actual code, with file and line references.

It clones a repo, splits the code into chunks, embeds them, and stores them in a
vector database. When you ask a question it retrieves the most relevant chunks
(dense + BM25 keyword search, with an optional cross-encoder reranker) and an LLM
answers using only that code. An optional agent mode grades the retrieved code and
rewrites the query to retry when the first attempt is weak.

## Stack

- Embeddings: BGE-M3 (local) via `sentence-transformers`, or a smaller MiniLM model
- Vector store: Chroma
- Retrieval: dense + BM25 hybrid (RRF), cross-encoder reranker
- Chunking: language-aware splitter, optional tree-sitter
- LLM: any OpenAI-compatible provider (Gemini / Groq / OpenRouter) or Claude
- Agent: LangGraph
- Backend: FastAPI
- Frontend: React (Vite)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

copy .env.example .env      # add one provider's API key

cd frontend
npm install
cd ..
```

## Usage

Run the API and the React app in two terminals:

```bash
# terminal 1 — backend
uvicorn app.api:app --reload

# terminal 2 — frontend (dev server, proxies /api to the backend)
cd frontend
npm run dev
```

Then open http://localhost:5173, paste a GitHub URL to index it, and start asking.

For a single-server setup, build the frontend once and let FastAPI serve it:

```bash
cd frontend && npm run build && cd ..
uvicorn app.api:app          # serves the UI + API on http://localhost:8000
```

## Docker

The image builds the React UI and serves it from FastAPI on one port, with the
embedding model (`all-MiniLM-L6-v2` by default) baked in. `docker-compose.yml`
adds a local MongoDB.

```bash
cp .env.example .env        # set SECRET_KEY and one LLM key (e.g. GROQ_API_KEY)
docker compose up --build   # http://localhost:8000
```

Cloned repos and Chroma vectors persist in the `reposage-data` volume (`/app/data`).
Without an LLM key, sign-up, login and indexing still work; only asking fails.

## Deploy free on Hugging Face Spaces

The free "CPU basic" Space (2 vCPU, 16 GB RAM) runs the Docker image as-is. The
YAML block at the top of this README is the Space config. The Space disk isn't
persistent, so indexed repos are lost when the Space restarts or sleeps (after
48 hours with no visitors), and users simply re-index. Accounts and chat history
are kept in MongoDB Atlas.

1. MongoDB Atlas: create a free M0 cluster and a database user, allow network
   access from `0.0.0.0/0`, and copy the `mongodb+srv://...` string.
2. Hugging Face: **New Space**, SDK **Docker** (blank template), hardware
   **CPU basic (free)**, visibility Public.
3. In the Space, go to **Settings > Variables and secrets** and add the secrets
   `MONGO_URI`, `SECRET_KEY` (any long random string) and `GROQ_API_KEY`.
4. Push this repo to the Space. Either do it once by hand:

   ```bash
   git remote add space https://huggingface.co/spaces/<hf-user>/<space-name>
   git push --force space main   # password = HF access token with write permission
   ```

   or let `.github/workflows/sync-hf-space.yml` push on every commit to `main`
   (add the repo secret `HF_TOKEN` and the variable `HF_SPACE=<hf-user>/<space-name>`
   in GitHub, then re-run the workflow from the Actions tab).
5. After the build finishes, open `https://<hf-user>-<space-name>.hf.space`.
   Use that direct URL, not the huggingface.co page, because the embedded
   iframe can block the login token in some browsers.

## Deploy to Render (paid)

`render.yaml` defines one Docker web service with a persistent disk. MongoDB is
hosted separately on MongoDB Atlas.

1. Create a free MongoDB Atlas M0 cluster, add a database user, allow network
   access from `0.0.0.0/0`, and copy the `mongodb+srv://...` connection string.
2. Get an LLM key (Groq is the default: https://console.groq.com/keys).
3. In Render: **New > Blueprint**, pick this repo. Fill in `MONGO_URI` and
   `GROQ_API_KEY` when prompted (`SECRET_KEY` is generated; leave `FRONTEND_URL`
   empty unless the UI is also hosted elsewhere).
4. Wait for the deploy, then open `https://<service>.onrender.com` and sign up.

The service needs the Standard plan (2 GB RAM) or larger and a disk, so it is not
on Render's free tier. Health check: `GET /api/health`.

CLI:

```bash
python -m src.cli ingest https://github.com/pallets/click.git
python -m src.cli ask "Where are command-line options parsed?"
python -m src.cli ask "Where is the retry logic?" --agentic
python -m src.cli chat
```

Evaluate retrieval against a labeled set:

```bash
python -m src.cli eval eval/datasets/requests.json --label run1
```

## Layout

```
config.py            settings (models, paths, retrieval params)
src/
  types.py           data types + interfaces
  ingest/            repo loader + chunkers
  embeddings/        embedding model
  store/             vector store
  retrieval/         dense, hybrid, reranker
  llm/               LLM clients
  agent/             LangGraph agent
  pipeline/rag.py    ties it together
  cli.py             command line
app/api.py           FastAPI backend
frontend/            React (Vite) chat UI
eval/                retrieval eval harness + datasets
Dockerfile           production image (UI + API)
docker-compose.yml   local stack with MongoDB
render.yaml          Render Blueprint
```
