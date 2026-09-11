#!/usr/bin/env python3
"""dispatch_guard — the three dispatch knobs, enforced instead of requested.

WHY THIS FILE EXISTS, in the words of the person who had to say it by hand.

Between 2026-08-26 and 2026-09-06 this harness ran 174 hours, 63,592 model calls and
16.6 billion prefill tokens against 18.1 million output tokens — 878 prefilled tokens per
token produced. The three settings that caused it were all requested in prose, and all three
were ignored, so the human said them again, and again:

  granularity  "不要拆的这么细了，大块的都搞定"            2026-09-04 02:07
               "r可行可不可以不切，直接做掉，你这无限切下去了有点，总也做不完"   2026-09-04 05:35
               "你blueprint写完也不要一直拆的太细了"          2026-09-05 01:53
               "不要拆那么细，这堆可以让一个generator一次干完的"  2026-09-05 01:55  <- 2 minutes later
               ...7 times in all

  lifetime     dispatch briefs said "Continue; do not restart." Median subagent life was
               61 turns, the longest 1,011. 56 of 585 agents burned 54.4% of ALL prefill,
               because an N-turn agent re-prefills its whole transcript N times. There were
               1,143 resumes against 614 spawns.

  occupancy    "your slot is empty now" · "你多并行点推进" · "槽位增加到10"
               "解锁了你自己补充槽位，不要每次都是我催你"    ...12 times in all

This project's own rule is that a prompt is a request and a hook is enforcement. Saying a
thing twice in two minutes is the signature of an instruction with nothing behind it, so the
three knobs live here now. Nothing in this file is a style preference; each limit has a
number in `harnesses/fl-prover/cycles/2026-09-09/report.md` behind it.

Contract: read a Claude Code hook payload on stdin, print a JSON decision on stdout, exit 0.
A crash must never block a dispatch — see `main`.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

# --- the three knobs ----------------------------------------------------------------
# Overridable by environment so a wave can be widened deliberately and visibly, rather
# than by editing a prose ceiling that three documents disagree about.

# NOT overridable by environment, and that is the point. The first version read
# FLP_MAX_AGENT_TURNS from the environment, which let the party being constrained lift
# its own cap — `FLP_MAX_AGENT_TURNS=99999` — without touching a tracked file and without
# leaving a trace in the git record. That is the exact inversion of this project's rule
# that a prompt is a request and a hook is enforcement. Widening a wave is a decision;
# it belongs in a commit.
MAX_AGENT_TURNS = 50
MAX_DECOMP_DEPTH = 2
MAX_DECOMP_CHILDREN = 4

# Below this many recently-active subagents, every allowed dispatch carries a nudge.
MIN_LIVE_AGENTS = 4

# 50 turns: the arithmetic is in report §1. Same work, each agent's life capped at 50 turns
# and its context reset at the cap, costs 40.4% of the prefill actually spent — a saving of
# 8.4 billion tokens. At 30 it is 26.9%, at 120 it is 73.0%. 50 is the knee.
#
# depth 2 / children 4: flowverse pins exactly these in a Pydantic type
# (`max_depth: 2`, `max_children: 4`, `max_nodes: 24`) and its decomposition prompt bans
# over-splitting outright. It is the harness this round was asked to learn from.

# Phrases that turn a dispatch into an unbounded life. The first is quoted verbatim from
# the briefs this harness actually sent.
NO_RESTART = re.compile(
    r"continue[,;:\s]*(?:and\s+)?do\s+not\s+restart"
    r"|do\s+not\s+start\s+over"
    r"|pick\s+up\s+exactly\s+where"
    r"|继续[，,]?\s*不要重(?:新开始|启|来)"
    r"|不要重新开始",
    re.IGNORECASE,
)

# NOTE on `\b` and Chinese: CJK characters are word characters to `re`, so `\b拆` never
# matches inside 把这个拆分 — there is no boundary between two word characters. The first
# version of this file had `\b` in front of the Chinese alternatives and silently allowed
# every Chinese over-split instruction through. The word boundary applies to the ASCII
# alternatives only, which is why the alternation is split in two.
# These must match an INSTRUCTION TO DECOMPOSE, never a mention of the words. The first
# version denied "prove the inner step at depth 3 of the induction on n" and "the proof is
# split into 6 parts across the files; read them all" — a mathematical use of `depth` and a
# description of existing structure. Over-blocking is the worse error here: the human's
# complaint was that the harness dispatched too LITTLE, and the proposal's own falsifier is
# "the hook denies work that should have run".
#
# So: `depth` only when it qualifies a decomposition noun, and `split into N` only in the
# imperative or the first person, and only about sub-lemmas/subgoals/tasks — not "parts",
# not "files", not "pieces".
DEPTH_HINT = re.compile(
    r"(?:decompos\w+|split|breakdown|subgoal|sub-?lemma|拆分?|分解)[^.\n]{0,40}?"
    r"\bdepth\s*[:=]?\s*(\d+)"
    r"|\bdepth\s*[:=]?\s*(\d+)[^.\n]{0,40}?(?:decompos\w+|split|subgoals?|sub-?lemmas?)"
    r"|(?:分解|拆分)\s*(?:到|至)?\s*(?:第)?\s*(\d+)\s*层",
    re.IGNORECASE,
)
CHILDREN_HINT = re.compile(
    r"(?:^|[.\n;]\s*|\b(?:you\s+(?:must|should|will)|please|i\s+will|then)\s+)"
    r"(?:split|decompose|break)\s+(?:this|it|the\s+\w+)?\s*(?:up\s+)?into\s+(\d+)\s*"
    r"(?:sub-?lemmas?|sub-?goals?|children|subproblems?|tasks?|nodes?)"
    r"|(?:拆分?|切分?|分)\s*成\s*(\d+)\s*(?:个)?\s*(?:子引理|子目标|子问题|任务|块|份)",
    re.IGNORECASE,
)


def _first_int(m: "re.Match[str] | None") -> int | None:
    if not m:
        return None
    for g in m.groups():
        if g:
            return int(g)
    return None


def deny(reason: str, fix: str) -> dict:
    """A hook that explains itself. A refusal with no repair is a wall, not a guard."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"dispatch_guard: {reason}\n  -> {fix}",
        }
    }


