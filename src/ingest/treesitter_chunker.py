"""AST-based chunking for Python via tree-sitter. Other languages fall back to
the recursive chunker."""
from __future__ import annotations

from config import CONFIG
from src.ingest.chunker import _splitter_for
from src.ingest.chunker import chunk_file as _recursive_chunk_file
from src.types import Chunk, SourceFile

_MAX_CHARS = CONFIG.chunk_size * 2
_PARSER_CACHE: dict = {}


def _parser(language: str):
    if language not in _PARSER_CACHE:
        from tree_sitter_language_pack import get_parser

        _PARSER_CACHE[language] = get_parser(language)
    return _PARSER_CACHE[language]


def _text(src: bytes, node) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _line_at(src: bytes, byte_offset: int) -> int:
    return src.count(b"\n", 0, byte_offset) + 1


def _name(src: bytes, node) -> str:
    n = node.child_by_field_name("name")
    return _text(src, n) if n is not None else ""


def _unwrap(node):
    if node.type == "decorated_definition":
        for c in node.children:
            if c.type in ("function_definition", "class_definition"):
                return c
    return node


def _emit_sized(src: bytes, node, symbol: str, language: str, out: list):
    text = _text(src, node)
    if len(text) <= _MAX_CHARS:
        out.append((text, node.start_point[0] + 1, node.end_point[0] + 1, symbol))
        return
    line = node.start_point[0] + 1
    for piece in _splitter_for(language).split_text(text):
        if piece.strip():
            n = piece.count("\n")
            out.append((piece, line, line + n, symbol))
            line += n


def _emit_class(src: bytes, outer, class_node, language: str, out: list):
    cls = _name(src, class_node)
    body = class_node.child_by_field_name("body")
    methods = [c for c in (body.children if body else [])
               if c.type in ("function_definition", "decorated_definition")]
    if not methods:
        _emit_sized(src, outer, cls, language, out)
        return
    header = src[outer.start_byte:methods[0].start_byte].decode("utf-8", errors="replace")
    if header.strip():
        out.append((header, outer.start_point[0] + 1,
                    _line_at(src, methods[0].start_byte) - 1, cls))
    for m in methods:
        inner = _unwrap(m)
        _emit_sized(src, m, f"{cls}.{_name(src, inner)}", language, out)


def chunk_file(file: SourceFile) -> list[Chunk]:
    if file.language != "python":
        return _recursive_chunk_file(file)
    try:
        src = file.text.encode("utf-8")
        root = _parser("python").parse(src).root_node
    except Exception:
        return _recursive_chunk_file(file)

    units: list = []
    module_buf: list = []

    def flush_module():
        if module_buf:
            first, last = module_buf[0], module_buf[-1]
            text = src[first.start_byte:last.end_byte].decode("utf-8", errors="replace")
            if text.strip():
                if len(text) <= _MAX_CHARS:
                    units.append((text, first.start_point[0] + 1, last.end_point[0] + 1, ""))
                else:
                    line = first.start_point[0] + 1
                    for piece in _splitter_for("python").split_text(text):
                        if piece.strip():
                            n = piece.count("\n")
                            units.append((piece, line, line + n, ""))
                            line += n
            module_buf.clear()

    for node in root.children:
        target = _unwrap(node)
        if target.type == "class_definition":
            flush_module()
            _emit_class(src, node, target, "python", units)
        elif target.type == "function_definition":
            flush_module()
            _emit_sized(src, node, _name(src, target), "python", units)
        else:
            module_buf.append(node)
    flush_module()

    chunks: list[Chunk] = []
    for i, (text, start_line, end_line, symbol) in enumerate(units):
        if not text.strip():
            continue
        chunks.append(
            Chunk(
                id=f"{file.path}::{i}",
                text=text,
                path=file.path,
                language=file.language,
                start_line=start_line,
                end_line=max(start_line, end_line),
                symbol=symbol,
            )
        )
    return chunks


def chunk_files(files: list[SourceFile]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_file(f))
    return chunks
