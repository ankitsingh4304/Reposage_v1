from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterator

from config import CONFIG, IGNORE_DIRS, IGNORE_EXTS, MAX_FILE_BYTES, REPOS_DIR
from src.types import SourceFile

EXT_LANGUAGE = {
    ".py": "python", ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".tsx": "ts", ".go": "go", ".java": "java", ".rb": "ruby",
    ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
    ".sh": "text", ".md": "markdown", ".rst": "text", ".html": "html", ".css": "text",
    ".sql": "text", ".yaml": "text", ".yml": "text", ".json": "text", ".toml": "text",
}


def _language_for(path: Path) -> str | None:
    name = path.name.lower()
    if any(name.endswith(ext) for ext in IGNORE_EXTS):
        return None
    return EXT_LANGUAGE.get(path.suffix.lower())


def _is_probably_binary(raw: bytes) -> bool:
    return b"\x00" in raw[:1024]


def resolve_repo(source: str) -> Path:
    p = Path(source)
    if p.exists() and p.is_dir():
        return p
    if source.endswith(".git") or source.startswith(("http://", "https://", "git@")):
        name = source.rstrip("/").split("/")[-1].removesuffix(".git")
        dest = REPOS_DIR / name
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            print(f"Cloning {source} -> {dest} ...")
            subprocess.run(["git", "clone", "--depth", "1", source, str(dest)], check=True)
        return dest
    raise FileNotFoundError(f"Not a directory or git URL: {source!r}")


def _iter_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def load_repo(source: str) -> list[SourceFile]:
    root = resolve_repo(source)
    files: list[SourceFile] = []
    for path in _iter_files(root):
        language = _language_for(path)
        if language is None:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = path.read_bytes()
            if _is_probably_binary(raw):
                continue
            text = raw.decode("utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        if not text.strip():
            continue
        files.append(SourceFile(path=path.relative_to(root).as_posix(),
                                language=language, text=text))
    return files