ALLOW: dict = {}


# One assistant TURN is one `message.id`, and Claude Code writes it across several lines
# — one per content block, plus one per `apiBlockIndex`. Counting lines over-counts by a
# median of 2.27x and by up to 7.7x (measured over 653 real subagent transcripts: 20 real
# turns reported as 154). The first version of this file counted lines, which made the
# 50-turn cap bite at about 24 and would have denied a resume to 166 of those 653 agents
# while they were still under the real cap. The cap in `report.md` §1 is stated in
# message-ids; it has to be enforced in message-ids.
_MSG_ID = re.compile(r'"id"\s*:\s*"(msg_[A-Za-z0-9]+)"')


def turns_spent(agent_ref: str) -> int:
    """Turns already taken by `agent_ref`: DISTINCT assistant message ids in its own
    transcript.

    The transcript is the only honest source — a resume carries no turn count, and the
    orchestrator's belief about how long an agent has run was wrong by an order of
    magnitude in every session measured.
    """
    ref = (agent_ref or "").strip()
    # Exact stem only. A substring glob on `123` matched three unrelated transcripts and
    # the old code SUMMED them, so a short or numeric ref could deny on someone else's
    # turns.
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,}", ref):
        return 0
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return 0
    hits = [q for q in root.glob(f"*/*/subagents/**/agent-{ref}.jsonl")]
    hits += [q for q in root.glob(f"*/*/subagents/**/{ref}.jsonl")]
    ids: set[str] = set()
    for q in hits:
        try:
            with q.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"assistant"' not in line:
                        continue
                    m = _MSG_ID.search(line)
                    if m:
                        ids.add(m.group(1))
        except OSError:
            continue
    return len(ids)


