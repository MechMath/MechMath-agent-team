#!/usr/bin/env python3
"""Shared gate ergonomics: a way out, and a way to know what the gate wanted.

Every gate used to have exactly two outcomes, pass and fail, with no appeal.
When a check misfired the only legal move was to edit the artifact until the
check stopped firing — which is how a card spent three days failing on a literal
that no error message ever named (ADR 0023 P.1).

Two additions, both small:

* ``--waive REASON`` records the violation and lets the run continue. The
  waiver is printed, carried in the JSON result, and appended to the workspace
  so ``gate stop`` can summarise it. Waivers are meant to be visible and
  countable: a check that is waived constantly is a check to delete.
* A standard failure shape — what rule, what values are legal, what the smallest
  fix is. The same text is what ``--help`` prints, so a caller can read the
  requirement without first tripping it.

Deliberately not offered: a way to waive silently, and a global waive-all.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Iterable

WAIVER_LOG = "gate_waivers.jsonl"


def add_waiver_arg(parser: argparse.ArgumentParser) -> None:
    """Add ``--waive`` to a gate subcommand parser."""
    parser.add_argument(
        "--waive",
        metavar="REASON",
        default=None,
        help=(
            "record the violations and continue instead of blocking. "
            "The reason is required, is written into the run's waiver log, and "
            "is summarised by `gate stop`. Use when the check has misfired; "
            "a check waived repeatedly is evidence the check should be removed."
        ),
    )


def apply_waiver(
    errors: list[str],
    reason: str | None,
    *,
    gate: str,
    workspace: str | Path | None = None,
) -> tuple[list[str], list[str]]:
    """Split ``errors`` into (still-blocking, waived).

    With no reason, nothing is waived. With a reason, every error is waived and
    recorded. Returns both lists so callers can report what was let through.
    """
    if not reason or not errors:
        return errors, []
    waived = list(errors)
    _record(gate=gate, reason=reason, waived=waived, workspace=workspace)
    return [], waived


def _record(
    *, gate: str, reason: str, waived: Iterable[str], workspace: str | Path | None
) -> None:
    if workspace is None:
        return
    entry = {
        "gate": gate,
        "reason": reason,
        "waived": list(waived),
        "at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        path = Path(workspace) / WAIVER_LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # A waiver that cannot be logged still applies; losing the audit trail
        # must not turn into a second, more confusing failure.
        pass


def read_waivers(workspace: str | Path) -> list[dict[str, Any]]:
    """Return every waiver recorded in this workspace, oldest first."""
    path = Path(workspace) / WAIVER_LOG
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def requirement_text(*, checks: str, legal: str, fix: str) -> str:
    """The three sections every gate states, in --help and on failure alike.

    ``checks``  what this gate looks at.
    ``legal``   the legal values, enumerated. Enumerating legal values marks a
                boundary; it does not bias what gets written inside it.
    ``fix``     the smallest change that clears a failure.

    No worked example belongs here. A filled-in sample pulls what agents write
    toward the sample, which is the failure mode this whole ADR is about; an
    enumeration of legal values does not.
    """
    return (
        f"Checks:\n{_indent(checks)}\n\n"
        f"Legal values:\n{_indent(legal)}\n\n"
        f"If it fails:\n{_indent(fix)}"
    )


def _indent(block: str) -> str:
    return "\n".join("  " + line if line.strip() else line
                     for line in block.strip("\n").splitlines())


def print_waived(waived: list[str], reason: str) -> None:
    if not waived:
        return
    print(f"WAIVED ({len(waived)}): {reason}")
    for item in waived:
        print(f"  - {item}")
