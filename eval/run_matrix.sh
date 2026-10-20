#!/bin/sh
# Index psf/requests once per (embedder, chunker), then evaluate every retriever
# setup on both labeled sets. Results land in eval/results/<set>__<index>__<setup>.json.
# Usage: sh eval/run_matrix.sh            (from the repo root, deps installed)
# The tree-sitter index needs: pip install tree-sitter tree-sitter-language-pack
set -e

REPO=https://github.com/psf/requests.git

# index name | EMBED_MODEL | CHUNKER
INDEXES="minilm|sentence-transformers/all-MiniLM-L6-v2|recursive
minilm-ts|sentence-transformers/all-MiniLM-L6-v2|treesitter
bge-small|BAAI/bge-small-en-v1.5|recursive"

# setup name | RETRIEVER | RERANK
SETUPS="dense|dense|0
dense-rerank|dense|1
hybrid|hybrid|0
hybrid-rerank|hybrid|1"

echo "$INDEXES" | while IFS='|' read -r index model chunker; do
    # one Qdrant collection per index, since models may differ in vector size
    export EMBED_MODEL="$model" CHUNKER="$chunker" QDRANT_COLLECTION="eval_$index"
    python -m src.cli --user "eval-$index" ingest "$REPO"
    echo "$SETUPS" | while IFS='|' read -r setup retriever rerank; do
        for set in requests requests_vague; do
            RETRIEVER="$retriever" RERANK="$rerank" python -m src.cli --user "eval-$index" \
                eval "eval/datasets/$set.json" --label "${set}__${index}__${setup}"
        done
    done
done
