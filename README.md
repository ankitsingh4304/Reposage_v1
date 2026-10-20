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

- Embeddings: `bge-small-en-v1.5` via FastEmbed (ONNX, no PyTorch, fits in 512 MB)
- Vector store: Qdrant (Qdrant Cloud when deployed, local mode in dev)
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
python scripts/download_models.py   # optional: fetch the embedding model now

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
embedding model (`bge-small-en-v1.5` by default) baked in. `docker-compose.yml`
adds a local MongoDB.

```bash
cp .env.example .env        # set SECRET_KEY and one LLM key (e.g. GROQ_API_KEY)
docker compose up --build   # http://localhost:8000
```

With `QDRANT_URL` empty, vectors are kept by local Qdrant in the `reposage-data`
volume (`/app/data`).
Without an LLM key, sign-up, login and indexing still work; only asking fails.

## Deploy free on Render

Five free services work together:

| Piece | Service | Holds |
|---|---|---|
| Backend (FastAPI) | Render web service, free plan | nothing permanent |
| Frontend (React) | Render static site, free | the built UI |
| Vectors | Qdrant Cloud free cluster | code chunks + embeddings |
| Users, chat history, index info | MongoDB Atlas free M0 | accounts and data |
| Answers | Groq API | — |

Render's free server wipes its disk on every restart, so everything that must
survive lives in Qdrant Cloud and MongoDB Atlas.

