"""Shared helpers for workspace indexing CLI tools."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


VIEW_CHOICES = ("compact", "summary", "full")
FORMAT_CHOICES = ("json", "md", "plain")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()


def relative_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_text(path: Path, limit: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[:limit]
    return text


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.casefold())


def score_query(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    doc_counts = Counter(tokenize(text))
    if not doc_counts:
        return 0.0
    score = 0.0
    for token, query_count in Counter(query_tokens).items():
        freq = doc_counts.get(token, 0)
        if freq:
            score += query_count * (1.0 + math.log(1.0 + freq))
    return score


def first_nonempty_lines(text: str, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(stripped)
        if len(lines) >= limit:
            break
    return lines


def summarize_text(text: str, *, view: str = "compact", max_chars: int | None = None) -> str:
    if max_chars is None:
        max_chars = {"compact": 240, "summary": 800, "full": 4000}.get(view, 240)
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def emit(payload: Any, *, fmt: str = "json") -> None:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if fmt == "md":
        print(to_markdown(payload))
        return
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, ensure_ascii=False))


def to_markdown(payload: Any, *, level: int = 1) -> str:
    if isinstance(payload, dict):
        lines: list[str] = []
        for key, value in payload.items():
            title = str(key).replace("_", " ").title()
            if isinstance(value, (dict, list)):
                lines.append(f"{'#' * level} {title}")
                lines.append(to_markdown(value, level=level + 1))
            else:
                lines.append(f"- **{title}**: {value}")
        return "\n".join(lines)
    if isinstance(payload, list):
        lines = []
        for item in payload:
            if isinstance(item, dict):
                lines.append(to_markdown(item, level=level))
            else:
                lines.append(f"- {item}")
        return "\n\n".join(lines)
    return str(payload)


def markdown_list(title: str, rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("NONE")
        return "\n".join(lines) + "\n"
    for row in rows:
        label = row.get("path") or row.get("id") or row.get("source_path") or "entry"
        lines.append(f"## {label}")
        for field in fields:
            if field in row and row[field] not in (None, ""):
                lines.append(f"- **{field}**: {row[field]}")
        lines.append("")
    return "\n".join(lines)
