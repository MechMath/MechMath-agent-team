#!/usr/bin/env python3
"""Local Lean file compile check using `lake env lean`.

JSON output: { okay, lean_messages, failed_declarations }.
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from _lean import scan as lean_sorry_scan

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)
DEFAULT_THREADS = 6

# Pattern: /path/file.lean:10:4: error: msg  OR  /path/file.lean:10:4: error(code): msg
DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>error|warning|info)(?:\([^)]*\))?:\s*(?P<msg>.+)",
    re.MULTILINE,
)


def find_project_root(file_path: Path) -> Path:
    """Walk up from file to find directory containing lean-toolchain."""
    current = file_path.parent if file_path.is_file() else file_path
    while current != current.parent:
        if (current / "lean-toolchain").exists():
            return current
        current = current.parent
    return file_path.parent if file_path.is_file() else file_path


def parse_diagnostics(output: str) -> list[dict]:
    """Parse Lean compiler output into structured diagnostics.

    Each diagnostic may span multiple lines (e.g. omega goal state, unsolved goals).
    We capture everything between consecutive header lines as the full message body.
    """
    messages = []
    matches = list(DIAG_RE.finditer(output))
    for i, m in enumerate(matches):
        # Text between this header's end and the next header (or EOF) is the detail body.
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        extra = output[body_start:body_end].strip()

        first_line = m.group("msg").strip()
        full_data = (first_line + "\n" + extra) if extra else first_line

        messages.append({
            "file_name": m.group("file"),
            "line": int(m.group("line")),
            "column": int(m.group("col")),
            "severity": m.group("sev"),
            "data": full_data,
        })
    return messages


def extract_failed_declarations(messages: list[dict]) -> list[str]:
    """Extract declaration names from error messages when possible."""
    failed = set()
    # Pattern: "declaration 'Foo.bar' ..." or similar
    decl_re = re.compile(r"'([A-Za-z_][\w.]*)'")
    for msg in messages:
        if msg["severity"] == "error":
            match = decl_re.search(msg["data"])
            if match:
                failed.add(match.group(1))
    return sorted(failed)


def default_threads() -> int:
    """Return the internal default thread count for Lean."""
    available = os.cpu_count() or DEFAULT_THREADS
    return max(1, min(DEFAULT_THREADS, available))


def check(file_path: Path, timeout: int = 120, threads: int | None = None) -> dict:
    """Run `lake env lean` on a file and return structured diagnostics."""
    project_root = find_project_root(file_path)
    thread_count = default_threads() if threads is None else threads

    try:
        result = subprocess.run(
            ["lake", "env", "lean", "-j", str(thread_count), str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return {
            "okay": False,
            "lean_messages": [{"severity": "error", "data": f"Timed out after {timeout}s", "line": 0, "column": 0}],
            "failed_declarations": [],
        }
    except Exception as e:
        return {
            "okay": False,
            "lean_messages": [{"severity": "error", "data": str(e), "line": 0, "column": 0}],
            "failed_declarations": [],
        }

    combined = result.stdout + "\n" + result.stderr
    messages = parse_diagnostics(combined)
    has_error = any(m["severity"] == "error" for m in messages) or result.returncode != 0
    if result.returncode != 0 and not any(m["severity"] == "error" for m in messages):
        messages.append({
            "file_name": str(file_path),
            "line": 0,
            "column": 0,
            "severity": "error",
            "data": combined.strip() or f"Lean exited with status {result.returncode}",
        })
    failed = extract_failed_declarations(messages)

    return {
        "okay": not has_error,
        "lean_messages": messages,
        "failed_declarations": failed,
    }


def severity_counts(messages: list[dict]) -> dict[str, int]:
    return {
        "error": sum(1 for msg in messages if msg.get("severity") == "error"),
        "warning": sum(1 for msg in messages if msg.get("severity") == "warning"),
        "info": sum(1 for msg in messages if msg.get("severity") == "info"),
    }


def filter_messages(
    messages: list[dict],
    *,
    severities: list[str] | None,
    line_start: int | None,
    line_end: int | None,
) -> list[dict]:
    result = messages
    if severities:
        allowed = set(severities)
        result = [msg for msg in result if msg.get("severity") in allowed]
    if line_start is not None:
        result = [msg for msg in result if int(msg.get("line", 0)) >= line_start]
    if line_end is not None:
        result = [msg for msg in result if int(msg.get("line", 0)) <= line_end]
    return result


def shorten_message(message: str, limit: int = 500) -> str:
    if len(message) <= limit:
        return message
    return message[:limit].rstrip() + "... [truncated]"


def summary_message(msg: dict) -> dict:
    item = dict(msg)
    item["data"] = shorten_message(str(item.get("data", "")))
    return item


def compact_message(msg: dict) -> dict:
    return {
        "file_name": msg.get("file_name"),
        "line": msg.get("line"),
        "column": msg.get("column"),
        "severity": msg.get("severity"),
    }


def next_commands(file_path: Path, counts: dict[str, int]) -> list[str]:
    commands = []
    if counts.get("error", 0):
        commands.append(f"uv run python cli_tools/lean.py check {file_path} --summary --severity error")
    if counts.get("warning", 0):
        commands.append(f"uv run python cli_tools/lean.py check {file_path} --summary --severity warning")
    return commands


def shape_result(
    result: dict,
    file_path: Path,
    *,
    summary: bool,
    compact: bool,
    severities: list[str] | None,
    line_start: int | None,
    line_end: int | None,
    include_sorries: bool,
) -> dict:
    all_messages = result["lean_messages"]
    filtered = filter_messages(
        all_messages,
        severities=severities,
        line_start=line_start,
        line_end=line_end,
    )
    counts = severity_counts(all_messages)
    payload = {
        "okay": result["okay"],
        "counts": counts,
        "failed_declarations": result["failed_declarations"],
    }

    if compact:
        payload["lean_messages"] = [compact_message(msg) for msg in filtered]
        payload["next_commands"] = next_commands(file_path, counts)
    elif summary:
        payload["lean_messages"] = [summary_message(msg) for msg in filtered]
    else:
        payload = dict(result)

    if summary or compact:
        payload["filters"] = {
            "severity": severities or [],
            "line_start": line_start,
            "line_end": line_end,
        }

    if include_sorries:
        payload["sorry_summary"] = lean_sorry_scan.scan_file(
            file_path,
            tokens=["sorry", "admit"],
            compact=True,
        )
    return payload


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Local Lean compile check (lake env lean)")
    parser.add_argument("file", type=Path, help="Lean file path to check")
    parser.add_argument("--timeout-seconds", type=int, default=300, help="Max execution time in seconds (default: 300)")
    parser.add_argument(
        "-j",
        "--threads",
        type=int,
        default=default_threads(),
        help="Lean worker threads to use (default: auto)",
    )
    parser.add_argument("--summary", action="store_true", help="Return counts and shortened diagnostics")
    parser.add_argument("--compact", action="store_true", help="Return counts and diagnostic locations only")
    parser.add_argument("--severity", action="append", choices=["error", "warning", "info"], help="Filter diagnostics by severity; may be repeated")
    parser.add_argument("--line-start", type=int, help="Filter diagnostics to lines >= this value")
    parser.add_argument("--line-end", type=int, help="Filter diagnostics to lines <= this value")
    parser.add_argument("--include-sorries", action="store_true", help="Include compact sorry/admit scan output")
    args = parser.parse_args(argv)

    file_path = args.file.resolve()
    if not file_path.exists():
        print(json.dumps({"okay": False, "lean_messages": [{"severity": "error", "data": f"File not found: {file_path}", "line": 0, "column": 0}], "failed_declarations": []}), flush=True)
        sys.exit(1)
    if args.threads < 1:
        print(json.dumps({"okay": False, "lean_messages": [{"severity": "error", "data": f"--threads must be >= 1, got {args.threads}", "line": 0, "column": 0}], "failed_declarations": []}), flush=True)
        sys.exit(1)

    logger.info("lean_check called: file=%s timeout=%d", file_path, args.timeout_seconds)
    result = check(file_path, timeout=args.timeout_seconds, threads=args.threads)
    logger.info("lean_check result: okay=%s errors=%d", result["okay"], len([m for m in result["lean_messages"] if m["severity"] == "error"]))

    output = shape_result(
        result,
        file_path,
        summary=args.summary,
        compact=args.compact,
        severities=args.severity,
        line_start=args.line_start,
        line_end=args.line_end,
        include_sorries=args.include_sorries,
    )
    print(json.dumps(output, indent=2, ensure_ascii=False), flush=True)
    sys.exit(0 if result["okay"] else 1)


if __name__ == "__main__":
    main()
