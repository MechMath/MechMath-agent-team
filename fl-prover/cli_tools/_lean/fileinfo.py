#!/usr/bin/env python3
"""Inspect Lean files: imports, declarations, statements, and outline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from _lean import sourcetools as lst


def declaration_has_token(text: str, decl: lst.Declaration, token: str) -> bool:
    return any(decl.start <= offset < decl.end for _, offset in lst.find_tokens(text[decl.start:decl.end], [token]))


def enrich_declaration(text: str, decl: lst.Declaration) -> dict:
    data = decl.to_dict()
    decl_text = text[decl.start:decl.end]
    data["has_sorry"] = bool(lst.find_tokens(decl_text, ["sorry"]))
    data["has_admit"] = bool(lst.find_tokens(decl_text, ["admit"]))
    return data


def load_declarations(file_path: Path) -> tuple[str, list[lst.Declaration]]:
    text = lst.read_text(file_path)
    return text, lst.find_declarations(text)


def apply_filters(
    declarations: list[lst.Declaration],
    *,
    kinds: list[str] | None = None,
    name_contains: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> list[lst.Declaration]:
    result = declarations
    if kinds:
        allowed = set(kinds)
        result = [decl for decl in result if decl.kind in allowed]
    if name_contains:
        needle = name_contains.lower()
        result = [decl for decl in result if decl.name and needle in decl.name.lower()]
    if line_start is not None:
        result = [decl for decl in result if decl.end_line >= line_start]
    if line_end is not None:
        result = [decl for decl in result if decl.line <= line_end]
    return result


def command_declarations(args: argparse.Namespace) -> dict:
    text, declarations = load_declarations(args.file)
    declarations = apply_filters(
        declarations,
        kinds=args.kind,
        name_contains=args.name_contains,
        line_start=args.line_start,
        line_end=args.line_end,
    )
    return {
        "file": str(args.file),
        "declarations": [enrich_declaration(text, decl) for decl in declarations],
    }


def command_statements(args: argparse.Namespace) -> dict:
    text, declarations = load_declarations(args.file)
    declarations = [decl for decl in declarations if decl.kind in lst.STATEMENT_KINDS]
    declarations = apply_filters(
        declarations,
        kinds=args.kind,
        name_contains=args.name_contains,
        line_start=args.line_start,
        line_end=args.line_end,
    )
    return {
        "file": str(args.file),
        "statements": [
            decl.to_dict(include_statement=True, text=text)
            for decl in declarations
        ],
    }


def extract_statement(file_path: Path, declaration: str) -> dict:
    text, declarations = load_declarations(file_path)
    # Declarations are found lexically, so their names are unqualified. Accept a
    # namespace-qualified name too (`lean.py axioms` and the ledger use those).
    bare = declaration.rsplit(".", 1)[-1]
    for decl in declarations:
        if decl.name == declaration or decl.name == bare:
            data = decl.to_dict(include_statement=True, text=text)
            data["found"] = True
            return data
    return {"found": False, "name": declaration, "file": str(file_path)}


def command_statement(args: argparse.Namespace) -> dict:
    return extract_statement(args.file, args.declaration)


def command_imports(args: argparse.Namespace) -> dict:
    text = lst.read_text(args.file)
    return {"file": str(args.file), "imports": lst.find_imports(text)}


def command_outline(args: argparse.Namespace) -> dict:
    text, declarations = load_declarations(args.file)
    sorry_hits = lst.find_tokens(text, ["sorry", "admit"])
    by_token = Counter(token for token, _ in sorry_hits)
    return {
        "file": str(args.file),
        "imports": lst.find_imports(text),
        "declaration_count": len(declarations),
        "declarations": [enrich_declaration(text, decl) for decl in declarations],
        "sorry_count": by_token.get("sorry", 0),
        "admit_count": by_token.get("admit", 0),
    }


def add_common_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", action="append", choices=sorted(lst.DECL_KINDS))
    parser.add_argument("--name-contains")
    parser.add_argument("--line-start", type=int)
    parser.add_argument("--line-end", type=int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("declarations")
    p.add_argument("file", type=Path)
    add_common_filters(p)
    p.set_defaults(func=command_declarations)

    p = sub.add_parser("statements")
    p.add_argument("file", type=Path)
    add_common_filters(p)
    p.set_defaults(func=command_statements)

    p = sub.add_parser("statement")
    p.add_argument("file", type=Path)
    p.add_argument("declaration")
    p.set_defaults(func=command_statement)

    p = sub.add_parser("imports")
    p.add_argument("file", type=Path)
    p.set_defaults(func=command_imports)

    p = sub.add_parser("outline")
    p.add_argument("file", type=Path)
    p.set_defaults(func=command_outline)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.file = args.file.resolve()
    payload = args.func(args)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if payload.get("found") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