1. **MongoDB Atlas** (https://cloud.mongodb.com): create a free M0 cluster, add a
   database user, and under **Network Access** allow `0.0.0.0/0` (Render's address
   changes). Copy the `mongodb+srv://...` connection string.
2. **Qdrant Cloud** (https://cloud.qdrant.io): create a free cluster. Copy its
   **Cluster URL** (ends in `:6333`) and create an **API key**.
3. **Groq** (https://console.groq.com/keys): create an API key.
4. Push this repo to GitHub.
5. **Render**: **New > Blueprint**, pick the repo. Render reads `render.yaml` and
   creates two services, `reposage-api` and `reposage-ui`. Fill in when asked:
   - `MONGO_URI`, `QDRANT_URL`, `QDRANT_API_KEY`, `GROQ_API_KEY`
   - `FRONTEND_URL` = `https://reposage-ui.onrender.com`
   - `VITE_API_URL` = `https://reposage-api.onrender.com`

   `SECRET_KEY` is generated for you.
6. When both deploys finish, check the real URLs on each service's page. If Render
   added a suffix (because the name was taken), fix `FRONTEND_URL` on the API and
   `VITE_API_URL` on the UI, then redeploy the UI (Vite bakes the URL in at build
   time).
7. Open the UI URL, sign up, and index a repo.

Free-plan limits:

- The API sleeps after 15 minutes with no traffic; the next request waits about a
  minute while it wakes.
- 0.1 CPU makes indexing slow, so repos over `MAX_INGEST_CHUNKS` (3000) are refused
  and only one repo is indexed at a time.
- A free Qdrant cluster is suspended after a week unused and deleted after four.

Health check: `GET /api/health`.

> Hugging Face Spaces is not a good fit: Spaces only allow outgoing connections on
> ports 80, 443 and 8080, and MongoDB Atlas uses 27017, so login would fail.

CLI:

```bash
python -m src.cli ingest https://github.com/pallets/click.git
python -m src.cli ask "Where are command-line options parsed?"
python -m src.cli ask "Where is the retry logic?" --agentic
python -m src.cli chat
```

Use `--user <name>` (before the command) to keep separate indexes side by side;
the default is `cli`.

## Evaluation

Retrieval is measured against hand-labeled questions about
[psf/requests](https://github.com/psf/requests) (80 indexed files), with
ground-truth files verified by grepping the source:

- `requests.json`: 25 precise questions, a mix of semantic ones and
  exact-identifier ones.
- `requests_vague.json`: 10 colloquial questions ("where's the cert stuff")
  with the same ground truth.

Metrics are at file level over the top 10 retrieved chunks:

- **Hit@k**: the share of questions where a correct file appears in the top k.
- **MRR**: the mean of 1 / rank of the first correct file.
- **Recall@10**: the share of correct files found in the top 10.

Reproduce all runs with `sh eval/run_matrix.sh`; results are written to
`eval/results/`. The tables below were measured with the earlier stack
(sentence-transformers + Chroma, including BGE-M3); the script now runs MiniLM and
bge-small through FastEmbed + Qdrant, so new numbers will differ somewhat.

**Precise questions (25)**

| Embedder | Chunker | Retriever | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@10 |
|---|---|---|---|---|---|---|---|
| MiniLM-L6 | recursive | dense | 0.52 | 0.88 | 1.00 | 0.706 | 1.00 |
| MiniLM-L6 | recursive | dense + rerank | 0.40 | 0.96 | 0.96 | 0.660 | 1.00 |
| MiniLM-L6 | recursive | hybrid | 0.60 | 0.92 | 1.00 | 0.773 | 1.00 |
| MiniLM-L6 | recursive | hybrid + rerank | 0.36 | 0.88 | 1.00 | 0.615 | 1.00 |
| MiniLM-L6 | tree-sitter | dense | 0.60 | 0.84 | 0.96 | 0.728 | 0.96 |
| MiniLM-L6 | tree-sitter | dense + rerank | 0.44 | 0.88 | 0.96 | 0.647 | 0.96 |
| MiniLM-L6 | tree-sitter | hybrid | 0.56 | 0.88 | 0.96 | 0.727 | 1.00 |
| MiniLM-L6 | tree-sitter | hybrid + rerank | 0.44 | 0.84 | 1.00 | 0.658 | 1.00 |
| BGE-M3 | recursive | dense | 0.48 | 0.96 | 1.00 | 0.701 | 1.00 |
| BGE-M3 | recursive | dense + rerank | 0.40 | 0.96 | 1.00 | 0.650 | 1.00 |
| **BGE-M3** | **recursive** | **hybrid** | **0.64** | **1.00** | **1.00** | **0.800** | **1.00** |
| BGE-M3 | recursive | hybrid + rerank | 0.36 | 0.92 | 1.00 | 0.618 | 1.00 |

**Vague questions (10)**

| Embedder | Chunker | Retriever | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@10 |
|---|---|---|---|---|---|---|---|
| MiniLM-L6 | recursive | dense | 0.30 | 0.90 | 1.00 | 0.542 | 1.00 |
| MiniLM-L6 | recursive | dense + rerank | 0.30 | 0.80 | 1.00 | 0.578 | 1.00 |
| **MiniLM-L6** | **recursive** | **hybrid** | **0.50** | 0.70 | 0.80 | **0.642** | 0.90 |
| MiniLM-L6 | recursive | hybrid + rerank | 0.20 | 0.70 | 0.90 | 0.478 | 0.90 |
| MiniLM-L6 | tree-sitter | dense | 0.40 | 0.50 | 1.00 | 0.548 | 1.00 |
| MiniLM-L6 | tree-sitter | dense + rerank | 0.30 | 0.60 | 1.00 | 0.545 | 1.00 |
| MiniLM-L6 | tree-sitter | hybrid | 0.30 | 0.60 | 0.80 | 0.493 | 0.90 |
| MiniLM-L6 | tree-sitter | hybrid + rerank | 0.30 | 0.60 | 0.90 | 0.525 | 0.90 |
| BGE-M3 | recursive | dense | 0.40 | 0.80 | 1.00 | 0.623 | 1.00 |
| BGE-M3 | recursive | dense + rerank | 0.40 | 0.80 | 0.90 | 0.587 | 0.90 |
| BGE-M3 | recursive | hybrid | 0.30 | 0.60 | 0.80 | 0.483 | 0.80 |
| BGE-M3 | recursive | hybrid + rerank | 0.20 | 0.60 | 0.70 | 0.408 | 0.70 |

What the numbers say:

- **Hybrid search is the biggest win on precise questions.** Adding BM25 to dense
  search (fused with RRF) raises MRR from 0.706 to 0.773 with MiniLM, and from
  0.701 to 0.800 with BGE-M3. Hit@1 goes from 48% to 64% with BGE-M3. Exact
  identifiers in the questions, like `HTTPDigestAuth` or `get_environ_proxies`,
  are what keyword search is good at.
- **A bigger embedder alone doesn't help much here.** Dense BGE-M3 (568M
  parameters) scores about the same as dense MiniLM (22M parameters), at
  0.701 vs 0.706 MRR. It pays off only in combination with hybrid search. The
  hosted build uses MiniLM because it fits in a small container.
- **The off-the-shelf reranker hurts.** `ms-marco-MiniLM-L-6-v2` is trained on
  web search passages, not code, and lowered MRR in every setup. That's why
  `RERANK` is off by default.
- **Vague questions are where retrieval breaks down.** BM25 has no exact words
  to match on colloquial queries: with BGE-M3, hybrid drops MRR from 0.623 to
  0.483. This is the case the agent mode targets, since it grades the retrieved
  code and rewrites the query. Agent mode needs an LLM key to evaluate:
  `python -m src.cli --user eval-minilm eval eval/datasets/requests_vague.json --agentic --label vague_agentic`.
- **Tree-sitter chunking is mixed.** Splitting along functions and classes
  improves dense Hit@1 from 52% to 60%, but costs a little recall and doesn't
  stack with hybrid search.

These sets are small: one question is 4 points on the precise set and 10 points
on the vague set. Read differences under about 0.04 MRR as noise.

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
