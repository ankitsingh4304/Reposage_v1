from __future__ import annotations

import hashlib
import os
import re
import shutil
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


# Public GitHub repos only: [https://][www.]github.com/<owner>/<repo>[.git][/tree/...]
GITHUB_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:/(?:tree|blob)/\S*)?/?$"
)
CLONE_TIMEOUT_S = 300


def normalize_github_url(source: str) -> str | None:
    """Return a canonical clone URL for a public GitHub repo, or None if it isn't one."""
    m = GITHUB_URL.match(source.strip())
    if not m or m.group("repo") in {".", ".."}:
        return None
    return f"https://github.com/{m.group('owner')}/{m.group('repo')}.git"


def _is_remote(source: str) -> bool:
    return source.endswith(".git") or source.startswith(("http://", "https://", "git@"))


def _clone_dir(source: str) -> Path:
    # Owner + repo + hash, so github.com/a/utils and github.com/b/utils never collide.
    url = normalize_github_url(source) or source
    parts = url.rstrip("/").removesuffix(".git").split("/")
    readable = re.sub(r"[^A-Za-z0-9._-]", "_", "__".join(parts[-2:]))
    digest = hashlib.sha1(url.encode()).hexdigest()[:10]
    return REPOS_DIR / f"{readable}-{digest}"


def resolve_repo(source: str) -> Path:
    p = Path(source)
    if p.exists() and p.is_dir():
        return p
    if _is_remote(source):
        url = normalize_github_url(source) or source
        dest = _clone_dir(source)
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)  # always index the latest commit
        print(f"Cloning {url} -> {dest} ...")
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # never hang on a password prompt
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--", url, str(dest)],
                           check=True, env=env, timeout=CLONE_TIMEOUT_S,
                           capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(dest, ignore_errors=True)
            raise RuntimeError(
                "Could not clone the repository. Check the URL and that the repo is public."
            ) from e
        except subprocess.TimeoutExpired as e:
            shutil.rmtree(dest, ignore_errors=True)
            raise RuntimeError("Cloning took too long. Try a smaller repository.") from e
        return dest
    raise FileNotFoundError(f"Not a directory or git URL: {source!r}")


def cleanup_clone(source: str) -> None:
    """Delete a clone made by resolve_repo. Local folders are never touched."""
    if _is_remote(source) and not Path(source).exists():
        shutil.rmtree(_clone_dir(source), ignore_errors=True)


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
