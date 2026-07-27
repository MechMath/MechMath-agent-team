#!/usr/bin/env python3
"""Scan Lean files for real sorry/admit tokens outside comments and strings."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from _lean import sourcetools as lst


def scan_file(
    file_path: Path,
    *,
    tokens: list[str],
    include_comments: bool = False,
    context_lines: int = 0,
    compact: bool = False,
) -> dict:
    text = lst.read_text(file_path)
    starts = lst.line_starts(text)
    declarations = lst.find_declarations(text)
    hits = lst.find_tokens(text, tokens, include_comments=include_comments)

    occurrences = []
    by_token: Counter[str] = Counter()
    for token, offset in hits:
        by_token[token] += 1
        line, column = lst.offset_to_line_col(starts, offset)
        owner = lst.owning_declaration(declarations, offset)
        item = {
            "token": token,
            "line": line,
            "column": column,
            "declaration": owner.name if owner else None,
            "declaration_kind": owner.kind if owner else None,
        }
        if context_lines > 0 and not compact:
            item["context"] = lst.context_for_line(text, line, context_lines)
        occurrences.append(item)

    result = {
        "file": str(file_path),
        "count": len(occurrences),
        "by_token": {token: by_token.get(token, 0) for token in tokens},
        "occurrences": occurrences,
    }
    if compact:
        result["occurrences"] = [
            {
                "token": item["token"],
                "line": item["line"],
                "column": item["column"],
                "declaration": item["declaration"],
            }
            for item in occurrences
        ]
    return result


def print_plain(result: dict) -> None:
    for item in result["occurrences"]:
        declaration = item.get("declaration") or "-"
        print(
            f"{result['file']}:{item['line']}:{item['column']}: "
            f"{declaration}: {item['token']}"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--token", action="append", choices=["sorry", "admit"], help="Token to scan; may be repeated")
    parser.add_argument("--include-comments", action="store_true", help="Also scan comments/docstrings")
    parser.add_argument("--context-lines", type=int, default=0, help="Context lines around each occurrence")
    parser.add_argument("--compact", action="store_true", help="Return compact JSON")
    parser.add_argument("--plain", action="store_true", help="Print file:line:column output")
    args = parser.parse_args(argv)

    file_path = args.file.resolve()
    tokens = args.token or ["sorry", "admit"]
    result = scan_file(
        file_path,
        tokens=tokens,
        include_comments=args.include_comments,
        context_lines=max(0, args.context_lines),
        compact=args.compact,
    )

    if args.plain:
        print_plain(result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
