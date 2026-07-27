#!/usr/bin/env python3
"""Scan, extract, and query workspace-local reference files."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from _common.indexing import (
    FORMAT_CHOICES,
    VIEW_CHOICES,
    emit,
    markdown_list,
    read_json,
    read_text,
    relative_to_workspace,
    score_query,
    sha256_file,
    summarize_text,
    utc_now,
    workspace_path,
    write_json,
)
from _common.paths import configure_cli_logging

configure_cli_logging()

TEXT_SUFFIXES = {".md", ".tex", ".txt"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | {".pdf"}


def references_dir(workspace: Path) -> Path:
    return workspace / "references"


def extracted_dir(workspace: Path) -> Path:
    return references_dir(workspace) / ".extracted"


def meta_path(workspace: Path) -> Path:
    return extracted_dir(workspace) / "meta.json"


def safe_stem(path: Path) -> str:
    return path.name.replace("/", "_").replace("\\", "_")


def extracted_text_path(workspace: Path, ref: Path) -> Path:
    if ref.suffix.casefold() == ".pdf":
        return extracted_dir(workspace) / f"{safe_stem(ref)}.txt"
    return ref


def list_references(workspace: Path) -> list[Path]:
    root = references_dir(workspace)
    if not root.exists():
        return []
    refs: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".extracted" in path.relative_to(root).parts:
            continue
        if path.suffix.casefold() in SUPPORTED_SUFFIXES:
            refs.append(path)
    return sorted(refs)


def file_record(workspace: Path, ref: Path, meta: dict[str, Any]) -> dict[str, Any]:
    stat = ref.stat()
    rel = relative_to_workspace(ref, workspace)
    item_meta = meta.get(rel, {})
    target = extracted_text_path(workspace, ref)
    extracted = target.exists()
    stale = False
    if extracted and item_meta:
        stale = (
            item_meta.get("size") != stat.st_size
            or item_meta.get("mtime_ns") != stat.st_mtime_ns
        )
    elif ref.suffix.casefold() == ".pdf":
        stale = True
    return {
        "path": rel,
        "suffix": ref.suffix.casefold(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "extracted": extracted,
        "stale": stale,
        "text_path": relative_to_workspace(target, workspace) if target.exists() else None,
        "last_error": item_meta.get("error"),
        "updated_at_utc": item_meta.get("updated_at_utc"),
    }


def build_index(workspace: Path) -> dict[str, Any]:
    meta = read_json(meta_path(workspace), {})
    refs = [file_record(workspace, ref, meta) for ref in list_references(workspace)]
    payload = {
        "workspace": str(workspace),
        "generated_at_utc": utc_now(),
        "references_dir": relative_to_workspace(references_dir(workspace), workspace),
        "count": len(refs),
        "references": refs,
    }
    write_indexes(workspace, payload)
    return payload


def write_indexes(workspace: Path, payload: dict[str, Any]) -> None:
    root = references_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "index.json", payload)
    rows = payload.get("references", [])
    fields = ["suffix", "size", "extracted", "stale", "text_path", "last_error"]
    (root / "index.md").write_text(markdown_list("Reference Index", rows, fields), encoding="utf-8")


def select_pdf_backend(backend: str) -> str:
    if backend != "auto":
        return backend
    if shutil.which("pdftotext") is not None:
        return "pdftotext"
    if shutil.which("mutool") is not None:
        return "mutool"
    raise RuntimeError("no PDF text backend is available on PATH: tried pdftotext, mutool")


def run_pdftotext(pdf: Path, target: Path, backend: str) -> str:
    selected = select_pdf_backend(backend)
    if selected == "mutool":
        executable = shutil.which("mutool")
        if executable is None:
            raise RuntimeError("mutool is not available on PATH")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [executable, "draw", "-q", "-F", "txt", "-o", str(target), str(pdf)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return selected

    if selected != "pdftotext":
        raise ValueError(f"Unsupported PDF backend: {backend}")
    executable = shutil.which("pdftotext")
    if executable is None:
        raise RuntimeError("pdftotext is not available on PATH")
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [executable, "-layout", str(pdf), str(target)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return selected


def extract(workspace: Path, *, backend: str, force: bool) -> dict[str, Any]:
    root = extracted_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    meta = read_json(meta_path(workspace), {})
    results: list[dict[str, Any]] = []
    for ref in list_references(workspace):
        rel = relative_to_workspace(ref, workspace)
        stat = ref.stat()
        digest = sha256_file(ref)
        existing = meta.get(rel, {})
        unchanged = (
            existing.get("size") == stat.st_size
            and existing.get("mtime_ns") == stat.st_mtime_ns
            and existing.get("sha256") == digest
        )
        target = extracted_text_path(workspace, ref)
        skipped = unchanged and target.exists() and not force
        error = None
        backend_used = backend if ref.suffix.casefold() == ".pdf" else "native-text"
        if not skipped:
            try:
                if ref.suffix.casefold() == ".pdf":
                    backend_used = run_pdftotext(ref, target, backend)
                else:
                    target = ref
            except Exception as exc:  # noqa: BLE001 - must record tool failure.
                error = str(exc)
        meta[rel] = {
            "source_path": rel,
            "text_path": relative_to_workspace(target, workspace) if target.exists() else None,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": digest,
            "backend": backend_used,
            "updated_at_utc": utc_now(),
            "error": error,
        }
        results.append({
            "path": rel,
            "text_path": meta[rel]["text_path"],
            "skipped": skipped,
            "ok": error is None,
            "error": error,
        })
    write_json(meta_path(workspace), meta)
    index = build_index(workspace)
    return {"ok": all(item["ok"] for item in results), "results": results, "index": index}


def resolve_ref(workspace: Path, ref_name: str) -> Path:
    root = references_dir(workspace)
    candidate = root / ref_name
    if candidate.exists():
        return candidate
    matches = [path for path in list_references(workspace) if path.name == ref_name or relative_to_workspace(path, workspace) == ref_name]
    if not matches:
        raise SystemExit(f"reference not found: {ref_name}")
    if len(matches) > 1:
        raise SystemExit(f"ambiguous reference {ref_name!r}: {[relative_to_workspace(p, workspace) for p in matches]}")
    return matches[0]


def text_for_ref(workspace: Path, ref: Path) -> str:
    target = extracted_text_path(workspace, ref)
    if not target.exists():
        raise SystemExit(f"reference text not available; run extract first: {relative_to_workspace(ref, workspace)}")
    return read_text(target)


def show(workspace: Path, *, ref_name: str, page: int | None, line_start: int | None, line_end: int | None, context_lines: int) -> dict[str, Any]:
    ref = resolve_ref(workspace, ref_name)
    text = text_for_ref(workspace, ref)
    if page is not None:
        pages = text.split("\f")
        if page < 1 or page > len(pages):
            raise SystemExit(f"page {page} out of range 1..{len(pages)}")
        snippet = pages[page - 1]
        location = {"page": page}
    else:
        lines = text.splitlines()
        start = max((line_start or 1) - 1 - context_lines, 0)
        end = min((line_end or line_start or min(len(lines), 40)) + context_lines, len(lines))
        snippet = "\n".join(lines[start:end])
        location = {"line_start": start + 1, "line_end": end}
    return {
        "reference": relative_to_workspace(ref, workspace),
        "location": location,
        "text": snippet,
    }


def search(workspace: Path, *, query: str, limit: int, view: str) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for ref in list_references(workspace):
        try:
            text = text_for_ref(workspace, ref)
        except SystemExit:
            continue
        score = score_query(query, text)
        if score <= 0:
            continue
        results.append({
            "path": relative_to_workspace(ref, workspace),
            "score": score,
            "summary": summarize_text(text, view=view),
        })
    results.sort(key=lambda item: (-item["score"], item["path"]))
    return {"query": query, "count": min(len(results), limit), "results": results[:limit]}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Reference extraction and lookup tools")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "extract", "show", "search"):
        p = sub.add_parser(name)
        p.add_argument("workspace")
        p.add_argument("--format", choices=FORMAT_CHOICES, default="json")
        p.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    sub.choices["extract"].add_argument(
        "--backend",
        default="auto",
        choices=["auto", "pdftotext", "mutool"],
        help="PDF text backend. auto prefers pdftotext and falls back to mutool.",
    )
    sub.choices["extract"].add_argument("--force", action="store_true")
    sub.choices["show"].add_argument("--ref", required=True)
    sub.choices["show"].add_argument("--page", type=int)
    sub.choices["show"].add_argument("--line-start", type=int)
    sub.choices["show"].add_argument("--line-end", type=int)
    sub.choices["show"].add_argument("--context-lines", type=int, default=0)
    sub.choices["search"].add_argument("--query", required=True)
    sub.choices["search"].add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    workspace = workspace_path(args.workspace)
    if args.command == "scan":
        payload = build_index(workspace)
    elif args.command == "extract":
        payload = extract(workspace, backend=args.backend, force=args.force)
    elif args.command == "show":
        payload = show(
            workspace,
            ref_name=args.ref,
            page=args.page,
            line_start=args.line_start,
            line_end=args.line_end,
            context_lines=args.context_lines,
        )
    elif args.command == "search":
        payload = search(workspace, query=args.query, limit=args.limit, view=args.view)
    else:
        raise AssertionError(args.command)
    emit(payload, fmt=args.format)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(json.dumps({"ok": False, "error": exc.stderr or str(exc)}), file=sys.stderr)
        raise SystemExit(1)
