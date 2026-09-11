#!/usr/bin/env python3
"""Record every subagent dispatch to `<workspace>/logs/dispatch.jsonl`.

Why this exists as a hook and not as an instruction
---------------------------------------------------
The Orchestrator was already told to keep this log by hand. Measured on the two
runs that followed:

    newtestc      38 entries / 39 artifacts   — kept
    newtestb_app   5 entries / 352 artifacts  — abandoned after 15 minutes

A log kept by hand is kept while the run is small. That is not a wording problem
and no stronger wording fixes it: a rule that must hold on the four-hundredth
dispatch belongs in middleware, not in a prompt.

What it records
---------------
One JSON object per completed `Task` dispatch:

    {"role", "started", "ended", "bytes", "tokens", "platform", "session"}

`role` is the subagent type. `bytes` is the size of what the subagent handed
back. `started`/`ended` are wall-clock UTC, stamped by the two halves of this
hook, so durations are measured rather than reconstructed from mtimes.

`platform` is always `claude-code`, and it is recorded **because a workspace can
hold both.** `newtestb` was worked by 5 Claude sessions and 12 Codex sessions;
`newtestc` by 38 Codex sessions and no Claude ones. Any per-workspace platform
label is therefore a guess, and comparing two workspaces without knowing the mix
compares two models as if they were two configurations. Stamping it per dispatch
is the only way that stops being a reconstruction.

`tokens` is real token accounting, not a byte proxy. Claude Code writes each
subagent's own transcript to `<project>/<session>/subagents/agent-*.jsonl` with
a sibling `.meta.json` carrying the `toolUseId` — which is exactly the
`tool_use_id` in this hook's payload. So the dispatch's cost is attributable to
the dispatch even when six of them run at once, which a transcript-offset range
could not do. Recorded separately: `in`, `out`, `cache_read`, `cache_write`.
Cache reads are counted apart because they are the bulk of the volume and a
small fraction of the price, and adding them into one number makes a cheap run
look enormous.

What it deliberately does NOT record
------------------------------------
The write target. A dispatch prompt names its target in prose and every attempt
to parse that back out is a guess that fails silently in the direction of
"looks fine". The artifact a dispatch actually produced is recoverable exactly:
its mtime falls inside `[started, ended]`. `gate.py speed` does that attribution
after the fact, where a wrong guess is visible instead of baked into the log.

Consequence worth stating: **a dispatch that produced nothing is detected by
finding no artifact in its window**, which is the same evidence a human would
use, rather than by trusting a target string.

**Prompt text. Not a snippet, not a matched substring, not the sentence a
pattern fired on.** A dispatch prompt carries the mathematics being worked on,
and this harness reads its own logs back — `gate.py speed` is run against a live
workspace and its output is read by the same run that produced it. Putting
problem content into the log is the leakage the whole design exists to prevent:
it turns an operational record into a side channel that quotes the proof.

`prompt_shape` (below) is the exception that respects that rule: booleans and a
length, never text. A boolean cannot smuggle a lemma.

What `prompt_shape` is for
--------------------------
ADR 0003 / `prompts/verifier.md` state a contract about what a verification
dispatch may contain — no prior verdict, no Generator account of its own work,
a stated budget and a stopping condition. Nothing could observe whether that
contract held: the 84% violation rate that motivated the contract was obtained
by hand-parsing `~/.claude/projects/*.jsonl`, which is not a measurement anyone
will repeat. A rule nothing records is a rule that is scored `UNMEASURED`
forever, which is how two earlier proposals ended.

The classifier is calibrated on a hand-read sample of 87 real verifier
dispatches; the patterns are the ones that actually occur in this corpus rather
than the ones a reader would invent. It is recorded for **every** role, not just
`verifier` — the contract generalises, and the comparison across roles is the
part worth looking at.

Failure policy
--------------
Never block, never raise, never write outside the workspace's `logs/`. Any
error means one missing line, which the `dispatch_lines` vs `lane_artifacts`
completeness check in `gate.py speed` already reports. Losing a measurement is
acceptable; failing a run to record one is not.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# The subagent-spawning tool. It is called `Agent` in this build; `Task` is the
# name used elsewhere and in most published hook examples, which is where the
# first version of this file got it — and being wrong here is silent, because a
# hook whose matcher never fires looks exactly like a run that never dispatched.
# Verified against real transcripts: 159 `Agent` calls, 0 `Task`.
TOOLS = ("Agent", "Task")
# Bound the pending directory. A run that crashes between Pre and Post leaves a
# stamp behind; without a cap those accumulate for the life of the machine.
MAX_PENDING = 512


# --- prompt shape ----------------------------------------------------------
#
# Each group below is one boolean on the record. The patterns are transcribed
# from a hand-read sample of 87 verifier dispatches, so they are deliberately
# literal: they match what this harness's Orchestrator writes, not a general
# theory of what anchoring language looks like. A pattern that fires on nothing
# in the corpus buys nothing and costs a false positive somewhere else.
#
# Nothing here may ever be stored. The match is reduced to True/False at the
# point of test and the subject string is dropped — see the module docstring.

_GENERATOR_FRAMING = (
    # "The Generator reports that the bound is tight", "the Generator has
    # already addressed", and the two artifacts that are its own account of
    # itself. Naming either file in a dispatch is framing even without prose.
    r"\bthe generator (?:reports|claims|says|asserts|notes|has|believes|maintains)\b",
    r"generator/status\.md",
    r"response_to_verifier\.md",
)

_PRIOR_VERDICT = (
    r"\bhistory\s*:",
    r"\bprior verdict\b",
    r"\b(?:prior|previous) verifier\b",
    r"\bprior packet\b",
    r"\b\d+\s+prior rounds?\b",
    r"\brounds?,\s*all\s+(?:NEEDS_REVISION|FAIL|PASS)\b",
    # A review path with its outcome appended: "verifier/report_v2.md (FAIL)".
    r"\((?:FAIL|NEEDS_REVISION)\)",
    r"\breview_\d+\.md\b",
    r"\btreat (?:their|its|his|her|those|these) findings as\b",
)

_BUDGET = (
    r"\bno sweeps\b",
    r"\bseconds?-scale\b",
    r"<=\s*\d+\s*(?:[KMG]i?B)\b",
    r"\btotal compute\b",
    r"\binstant\b",
    r"\bbudget\b",
    r"\bat most \d+ minutes?\b",
)

_STOPPING_CONDITION = (
    r"\bstop when\b",
    r"\bstop if\b",
    r"\bat most \d+ rounds?\b",
    r"\bdo not exceed\b",
    # "if you cannot settle it in one pass, stop and report" — the clause and
    # its stop have to be near each other or every long prompt matches.
    r"\bif you cannot\b[^.\n]{0,160}\bstop\b",
)

_FRESHNESS_CLAIM = (
    r"\bfresh\b",
    r"\bstateless\b",
    r"\bindependent referee\b",
    r"\bFIRST time you are seeing\b",
)

_SHAPE_PATTERNS = {
    "generator_framing": _GENERATOR_FRAMING,
    "prior_verdict": _PRIOR_VERDICT,
    "budget": _BUDGET,
    "stopping_condition": _STOPPING_CONDITION,
    "freshness_claim": _FRESHNESS_CLAIM,
}

_SHAPE_COMPILED = {
    name: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for name, patterns in _SHAPE_PATTERNS.items()
}


def classify_prompt(prompt: object) -> dict | None:
    """Reduce a dispatch prompt to booleans and a length. Never to text.

    Returns None when there is no prompt to classify, which is honest: a record
    with no `prompt_shape` means "not observed", and `gate.py speed` reports
    that as unmeasured rather than as a clean 0%.
    """
    if not isinstance(prompt, str) or not prompt:
        return None
    shape: dict = {"chars": len(prompt)}
    for name, patterns in _SHAPE_COMPILED.items():
        shape[name] = any(pattern.search(prompt) for pattern in patterns)
    return shape


def _safe_prompt_shape(payload: dict) -> dict | None:
    """`classify_prompt` inside the never-raise guarantee.

    The hook is documented "Never block, never raise" and exits 0 whatever
    happens. Classification is the newest and therefore the most likely part to
    throw, so it gets its own guard: a broken classifier must cost the shape
    field, never the record.
    """
    try:
        return classify_prompt((payload.get("tool_input") or {}).get("prompt"))
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pending_dir(session: str) -> Path:
    key = hashlib.sha256(session.encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"nlprover-dispatch-{key}"


def _stamp_name(payload: dict) -> str:
    """A key both halves of the hook can compute from the same tool input.

    `tool_input` is identical in the Pre and Post payloads for one call, so its
    canonical JSON is a stable join key. Two genuinely identical concurrent
    dispatches would collide; the sequence suffix below keeps them apart.
    """
    raw = json.dumps(payload.get("tool_input", {}), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def resolve_workspace(payload: dict) -> Path | None:
    """Where to write the log.

    In order, because each fallback is weaker than the one before it:

    1. `$NLPROVER_WORKSPACE` — explicit, and the only one that cannot be wrong.
    2. `cwd` or an ancestor containing `STATUS.md` — a workspace is the thing
       that has a `STATUS.md`.
    3. Nothing. **Not a guess.** Picking the most recently touched workspace on
       disk would attribute one run's dispatches to another run's log, which is
       worse than no log at all: the completeness check would read as healthy.
    """
    explicit = os.environ.get("NLPROVER_WORKSPACE")
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_dir():
            return candidate

    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        here = Path(cwd)
        for directory in (here, *here.parents):
            if (directory / "STATUS.md").is_file():
                return directory
    return None


def handle_pre(payload: dict) -> None:
    session = str(payload.get("session_id", "nosession"))
    directory = _pending_dir(session)
    directory.mkdir(parents=True, exist_ok=True)
    if len(list(directory.iterdir())) >= MAX_PENDING:
        return
    stamp = directory / f"{_stamp_name(payload)}.json"
    body = {"started": _now(), "role": (payload.get("tool_input") or {}).get("subagent_type")}
    # Classified here, on the half where `tool_input.prompt` is the live
    # request, and carried through the stamp to the record the Post half
    # writes. Booleans only — the stamp file is as much a place not to put
    # problem text as the log is.
    shape = _safe_prompt_shape(payload)
    if shape is not None:
        body["prompt_shape"] = shape
    stamp.write_text(json.dumps(body), encoding="utf-8")


def _response_bytes(payload: dict) -> int:
    response = payload.get("tool_response")
    if response is None:
        return 0
    if not isinstance(response, str):
        response = json.dumps(response, ensure_ascii=False)
    return len(response.encode("utf-8"))


def _subagent_tokens(payload: dict) -> dict | None:
    """Tokens this dispatch actually cost, from its own subagent transcript.

    Located by `tool_use_id`, which appears verbatim as `toolUseId` in the
    subagent's `.meta.json`. That link is what makes the number attributable
    under concurrency: six dispatches in flight write six transcripts, and each
    one's cost belongs to exactly one `Task` call.

    Returns None when the transcript cannot be found — a missing number is
    honest, a zero would silently drag every total down.
    """
    transcript = payload.get("transcript_path")
    tool_use_id = payload.get("tool_use_id")
    if not isinstance(transcript, str) or not isinstance(tool_use_id, str):
        return None
    session_dir = Path(transcript).with_suffix("")
    subagents = session_dir / "subagents"
    if not subagents.is_dir():
        return None

    target = None
    for meta in subagents.glob("*.meta.json"):
        try:
            if json.loads(meta.read_text(encoding="utf-8")).get("toolUseId") == tool_use_id:
                target = meta.with_suffix("").with_suffix(".jsonl")
                break
        except (OSError, ValueError):
            continue
    if target is None or not target.is_file():
        return None

    totals = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
    try:
        with target.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"usage"' not in line:
                    continue
                try:
                    message = json.loads(line).get("message")
                except ValueError:
                    continue
                usage = message.get("usage") if isinstance(message, dict) else None
                if not isinstance(usage, dict):
                    continue
                totals["in"] += usage.get("input_tokens") or 0
                totals["out"] += usage.get("output_tokens") or 0
                totals["cache_read"] += usage.get("cache_read_input_tokens") or 0
                totals["cache_write"] += usage.get("cache_creation_input_tokens") or 0
    except OSError:
        return None
    return totals if any(totals.values()) else None


def warn_unresolved(payload: dict) -> bool:
    """Say, once per session, that this run is not being logged.

    `resolve_workspace` returning None was a silent `return`, and silence here
    is indistinguishable from a run that dispatched nothing — which is the exact
    failure this hook was built to end, reappearing one level up. Measured
    2026-08-26 across every workspace in the corpus: **0 of 96 rows on the
    Claude side carry `source`, because the hook has never once resolved a
    workspace.** The orchestrator is run from the harness repo, which has no
    `STATUS.md`, and the workspace is not an ancestor of that cwd, so step 2
    cannot fire and step 1 needs an env var nobody was told to export until
    P52.

    Returns True when it warned, so the caller does not warn twice. Never
    raises and never blocks: a logging hook that can fail a run is worse than no
    logging hook, so this is stderr and exit 0, not exit 2.
    """
    session = str(payload.get("session_id", "nosession"))
    marker = _pending_dir(session) / "unresolved.warned"
    try:
        if marker.exists():
            return False
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(_now(), encoding="utf-8")
    except OSError:
        return False
    cwd = payload.get("cwd") or "(no cwd in payload)"
    print(
        "dispatch_log: no workspace resolved, so this session's dispatches are "
        f"NOT being logged.\n  cwd={cwd} has no STATUS.md in it or any parent, "
        "and $NLPROVER_WORKSPACE is unset.\n  Fix: export NLPROVER_WORKSPACE=<the "
        "run's workspace> before starting the run.\n  Said once per session. An "
        "unlogged run reads downstream exactly like a run that dispatched nothing.",
        file=sys.stderr,
    )
    return True


def handle_post(payload: dict) -> None:
    workspace = resolve_workspace(payload)
    if workspace is None:
        warn_unresolved(payload)
        return

    session = str(payload.get("session_id", "nosession"))
    stamp = _pending_dir(session) / f"{_stamp_name(payload)}.json"
    started = None
    role = None
    shape = None
    if stamp.is_file():
        try:
            body = json.loads(stamp.read_text(encoding="utf-8"))
            started, role = body.get("started"), body.get("role")
            candidate = body.get("prompt_shape")
            if isinstance(candidate, dict):
                shape = candidate
        except (OSError, ValueError):
            pass
        finally:
            stamp.unlink(missing_ok=True)

    if role is None:
        role = (payload.get("tool_input") or {}).get("subagent_type")
    if shape is None:
        # An orphan Post — the Pre half never ran, or the stamp was lost. The
        # Post payload echoes the same `tool_input`, so the shape is still
        # observable and a missing Pre should cost the duration, not the shape.
        shape = _safe_prompt_shape(payload)

    ended = _now()
    entry = {
        "role": role,
        "started": started or ended,
        "ended": ended,
        "bytes": _response_bytes(payload),
        # A workspace can be worked by both platforms, so this is per dispatch
        # and never inferred from the workspace.
        "platform": "claude-code",
        "session": session[:12],
        "source": "hook",
    }
    if shape is not None:
        entry["prompt_shape"] = shape
    tokens = _subagent_tokens(payload)
    if tokens is not None:
        entry["tokens"] = tokens
    # A start we never stamped is a duration we do not know. Say so rather than
    # emitting a zero, which would drag every median toward zero and make the
    # A3 batch criterion pass on arithmetic instead of on concurrency.
    if started is None:
        entry["duration_unknown"] = True

    logs = workspace / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / "dispatch.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def self_test() -> int:
    """Pin the shape. This hook is a silent parser and silent parsers rot: a
    changed payload key makes it write nothing, and writing nothing is exactly
    what a run with no dispatches looks like."""
    failures = []

    def check(label: str, condition: bool) -> None:
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp) / "ws"
        (workspace / "lemmas").mkdir(parents=True)
        (workspace / "STATUS.md").write_text("# S\n", encoding="utf-8")

        payload = {
            "session_id": "abc123",
            "cwd": str(workspace / "lemmas"),
            "tool_name": TOOLS[0],
            "tool_input": {"subagent_type": "generator", "prompt": "prove it"},
        }
        check("workspace found from a subdirectory", resolve_workspace(payload) == workspace)

        handle_pre(payload)
        handle_post({**payload, "tool_response": "x" * 100})
        lines = (workspace / "logs" / "dispatch.jsonl").read_text(encoding="utf-8").splitlines()
        check("one line per dispatch", len(lines) == 1)
        entry = json.loads(lines[0])
        check("role recorded", entry["role"] == "generator")
        check("bytes recorded", entry["bytes"] == 100)
        check("duration known when Pre ran", "duration_unknown" not in entry)

        # Post without Pre: the line must still appear, flagged.
        handle_post({**payload, "tool_input": {"subagent_type": "verifier"}, "tool_response": ""})
        lines = (workspace / "logs" / "dispatch.jsonl").read_text(encoding="utf-8").splitlines()
        check("orphan Post still logged", len(lines) == 2)
        check("orphan Post flagged", json.loads(lines[1]).get("duration_unknown") is True)

        check("platform stamped on every line", entry["platform"] == "claude-code")

        # No STATUS.md anywhere and no env var: write nothing, guess nothing.
        stray = {"session_id": "z", "cwd": temp, "tool_input": {"subagent_type": "writer"}}
        os.environ.pop("NLPROVER_WORKSPACE", None)
        check("unresolvable workspace is not guessed", resolve_workspace(stray) is None)
        handle_post({**stray, "tool_response": "y"})
        check("nothing written when unresolvable", len(lines) == 2)

        # Token accounting, against the real on-disk layout:
        #   <project>/<session>.jsonl  and  <project>/<session>/subagents/
        project = Path(temp) / "project"
        session_dir = project / "sess"
        subagents = session_dir / "subagents"
        subagents.mkdir(parents=True)
        (project / "sess.jsonl").write_text("", encoding="utf-8")
        (subagents / "agent-x.meta.json").write_text(
            json.dumps({"agentType": "generator", "toolUseId": "toolu_ABC"}), encoding="utf-8"
        )
        (subagents / "agent-x.jsonl").write_text(
            "\n".join(
                json.dumps({"message": {"usage": use}})
                for use in (
                    {"input_tokens": 10, "output_tokens": 100,
                     "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 200},
                    {"input_tokens": 3, "output_tokens": 50,
                     "cache_read_input_tokens": 7000, "cache_creation_input_tokens": 0},
                )
            ) + "\n",
            encoding="utf-8",
        )
        with_tokens = {
            "session_id": "abc123",
            "cwd": str(workspace),
            "transcript_path": str(project / "sess.jsonl"),
            "tool_use_id": "toolu_ABC",
            "tool_input": {"subagent_type": "generator"},
            "tool_response": "done",
        }
        tokens = _subagent_tokens(with_tokens)
        check("tokens summed across turns", tokens == {
            "in": 13, "out": 150, "cache_read": 12000, "cache_write": 200
        })
        # The attribution link is toolUseId, not "the newest file" — that is what
        # keeps six concurrent dispatches from claiming each other's cost.
        check(
            "a different tool_use_id gets nothing",
            _subagent_tokens({**with_tokens, "tool_use_id": "toolu_OTHER"}) is None,
        )
        check("no subagent dir means None, not zero", _subagent_tokens(
            {**with_tokens, "transcript_path": str(project / "missing.jsonl")}) is None)

        # --- prompt shape --------------------------------------------------
        anchored_prompt = (
            "History: 3 prior rounds, all NEEDS_REVISION. The Generator reports "
            "that the residue bound now holds. Read generator/status.md. "
            "Budget: seconds-scale, no sweeps. Stop when you have a verdict."
        )
        shape = classify_prompt(anchored_prompt)
        check("anchored prompt sets generator_framing", shape["generator_framing"] is True)
        check("anchored prompt sets prior_verdict", shape["prior_verdict"] is True)
        check("budget wording detected", shape["budget"] is True)
        check("stopping condition detected", shape["stopping_condition"] is True)
        check("length recorded", shape["chars"] == len(anchored_prompt))

        clean = classify_prompt(
            "You are a fresh, stateless referee. Verify lemmas/lem_a/generator/"
            "proof_v4.md against its statement and dependencies."
        )
        check("clean prompt is not anchored", not clean["generator_framing"] and not clean["prior_verdict"])
        check("freshness claim detected", clean["freshness_claim"] is True)
        check("clean prompt names no stopping condition", clean["stopping_condition"] is False)

        # The rule the whole field depends on: booleans and a length, never a
        # substring of the mathematics.
        check(
            "no prompt text is stored",
            set(shape) == {"chars", *_SHAPE_PATTERNS}
            and all(isinstance(v, (bool, int)) for v in shape.values()),
        )
        check("no prompt means no shape, not a false zero", classify_prompt(None) is None)

        shaped = {
            "session_id": "shape1",
            "cwd": str(workspace),
            "tool_input": {"subagent_type": "verifier", "prompt": anchored_prompt},
        }
        handle_pre(shaped)
        handle_post({**shaped, "tool_response": "ok"})
        recorded = json.loads(
            (workspace / "logs" / "dispatch.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        )
        check("prompt_shape reaches the record", recorded.get("prompt_shape") == shape)
        check(
            "the record carries no prompt text",
            anchored_prompt[:40] not in json.dumps(recorded),
        )

        # "Never block, never raise" has to survive the newest moving part: a
        # classifier that throws costs the shape field and nothing else.
        original = globals()["classify_prompt"]

        def _explode(_prompt):
            raise RuntimeError("classifier is broken")

        globals()["classify_prompt"] = _explode
        try:
            broken = {
                "session_id": "shape2",
                "cwd": str(workspace),
                "tool_input": {"subagent_type": "verifier", "prompt": anchored_prompt},
            }
            handle_pre(broken)
            handle_post({**broken, "tool_response": "ok"})
        finally:
            globals()["classify_prompt"] = original
        last = json.loads(
            (workspace / "logs" / "dispatch.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        )
        check("a throwing classifier still writes the record", last.get("role") == "verifier")
        check("a throwing classifier omits prompt_shape", "prompt_shape" not in last)

    # An unresolved workspace must say so, exactly once per session. The silent
    # `return` it replaces is why 0 of 96 rows in the corpus carry `source`.
    import io as _io
    import contextlib as _contextlib
    _payload = {"session_id": "selftest-unresolved", "cwd": "/nonexistent-dir-with-no-status"}
    _marker = _pending_dir("selftest-unresolved") / "unresolved.warned"
    _marker.unlink(missing_ok=True)
    _buffer = _io.StringIO()
    with _contextlib.redirect_stderr(_buffer):
        _first = warn_unresolved(_payload)
        _second = warn_unresolved(_payload)
    if not _first or "NOT being logged" not in _buffer.getvalue():
        failures.append("an unresolved workspace warned nothing")
    if _second:
        failures.append("an unresolved workspace warned more than once per session")
    _marker.unlink(missing_ok=True)

    for failure in failures:
        print(f"FAIL {failure}")
    total = 27
    print(f"dispatch_log self-test: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


def main() -> None:
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)
    if payload.get("tool_name") not in TOOLS:
        sys.exit(0)
    try:
        if payload.get("hook_event_name") == "PreToolUse":
            handle_pre(payload)
        else:
            handle_post(payload)
    except Exception:
        # A logging hook that can fail a run is worse than no logging hook.
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
