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

## Deploy to Render

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
