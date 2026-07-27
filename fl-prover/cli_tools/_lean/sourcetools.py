"""Lightweight Lean source inspection helpers.

These helpers are intentionally lexical. They do not replace Lean elaboration.
"""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DECL_KINDS = {
    "theorem",
    "lemma",
    "def",
    "abbrev",
    "instance",
    "class",
    "structure",
    "inductive",
    "axiom",
    "opaque",
}

STATEMENT_KINDS = {"theorem", "lemma", "axiom"}

DECL_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive|axiom|opaque)"
    r"(?:\s+(?P<name>[A-Za-z_][\w'.]*))?"
)

IMPORT_RE = re.compile(r"(?m)^[ \t]*import\s+(?P<module>[A-Za-z0-9_.]+)")
WORD_RE_TEMPLATE = r"(?<![A-Za-z0-9_'.])({})(?![A-Za-z0-9_'.])"


@dataclass(frozen=True)
class Declaration:
    kind: str
    name: str | None
    start: int
    end: int
    statement_start: int
    statement_end: int
    line: int
    column: int
    end_line: int
    statement_start_line: int
    statement_end_line: int
    parse_warnings: tuple[str, ...] = ()

    def to_dict(self, *, include_statement: bool = False, text: str = "") -> dict:
        result = {
            "kind": self.kind,
            "name": self.name,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "statement_range": {
                "start_line": self.statement_start_line,
                "end_line": self.statement_end_line,
            },
        }
        if self.parse_warnings:
            result["parse_warnings"] = list(self.parse_warnings)
        if include_statement:
            statement = text[self.statement_start:self.statement_end].strip()
            result.update({
                "statement": statement,
                "normalized_statement": normalize_statement(statement),
                "hash": sha256(normalize_statement(statement)),
            })
        return result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def offset_to_line_col(starts: list[int], offset: int) -> tuple[int, int]:
    idx = bisect_right(starts, offset) - 1
    return idx + 1, offset - starts[idx] + 1


def normalize_statement(text: str) -> str:
    return " ".join(text.split())


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "'", "."}


def looks_like_char_literal(text: str, i: int) -> int | None:
    if text[i] != "'":
        return None
    if i > 0 and is_ident_char(text[i - 1]):
        return None
    j = i + 1
    escaped = False
    while j < len(text) and j <= i + 8:
        ch = text[j]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "'":
            if j + 1 < len(text) and is_ident_char(text[j + 1]):
                return None
            return j + 1
        elif ch == "\n":
            return None
        j += 1
    return None


def code_mask(text: str, *, include_comments: bool = False) -> list[bool]:
    """Return True for characters considered code.

    Comments and strings are False unless include_comments is set, in which case
    comments are True but strings remain False.
    """
    mask = [True] * len(text)
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("--", i):
            j = text.find("\n", i)
            if j == -1:
                j = n
            if not include_comments:
                for k in range(i, j):
                    mask[k] = False
            i = j
            continue

        if text.startswith("/-", i):
            depth = 1
            j = i + 2
            while j < n and depth > 0:
                if text.startswith("/-", j):
                    depth += 1
                    j += 2
                elif text.startswith("-/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if not include_comments:
                for k in range(i, min(j, n)):
                    mask[k] = False
            i = j
            continue

        if text[i] == '"':
            j = i + 1
            escaped = False
            while j < n:
                ch = text[j]
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    j += 1
                    break
                j += 1
            for k in range(i, min(j, n)):
                mask[k] = False
            i = j
            continue

        char_end = looks_like_char_literal(text, i)
        if char_end is not None:
            for k in range(i, min(char_end, n)):
                mask[k] = False
            i = char_end
            continue

        i += 1
    return mask


def masked_text(text: str, mask: list[bool]) -> str:
    return "".join(ch if keep or ch == "\n" else " " for ch, keep in zip(text, mask))


def find_imports(text: str) -> list[dict]:
    mask = code_mask(text)
    clean = masked_text(text, mask)
    starts = line_starts(text)
    imports = []
    for match in IMPORT_RE.finditer(clean):
        line, _ = offset_to_line_col(starts, match.start())
        imports.append({"module": match.group("module"), "line": line})
    return imports


def find_declarations(text: str) -> list[Declaration]:
    mask = code_mask(text)
    clean = masked_text(text, mask)
    starts = line_starts(text)
    matches = list(DECL_RE.finditer(clean))
    declarations: list[Declaration] = []

    for index, match in enumerate(matches):
        kind = match.group("kind")
        name = match.group("name")
        start = match.start()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        end = next_start
        statement_end, warnings = find_statement_end(clean, match.end(), next_start)
        if statement_end <= start:
            statement_end = min(next_start, match.end())
            warnings.append("could not identify statement boundary")

        line, col = offset_to_line_col(starts, start)
        end_line, _ = offset_to_line_col(starts, max(start, end - 1))
        statement_start_line, _ = offset_to_line_col(starts, start)
        statement_end_line, _ = offset_to_line_col(starts, max(start, statement_end - 1))
        declarations.append(Declaration(
            kind=kind,
            name=name,
            start=start,
            end=end,
            statement_start=start,
            statement_end=statement_end,
            line=line,
            column=col,
            end_line=end_line,
            statement_start_line=statement_start_line,
            statement_end_line=statement_end_line,
            parse_warnings=tuple(warnings),
        ))
    return declarations


def find_statement_end(clean_text: str, search_start: int, limit: int) -> tuple[int, list[str]]:
    warnings: list[str] = []
    segment = clean_text[search_start:limit]
    candidates: list[int] = []
    for token in (":=", " where", "\nwhere", " by", "\nby"):
        pos = segment.find(token)
        if pos >= 0:
            candidates.append(search_start + pos)
    if candidates:
        return min(candidates), warnings
    warnings.append("statement boundary approximated by next declaration")
    return limit, warnings


def owning_declaration(declarations: list[Declaration], offset: int) -> Declaration | None:
    owner = None
    for decl in declarations:
        if decl.start <= offset < decl.end:
            owner = decl
        elif decl.start > offset:
            break
    return owner


def context_for_line(text: str, line: int, context_lines: int) -> str:
    lines = text.splitlines()
    start = max(1, line - context_lines)
    end = min(len(lines), line + context_lines)
    return "\n".join(lines[start - 1:end])


def find_tokens(
    text: str,
    tokens: Iterable[str],
    *,
    include_comments: bool = False,
) -> list[tuple[str, int]]:
    mask = code_mask(text, include_comments=include_comments)
    clean = masked_text(text, mask)
    escaped = [re.escape(token) for token in tokens]
    pattern = re.compile(WORD_RE_TEMPLATE.format("|".join(escaped)))
    return [(match.group(1), match.start()) for match in pattern.finditer(clean)]