def check_dispatch(tool: str, inp: dict) -> dict:
    brief = " ".join(
        str(inp.get(k, "")) for k in ("prompt", "message", "description", "task")
    )

    # knob 2 — lifetime. A resume is the mechanism that produced the 1,011-turn agent.
    ref = str(inp.get("to") or inp.get("agent_id") or inp.get("agentId") or "")
    if tool == "SendMessage" and ref:
        spent = turns_spent(ref)
        if spent >= MAX_AGENT_TURNS:
            return deny(
                f"agent {ref} has already taken {spent} turns (cap {MAX_AGENT_TURNS}); "
                f"resuming it re-prefills all {spent} of them.",
                "Write what it learned to the DAG node and dispatch a FRESH agent from that "
                "record. 56 of 585 agents took 54.4% of this harness's entire token spend "
                "by living past this line.",
            )

    if NO_RESTART.search(brief):
        return deny(
            "the brief tells the agent not to restart, which is what makes an agent immortal.",
            "Delete the clause. Hand over a node record, not a life: the successor should "
            "read state, not inherit a transcript. (1,143 resumes against 614 spawns.)",
        )

    # knob 1 — granularity.
    d = _first_int(DEPTH_HINT.search(brief))
    if d is not None and d > MAX_DECOMP_DEPTH:
        return deny(
            f"declared decomposition depth {d} exceeds {MAX_DECOMP_DEPTH}.",
            "Give one agent the whole block. The human asked for this seven times, ending "
            '"你这无限切下去了有点，总也做不完".',
        )
    n = _first_int(CHILDREN_HINT.search(brief))
    if n is not None and n > MAX_DECOMP_CHILDREN:
        return deny(
            f"declared {n} children exceeds {MAX_DECOMP_CHILDREN}.",
            "Send a bigger package. A generator with a clear mathematical map closes the "
            "whole group in one life.",
        )
    return ALLOW


def occupancy_note() -> str:
    """knob 3 — occupancy, reported and never blocking.

    The first version of this file had a `check_occupancy` that no code called and that
    returned ALLOW unconditionally, while its docstring claimed it "surfaces the number
    the human had to ask for twelve times". It surfaced nothing: knob 3 was dead code, so
    the twelve slot-refills had no mechanism behind them at all.

    Under-dispatch cannot be fixed by refusing a dispatch, so this attaches a count to
    every allowed dispatch instead — a `systemMessage`, which is the one channel a
    PreToolUse hook has that is read on success.
    """
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return ""
    now = time.time()
    live = 0
    for q in root.glob("*/*/subagents/**/*.jsonl"):
        try:
            if now - q.stat().st_mtime < 300:      # touched in the last five minutes
                live += 1
        except OSError:
            continue
    if live >= MIN_LIVE_AGENTS:
        return ""
    return (f"dispatch_guard: {live} subagent transcript(s) active in the last 5 min. "
            f"The human refilled empty slots by hand twelve times last run "
            f'("your slot is empty now", "不要每次都是我催你"). If there is ready work in '
            f"`dag leaves`, dispatch it in this same message rather than waiting.")


def main() -> int:
    # ONE try around everything. The first version wrapped only `check_dispatch`, so a
    # payload that was a list rather than an object crashed at `payload.get` with a bare
    # traceback and exit 1, and a bad env override crashed at import time. Both "failed
    # open" in the sense that Claude Code does not block on a non-zero hook — but
    # silently, with nothing in the transcript to say the guard was off. A guard that can
    # be off without saying so is the failure mode this whole round is about.
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        tool = str(payload.get("tool_name") or payload.get("toolName") or "")
        inp = payload.get("tool_input") or payload.get("toolInput") or {}
        if not isinstance(inp, dict):
            return 0
        out = check_dispatch(tool, inp) if tool in ("Agent", "Task", "SendMessage") else ALLOW
        if out:
            print(json.dumps(out))
        elif tool in ("Agent", "Task"):
            note = occupancy_note()
            if note:
                print(json.dumps({"systemMessage": note}))
    except (json.JSONDecodeError, ValueError):
        return 0   # an unreadable payload is not a reason to block
    except Exception as exc:                                  # noqa: BLE001
        print(json.dumps({"systemMessage": f"dispatch_guard FAILED OPEN, so the three "
                                           f"dispatch caps are NOT being enforced on this "
                                           f"call: {exc!r}"}))
    return 0


# --- self-test ----------------------------------------------------------------------
# NL-Prover's `dispatch_log.py` is 644 lines that, by its own CLAUDE.md, "has never once
# fired". A hook with no test is that hook. `--self-test` runs on the payload shapes this
# harness actually sends, including the Chinese ones, and is wired into the test suite.

