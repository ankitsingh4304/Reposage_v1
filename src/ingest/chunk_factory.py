from __future__ import annotations

from config import CONFIG
from src.types import Chunk, SourceFile


def chunk_files(files: list[SourceFile]) -> list[Chunk]:
    if CONFIG.chunker == "treesitter":
        from src.ingest.treesitter_chunker import chunk_files as ts_chunk_files

        return ts_chunk_files(files)
    from src.ingest.chunker import chunk_files as recursive_chunk_files

    return recursive_chunk_files(files)
