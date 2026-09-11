#!/usr/bin/env python3
"""verify — assemble (and optionally run) one verification dispatch.

    verify dispatch <artifact> --statement F --problem F --output-dir D
                    --mode certification|discovery
                    --verification-mode lemma|target_obstruction|plan_logic|global_refinement
                    [--version N] [--dependency PATH[:PASS|NEEDS_REVISION|none] ...]
                    [--context PATH ...] [--budget-minutes N]
                    [--stop-when packet-written|blocking-issue-found|budget-exhausted]
                    [--workspace W] [--run] [--json]

Two routes to a verdict, and they are the same text
---------------------------------------------------
The Verifier subagent stays. It is the right instrument when the Orchestrator
must open the check itself: a finished article end to end, a gap it spotted, a
claim whose trust field is still pending. Nothing here removes it.

What this adds is the ordinary case. In **certification**, an artifact arrives
for merge with a verifier packet or it does not arrive: `gate.py proof-attempt`
turns it back, and the producer runs this to get one, without a round trip
through the hub. In **discovery**, nothing is required — discovery output
discharges no obligation, carries no proof weight, and a verdict on it would be
a category error.

That is not an extra verification pass. It is the same single pass ADR 0014
settled on, started by the party that already has the artifact in hand. The
number of Verifier checks per merged artifact is unchanged; the number of
Orchestrator round trips is what falls.

The two routes are equivalent because `_verify/dispatch.py` renders the text for
both: `--run` executes it against a cold-start verifier, and without `--run` it
prints exactly what the Orchestrator hands to a subagent. Same generator, so
equivalence is by construction rather than by audit -- and either way a record
lands in `logs/dispatch.jsonl` with the same `prompt_shape` the hook computes,
so `gate.py speed` can put a number on it.

Running it
----------
`--run` needs a cold-start verifier command in `NLPROVER_VERIFIER_CMD`, e.g.

    NLPROVER_VERIFIER_CMD='claude -p --permission-mode acceptEdits'
    NLPROVER_VERIFIER_CMD='codex exec'

The dispatch text is fed on stdin. Without it, `--run` refuses and says so
rather than silently doing nothing: a verification that did not happen must not
look like one that passed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verify import dispatch as dispatch_mod  # noqa: E402
from _verify.dispatch import (  # noqa: E402
    DEPENDENCY_STATES,
    REGIONS,
    STOP_CONDITIONS,
    VERIFICATION_MODES,
    Dependency,
    Dispatch,
    DispatchError,
    anchoring_matches,
)

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "dispatch_log.py"


def _classify(prompt: str) -> dict | None:
    """Score our own dispatch with the hook's classifier, not a copy of it.

    Two copies of this classifier would drift, and then the tool route and the
    subagent route would be scored by different rulers -- which is precisely the
    comparison this is for.
    """
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("_dispatch_log", HOOK)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.classify_prompt(prompt)
    except Exception:
        # Never fail a verification because the telemetry could not load. A
        # record with no prompt_shape reads as unmeasured, which is honest.
        return None


def _log_dispatch(workspace: Path, dispatch: Dispatch, prompt: str, *, ran: bool) -> str | None:
    """One line in the same log the hook writes.

    The hook fires on `Agent|Task`; a tool call is neither, so without this the
    tool route would be invisible to `gate.py speed` and the equivalence claim
    would be unmeasurable -- exactly the state ADR 0003's contract was in before
    anything recorded it.
    """
    logs = workspace / "logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    record = {
        "role": "verifier",
        "target": dispatch.output_paths()["review_packet"],
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": dispatch.region,
        "resume": False,
        "verification_mode": dispatch.verification_mode,
        "source": "verify.py",
        "ran": ran,
    }
    shape = _classify(prompt)
    if shape is not None:
        record["prompt_shape"] = shape
    path = logs / "dispatch.jsonl"
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return None
    return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble one verification dispatch from paths and enums.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("dispatch", help="render (and optionally run) a verification dispatch")
    p.add_argument("artifact", help="the file under review, by path")
    p.add_argument("--statement", required=True, help="the statement it must satisfy")
    p.add_argument("--problem", required=True, help="problem.md")
    p.add_argument("--output-dir", required=True, help="the verifier-owned output directory")
    p.add_argument("--mode", choices=REGIONS, required=True)
    p.add_argument(
        "--verification-mode", choices=sorted(VERIFICATION_MODES), default="lemma"
    )
    p.add_argument("--version", type=int, default=1)
    p.add_argument(
        "--dependency",
        action="append",
        default=[],
        metavar="PATH[:STATE]",
        help="a dependency's statement path and its verdict STATE "
        f"({'|'.join(DEPENDENCY_STATES)}). The state, never the reasoning.",
    )
    p.add_argument(
        "--context", action="append", default=[], metavar="PATH",
        help="a further input, by path (a kb-manager output, a source-theorem package)",
    )
    p.add_argument("--budget-minutes", type=int, default=30)
    p.add_argument("--stop-when", choices=sorted(STOP_CONDITIONS), default="packet-written")
    p.add_argument("--workspace", default=None, help="workspace root, for logs/dispatch.jsonl")
    p.add_argument("--run", action="store_true", help="execute against NLPROVER_VERIFIER_CMD")
    p.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        dispatch = Dispatch(
            region=args.mode,
            verification_mode=args.verification_mode,
            artifact=args.artifact,
            statement=args.statement,
            problem=args.problem,
            output_dir=args.output_dir,
            version=args.version,
            dependencies=[Dependency.parse(raw) for raw in args.dependency],
            context_paths=list(args.context),
            budget_minutes=args.budget_minutes,
            stop_when=args.stop_when,
        )
        prompt = dispatch.render()
    except DispatchError as exc:
        print(f"cannot assemble this dispatch: {exc}", file=sys.stderr)
        return 2

    leaked = anchoring_matches(prompt)
    if leaked:
        # Cannot happen from paths and enums; if it ever does, the claim this
        # tool rests on is false and it must not quietly ship the dispatch.
        print(
            "refusing: the assembled dispatch carries anchoring content "
            f"({', '.join(leaked)}). This is a bug in the assembler.",
            file=sys.stderr,
        )
        return 2

    if not dispatch_mod.guard_is_authoritative():
        print(
            "warning: the anti-anchoring guard could not load the hook's own "
            "patterns and is running on a reduced fallback set. The dispatch "
            "below is NOT guaranteed clean by the check this tool advertises.",
            file=sys.stderr,
        )

    workspace = Path(args.workspace) if args.workspace else None
    command = os.environ.get("NLPROVER_VERIFIER_CMD", "").strip()
    ran = False
    run_error = None

    if args.run:
        if not command:
            print(
                "refusing to run: NLPROVER_VERIFIER_CMD is not set, so no cold-start "
                "verifier was started. A verification that did not happen must not look "
                "like one that passed. Set it, or drop --run and hand the dispatch below "
                "to a Verifier subagent — it is the same text.",
                file=sys.stderr,
            )
            return 3
        try:
            proc = subprocess.run(
                command, shell=True, input=prompt, text=True, capture_output=True
            )
            # Exit 0 is not evidence a verification happened. `cat >/dev/null`
            # exits 0, writes nothing, and used to be logged as `ran: true`
            # against a module whose own rule is that a verification which did
            # not happen must not look like one that passed. The evidence is the
            # packet, at the path this dispatch told the verifier to write.
            packet = Path(dispatch.output_paths()["review_packet"])
            ran = proc.returncode == 0 and packet.is_file()
            if proc.returncode != 0:
                run_error = (proc.stderr or "").strip()[:2000]
            elif not ran:
                run_error = (
                    f"the verifier exited 0 and wrote no packet at {packet}. "
                    "Exit status is not a verdict; treat this as no verification "
                    "at all, not as a pass"
                )
        except OSError as exc:
            run_error = str(exc)

    log_path = _log_dispatch(workspace, dispatch, prompt, ran=ran) if workspace else None

    if args.json:
        print(
            json.dumps(
                {
                    "ok": (not args.run) or ran,
                    "mode": dispatch.region,
                    "verification_mode": dispatch.verification_mode,
                    "outputs": dispatch.output_paths(),
                    "ran": ran,
                    "run_error": run_error,
                    "dispatch_log": log_path,
                    "prompt_chars": len(prompt),
                },
                indent=2,
            )
        )
    else:
        print(prompt)
        if log_path:
            print(f"# recorded in {log_path}", file=sys.stderr)
        if run_error:
            print(f"# verifier command failed: {run_error}", file=sys.stderr)

    return 0 if ((not args.run) or ran) else 1


if __name__ == "__main__":
    raise SystemExit(main())