CASES = [
    # (label, payload, expect_deny)
    ("verbatim brief from this harness",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "TASK ID: S9-A5g. WORKTREE: w05 - your predecessor finished cleanly and has "
      "released it. Read BRIEF.md, then STATUS-S9.md. **Continue; do not restart.**"}}, True),
    ("chinese no-restart",
     {"tool_name": "Agent", "tool_input": {"prompt": "接着前一个agent干，继续，不要重新开始"}}, True),
    ("depth over cap, as a decomposition order",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "Plan a decomposition at depth 4 for this block and dispatch the leaves"}}, True),
    # Deliberately ALLOWED since 2026-09-09: a bare mention of depth is mathematics, not
    # a decomposition order. A change-reviewer reproduced "prove the inner step at depth
    # 3 of the induction on n" being denied, and over-blocking is the worse error here.
    ("bare mathematical 'depth': MUST be allowed",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "Prove the inner step at depth 3 of the induction on n."}}, False),
    ("a description of existing structure: MUST be allowed",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "The proof is split into 6 parts across the files; read them all and prove the "
      "last one."}}, False),
    ("children over cap, english",
     {"tool_name": "Agent", "tool_input": {"prompt": "split into 9 sublemmas"}}, True),
    ("children over cap, chinese",
     {"tool_name": "Agent", "tool_input": {"prompt": "把这个拆分成 7 个子引理分别派发"}}, True),
    ("children over cap, chinese 分成",
     {"tool_name": "Agent", "tool_input": {"prompt": "这里分成 8 块派出去"}}, True),
    ("big package, at the cap: MUST be allowed",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "TARGET: close Kakeya.ThinCase.factoringApply end to end. You own the whole block: "
      "prove all 13 conjuncts in one life. depth 1, split into 3 sublemmas if you must."}}, False),
    ("plain work brief: MUST be allowed",
     {"tool_name": "Agent", "tool_input": {"prompt":
      "TARGET: Kakeya.MainLemma1.multiplicity_le_caseTwo. Prove it. Report with a sentinel."}}, False),
    ("unrelated tool: MUST be allowed",
     {"tool_name": "Bash", "tool_input": {"command": "lake build Kakeya"}}, False),
    ("a resume with no agent ref: MUST be allowed",
     {"tool_name": "SendMessage", "tool_input": {"message": "status?"}}, False),
]


def self_test() -> int:
    bad = []
    for label, payload, want_deny in CASES:
        tool = payload["tool_name"]
        inp = payload["tool_input"]
        out = check_dispatch(tool, inp) if tool in ("Agent", "Task", "SendMessage") else ALLOW
        got_deny = bool(out)
        if got_deny != want_deny:
            bad.append(f"{label}: expected {'deny' if want_deny else 'allow'}, got "
                       f"{'deny' if got_deny else 'allow'}")
    # A malformed payload must fail open, exit 0, and not raise. These crashed the first
    # version with a bare traceback and exit 1.
    import io
    import contextlib
    for junk in ("not json", "", "[]", "123", '{"tool_name":"Agent"}',
                 '{"tool_name":"Agent","tool_input":[]}', '{"tool_input":{"prompt":"x"}}'):
        saved = sys.stdin
        try:
            sys.stdin = io.StringIO(junk)
            with contextlib.redirect_stdout(io.StringIO()):
                rc = main()
            if rc != 0:
                bad.append(f"payload {junk!r}: exited {rc}, must fail open with 0")
        except Exception as exc:                                # noqa: BLE001
            bad.append(f"payload {junk!r}: raised {exc!r} instead of failing open")
        finally:
            sys.stdin = saved
    if bad:
        print("DISPATCH_GUARD SELF-TEST FAILED - the guard is not guarding.")
        for b in bad:
            print(f"  - {b}")
        return 1
    print(f"dispatch_guard self-test passed ({len(CASES)} payload shapes, "
          f"caps: turns={MAX_AGENT_TURNS} depth={MAX_DECOMP_DEPTH} children={MAX_DECOMP_CHILDREN})")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    raise SystemExit(main())
