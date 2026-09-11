#!/usr/bin/env python3
"""Invariant 2, enforced on the Claude side: a specialist may not dispatch.

`.codex/config.toml` sets `max_depth = 1`, so on Codex a specialist that tries
to spawn a subagent is refused by the runtime. On Claude Code the same rule was
prose in three places -- `CLAUDE.md` invariant 2, the same file's Read First
block, and a line in each of the thirteen agent bodies -- and nothing enforced
it. None of the thirteen registrations declares `tools:`, and a Claude Code
subagent with no `tools:` inherits the full set, `Agent` included. So every
specialist could dispatch, and the only consequence was that `dispatch_log.py`
recorded it happening: that hook's contract is *never block* and every one of
its exit paths is `sys.exit(0)`.

This is a separate file for that reason. Turning the recorder into a gate would
have broken the one guarantee that makes it safe to leave running, and P20 is
the round where a measurement disappeared because its recorder was doing two
jobs. One hook records, one hook refuses.

How nesting is detected
-----------------------
From `agent_id`. The runtime's own schema for the hook payload says it, in as
many words:

    Subagent identifier. Present only when the hook fires from within a
    subagent (e.g., a tool called by an AgentTool worker). Absent for the main
    thread, even in --agent sessions. Use this field (not agent_type) to
    distinguish subagent calls from main-thread calls.

The first version of this file read `transcript_path` instead, on the theory
that a subagent's transcript sits under `subagents/`. Subagent transcripts DO
live there -- but `transcript_path` in a hook payload is always the *session*
transcript, `<project>/<session-uuid>.jsonl`, for the main thread and a subagent
alike. The field the guard read could never hold the value it tested for, so the
hook allowed every dispatch and reported healthy. That is the `wall_clock_ms =
0.0` failure this repository keeps writing rules about, committed inside the
enforcement written to fix a different instance of it.

Its self-test could not have caught this: the "a subagent is identified" case
built its own input string, so the parser agreed with a fixture the same author
invented and with nothing the runtime sends. The checks below use payloads
shaped as the runtime documents them, and `--self-test --strict` refuses to pass
at all on a client whose schema no longer carries the field.

Failure policy
--------------
**Fail open, always.** A missing field, an unreadable payload, an unexpected
layout, any exception at all: allow the dispatch. This hook can only ever refuse
on a positive identification. The asymmetry is deliberate and it is the opposite
of `dispatch_log.py`'s: losing an enforcement is a rule going unenforced for one
call, which the gates still catch afterwards; a false refusal stops the
Orchestrator itself and breaks the run. Between those two, take the first.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Same tuple, same reason as dispatch_log.py: the tool is called `Agent` in this
# build and `Task` in most published examples, and matching only one is silent.
TOOLS = ("Agent", "Task")

SUBAGENT_DIR = "subagents"  # kept only for the corroborating check below

REASON = (
    "Invariant 2: a specialist may not dispatch another agent. This is a "
    "hub-and-spoke harness — return the blocker to the Orchestrator and let it "
    "route. (Enforced on Codex by `.codex/config.toml` max_depth = 1; this hook "
    "is the Claude-side counterpart. See CLAUDE.md 'Core Invariants'.)"
)


def is_subagent(payload: dict) -> bool:
    """True only on a positive identification. Every other answer is False."""
    agent_id = payload.get("agent_id")
    if isinstance(agent_id, str) and agent_id.strip():
        return True
    # Corroborating only, and it is expected never to fire: if a future runtime
    # ever hands the hook the SUBAGENT's own transcript rather than the
    # session's, this keeps working. It must not be the primary test -- that
    # mistake is what the docstring above is about.
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        try:
            if Path(transcript).parent.name == SUBAGENT_DIR:
                return True
        except (OSError, ValueError):
            pass
    return False


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")


def _schema_says_agent_id_marks_a_subagent() -> bool | None:
    """Ask the installed client whether `agent_id` still means what we read.

    None when no client can be found -- absence of evidence, reported as such.
    This is the check the first version of this file needed and did not have:
    its fixture was invented by the same author as the parser, so the two agreed
    with each other and with nothing the runtime sends.
    """
    import glob

    roots = sorted(glob.glob(str(Path.home() / ".local/share/claude/versions/*")))
    if not roots:
        return None
    try:
        blob = Path(roots[-1]).read_bytes()
    except OSError:
        return None
    return b"Present only when the hook fires from within a subagent" in blob


def self_test(strict: bool = False) -> int:
    """Both directions, because only one of them is dangerous.

    A guard that fails to refuse leaves a rule unenforced for one call. A guard
    that refuses wrongly stops the Orchestrator. The cases that assert *allow*
    are the ones that matter -- but the case that asserts *deny* is the one that
    was wrong for a whole day, so it is built from the payload shape the runtime
    documents rather than from a string invented here.
    """
    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    project = "/home/u/.claude/projects/-home-u-work"
    session = f"{project}/4c03ec86-58ee-4668-916e-dd7ed54e1a58"
    # As the runtime sends it: transcript_path is the SESSION transcript in both
    # cases, and only `agent_id` distinguishes them.
    main_thread = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "transcript_path": f"{session}.jsonl",
        "session_id": "4c03ec86-58ee-4668-916e-dd7ed54e1a58",
    }
    from_subagent = dict(main_thread, agent_id="a0c0162181716b579", agent_type="Explore")

    check("a dispatch from inside a subagent is identified", is_subagent(from_subagent))
    check("a main-thread dispatch is not", not is_subagent(main_thread))
    check(
        "an --agent session's main thread is not (agent_type without agent_id)",
        not is_subagent(dict(main_thread, agent_type="Explore")),
    )
    check(
        "the session transcript alone never identifies a subagent",
        not is_subagent({"transcript_path": f"{session}.jsonl"}),
    )
    check(
        "a subagent's own transcript still would, if one were ever passed",
        is_subagent({"transcript_path": f"{session}/subagents/agent-a56d351.jsonl"}),
    )
    # Everything below must ALLOW. Each is a way the payload can surprise this
    # hook, and every one must cost an enforcement, never a run.
    check("no fields at all allows", not is_subagent({}))
    check("a null agent_id allows", not is_subagent({"agent_id": None}))
    check("an empty agent_id allows", not is_subagent({"agent_id": "   "}))
    check("a non-string agent_id allows", not is_subagent({"agent_id": {"id": "x"}}))
    check("a null transcript_path allows", not is_subagent({"transcript_path": None}))
    check(
        "a non-string transcript_path allows",
        not is_subagent({"transcript_path": {"path": "x"}}),
    )
    check("a bare filename allows", not is_subagent({"transcript_path": "agent-a5.jsonl"}))
    check(
        "a directory merely CONTAINING the word allows",
        not is_subagent({"transcript_path": f"{project}/subagents-archive/x.jsonl"}),
    )
    check(
        "the word elsewhere in the path allows",
        not is_subagent({"transcript_path": "/w/subagents/notes/session.jsonl"}),
    )

    schema = _schema_says_agent_id_marks_a_subagent()
    if schema is False:
        failures.append(
            "the installed client no longer documents agent_id as the subagent "
            "marker -- re-read the payload schema before trusting this hook"
        )
    elif schema is None and strict:
        failures.append("no installed client found to check the payload schema against")

    for failure in failures:
        print(f"FAIL {failure}")
    total = 14 + (1 if schema is not None or strict else 0)
    passed = total - len(failures)
    note = "" if schema is not None else "  (client schema not checked)"
    print(f"nesting_guard self-test: {passed}/{total} checks passed{note}")
    return 1 if failures else 0


def main() -> None:
    if "--self-test" in sys.argv:
        sys.exit(self_test(strict="--strict" in sys.argv))
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)
    if payload.get("hook_event_name") != "PreToolUse":
        sys.exit(0)
    if payload.get("tool_name") not in TOOLS:
        sys.exit(0)
    try:
        nested = is_subagent(payload)
    except Exception:
        sys.exit(0)
    if nested:
        deny(REASON)
    sys.exit(0)


if __name__ == "__main__":
    main()
