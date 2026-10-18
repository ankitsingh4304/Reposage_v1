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
`eval/results/`.

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
