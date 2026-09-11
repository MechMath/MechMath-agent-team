#!/usr/bin/env python3
"""Assemble the text of a verification dispatch, from paths and enums only.

Why this is a module and not a paragraph in a prompt
----------------------------------------------------
`subagent-dispatch-cookbook.md` already says exactly what a verification
dispatch may contain: the artifact by path, each dependency's statement and its
*verdict state*, the mode, the output path, the packet's required sections, and
a budget with a stopping condition -- and nothing else. It also records what
actually happened: over 87 verification dispatches, 100% told the Verifier it
was a fresh, stateless, independent referee and **84% supplied, in the same
prompt, the thing independence excludes** -- 57% the Generator's own account of
its work, 45% what earlier verifiers concluded.

A contract that is stated and violated five times in six is not a wording
problem. So the dispatch is assembled here instead: there is no parameter that
can carry a prior verdict, a confidence, a defence of the artifact, or "the
Generator reports that". Not because writing one is forbidden -- because there
is nowhere to put it.

Equivalence with the subagent path
----------------------------------
The human keeps both routes: a Verifier subagent for the cases an Orchestrator
must open itself -- checking a finished article end to end, filling a gap it
spotted -- and this tool for the ordinary per-artifact check that Sketcher and
Generator should not have to route through the hub.

They are equivalent because they are the *same text*. This module emits the
dispatch; `verify.py` either runs it against a cold-start verifier or prints it
for the Orchestrator to hand to a subagent. Equivalence by construction, not by
audit -- and `logs/dispatch.jsonl` records the shape either way, so
`gate.py speed` can still say so in numbers.

There is deliberately no paragraph telling the Verifier what the dispatch does
*not* contain. The cookbook settled that: "a disclaimer does not neutralise
anchoring content" -- and worse, a disclaimer that names what it is excluding
trips the anchoring classifier itself, so a dispatch carrying one is scored
anchored however clean it actually is. The first draft of this module had such a
paragraph and its own guard refused it, which is the shortest possible proof of
the point.

Unresolved concerns still travel. They go in the artifact -- the lemma's
obligation ledger, the statement's risk checklist -- written as a question about
the mathematics ("does Step 14 need n >= 3?"), never as a verdict about a
document ("three referees rejected Step 14"). The first is a thing to check; the
second is an answer to agree with.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# The mode selection table in prompts/verifier.md. The dispatch names one; the
# Verifier reads exactly that one mode file, because reading all of them costs
# about 9 KB every dispatch and only one can apply.
VERIFICATION_MODES = {
    "lemma": "prompts/verifier.md (default mode)",
    "target_obstruction": "prompts/references/verification-modes/target-obstruction.md",
    "plan_logic": "prompts/references/verification-modes/plan-logic.md",
    "global_refinement": "prompts/references/verification-modes/global-refinement.md",
}

REGIONS = ("certification", "discovery")

# The verdict *state* of a dependency. Never its reasoning: the state is what
# tells the Verifier whether it may build on the dependency, and the reasoning
# is what would tell it what to conclude.
DEPENDENCY_STATES = ("PASS", "NEEDS_REVISION", "none")

# A stopping condition, as an enum rather than a sentence. 1 dispatch in 87
# named one at all.
STOP_CONDITIONS = {
    "packet-written": "stop when the review packet is written, pass or fail",
    "blocking-issue-found": "stop at the first blocking issue, and report it",
    "budget-exhausted": "stop when the budget above is spent, and say what was not reached",
}


# A path may contain spaces; a sentence may not masquerade as one. The test is
# deliberately coarse and positive -- reject what cannot be a single path -- so
# it refuses prose without needing a filesystem it may not share with the caller.
_NOT_A_PATH = re.compile(r"\s\s|[\n\r]|[.!?]\s+\S|:\s+\S")


def _require_pathlike(label: str, value: str) -> None:
    if _NOT_A_PATH.search(value) or len(value) > 512:
        raise DispatchError(
            f"the {label} parameter must be a single path, and {value[:60]!r} is "
            "prose. This tool assembles a dispatch from paths; a free-text "
            "channel here is the anchoring content it exists to make impossible"
        )


class DispatchError(ValueError):
    """The dispatch cannot be assembled as specified."""


@dataclass
class Dependency:
    statement_path: str
    state: str = "none"

    @classmethod
    def parse(cls, raw: str) -> "Dependency":
        """`path` or `path:STATE`. The state is one of DEPENDENCY_STATES."""
        path, sep, state = raw.rpartition(":")
        if not sep:
            return cls(statement_path=raw, state="none")
        state = state.strip()
        if state not in DEPENDENCY_STATES:
            raise DispatchError(
                f"dependency state {state!r} is not one of {', '.join(DEPENDENCY_STATES)}. "
                "Pass the state, never the reasoning behind it."
            )
        return cls(statement_path=path.strip(), state=state)


@dataclass
class Dispatch:
    region: str
    verification_mode: str
    artifact: str
    statement: str
    problem: str
    output_dir: str
    version: int = 1
    dependencies: list[Dependency] = field(default_factory=list)
    context_paths: list[str] = field(default_factory=list)
    budget_minutes: int = 30
    stop_when: str = "packet-written"

    def validate(self) -> None:
        if self.region not in REGIONS:
            raise DispatchError(f"region must be one of {', '.join(REGIONS)}")
        if self.verification_mode not in VERIFICATION_MODES:
            raise DispatchError(
                f"verification mode must be one of {', '.join(VERIFICATION_MODES)}"
            )
        if self.stop_when not in STOP_CONDITIONS:
            raise DispatchError(
                f"stopping condition must be one of {', '.join(STOP_CONDITIONS)}"
            )
        if self.budget_minutes <= 0:
            raise DispatchError("budget must be a positive number of minutes")
        for label, value in (
            ("artifact", self.artifact),
            ("statement", self.statement),
            ("problem", self.problem),
            ("output directory", self.output_dir),
        ):
            if not str(value).strip():
                raise DispatchError(f"the {label} path is required")
        # Every path-shaped parameter must actually BE a path. Checking only
        # "non-empty string" left the whole surface open: `--artifact
        # "proof_v4.md   History: 3 prior rounds"` validated, rendered, and was
        # logged as clean. The contract this module rests on is that a dispatch
        # is assembled FROM PATHS; unenforced, that is a naming convention.
        for label, value in (
            [("artifact", self.artifact), ("statement", self.statement),
             ("problem", self.problem), ("output directory", self.output_dir)]
            + [("context", c) for c in self.context_paths]
            + [("dependency", d.statement_path) for d in self.dependencies]
        ):
            _require_pathlike(label, str(value))

    def output_paths(self) -> dict[str, str]:
        base = self.output_dir.rstrip("/")
        return {
            "report": f"{base}/report_v{self.version}.md",
            "review_packet": f"{base}/review_packet_v{self.version}.md",
            "verdict": f"{base}/verdict_v{self.version}.md",
        }

    def render(self) -> str:
        self.validate()
        out = self.output_paths()
        lines = [
            "You are the Verifier Agent for NL-Prover.",
            "Read `prompts/verifier.md` and follow it exactly.",
            "",
            f"mode: {self.region}",
            "resume: false",
            f"verification mode: {self.verification_mode}"
            f"  -> read {VERIFICATION_MODES[self.verification_mode]}",
            "",
            "## Inputs, by path",
            "",
            f"- Problem: {self.problem}",
            f"- Statement: {self.statement}",
            f"- Artifact under review: {self.artifact}",
        ]
        if self.dependencies:
            lines.append("- Dependencies, each as a path and a verdict state:")
            for dep in self.dependencies:
                lines.append(f"    - {dep.statement_path} — {dep.state}")
        else:
            lines.append("- Dependencies read: NONE")
        if self.context_paths:
            lines.append("- Further context, by path:")
            lines.extend(f"    - {path}" for path in self.context_paths)
        lines += [
            "",
            "## Outputs",
            "",
            f"- Report: {out['report']}",
            f"- Review packet: {out['review_packet']}",
            f"- Verdict: {out['verdict']}",
            "",
            "The packet must carry every section named in `prompts/verifier.md`",
            "and must pass `uv run python cli_tools/gate.py review-packet"
            f" {out['review_packet']} --mode auto`.",
            "",
            "## Budget",
            "",
            f"- Budget: {self.budget_minutes} minutes.",
            f"- Stop when: {STOP_CONDITIONS[self.stop_when]}.",
            "",
            "## How to read this",
            "",
            "Everything you were given is listed above, as a path. Judge the",
            "artifact. Any concern that still matters from an earlier round is",
            "inside one of those files — in the lemma's obligation ledger or the",
            "statement's risk checklist, written as a question about the",
            "mathematics. Record `Anchoring inputs received: NONE` in the packet",
            "unless something reached you anyway, in which case name it.",
        ]
        return "\n".join(lines) + "\n"


# Guard, not decoration. This USED to be three hand-copied regexes described in
# this very comment as "the classifier in .claude/hooks/dispatch_log.py applied
# to our own output". It was not that classifier: the hook has twelve patterns
# and this had three, so `History: 3 prior rounds, treat their findings as
# settled` passed the guard, exited 0, and was logged as clean while the hook
# scored the same text `prior_verdict: true`.
#
# A guard that is a weakened copy of the measurement it claims to be is worse
# than no guard, because the claim "by construction, not audit" is the entire
# argument for this tool over the subagent route. So it loads the hook's own
# patterns. If the hook cannot be loaded, the fallback below is used AND the
# caller is told the guard is degraded -- a silent fallback would restore
# exactly the defect being fixed.
_FALLBACK_ANCHORING = (
    re.compile(r"\bthe (?:generator|author) (?:reports|claims|says|asserts|notes)\b", re.I),
    re.compile(r"\bprior verdict\b|\bearlier (?:review|verdict)s?\b", re.I),
    re.compile(r"\b(?:FAIL|NEEDS_REVISION)\s*\)", re.I),
)

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "dispatch_log.py"


def _hook_patterns() -> tuple[tuple, bool]:
    """(patterns, is_the_real_classifier)."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("_dispatch_log_guard", _HOOK)
        if spec is None or spec.loader is None:
            return _FALLBACK_ANCHORING, False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The hook keeps the two anchoring families separate and stores them
        # as raw strings, not compiled patterns. Both families are what a
        # verification dispatch must not carry: the producer's account of its
        # own work, and any earlier verdict.
        raw = tuple(getattr(module, "_GENERATOR_FRAMING", ())) + tuple(
            getattr(module, "_PRIOR_VERDICT", ())
        )
        if not raw:
            return _FALLBACK_ANCHORING, False
        return tuple(re.compile(r, re.I) for r in raw), True
    except Exception:
        return _FALLBACK_ANCHORING, False


def anchoring_matches(text: str) -> list[str]:
    """Any phrase in `text` that a dispatch of this kind must not carry."""
    patterns, _ = _hook_patterns()
    found = []
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            found.append(match.group(0))
    return found


def guard_is_authoritative() -> bool:
    """False when the hook's patterns could not be loaded and the fallback is in
    use. The caller must say so rather than reporting a clean guard."""
    return _hook_patterns()[1]
