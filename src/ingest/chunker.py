from __future__ import annotations

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from config import CONFIG
from src.types import Chunk, SourceFile

_LANGCHAIN_LANG = {
    "python": Language.PYTHON, "js": Language.JS, "ts": Language.TS,
    "go": Language.GO, "java": Language.JAVA, "ruby": Language.RUBY,
    "rust": Language.RUST, "c": Language.C, "cpp": Language.CPP,
    "csharp": Language.CSHARP, "php": Language.PHP, "swift": Language.SWIFT,
    "kotlin": Language.KOTLIN, "scala": Language.SCALA, "markdown": Language.MARKDOWN,
    "html": Language.HTML,
}

_SPLITTER_CACHE: dict[str, RecursiveCharacterTextSplitter] = {}


def _splitter_for(language: str) -> RecursiveCharacterTextSplitter:
    if language not in _SPLITTER_CACHE:
        lc_lang = _LANGCHAIN_LANG.get(language)
        if lc_lang is not None:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lc_lang,
                chunk_size=CONFIG.chunk_size,
                chunk_overlap=CONFIG.chunk_overlap,
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CONFIG.chunk_size,
                chunk_overlap=CONFIG.chunk_overlap,
            )
        _SPLITTER_CACHE[language] = splitter
    return _SPLITTER_CACHE[language]


def _line_span(text: str, piece: str, cursor: int) -> tuple[int, int, int]:
    # Locate the piece with a moving cursor so repeated snippets map to distinct lines.
    idx = text.find(piece, cursor)
    if idx == -1:
        idx = text.find(piece)
        if idx == -1:
            return 1, text.count("\n") + 1, cursor
    start_line = text.count("\n", 0, idx) + 1
    end_line = start_line + piece.count("\n")
    return start_line, end_line, idx + max(1, len(piece) - CONFIG.chunk_overlap)


def chunk_file(file: SourceFile) -> list[Chunk]:
    pieces = _splitter_for(file.language).split_text(file.text)
    chunks: list[Chunk] = []
    cursor = 0
    for i, piece in enumerate(pieces):
        if not piece.strip():
            continue
        start_line, end_line, cursor = _line_span(file.text, piece, cursor)
        chunks.append(
            Chunk(
                id=f"{file.path}::{i}",
                text=piece,
                path=file.path,
                language=file.language,
                start_line=start_line,
                end_line=end_line,
            )
        )
    return chunks


def chunk_files(files: list[SourceFile]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_file(f))
    return chunks
