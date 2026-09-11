#!/usr/bin/env python3
"""verdict — a build log becomes a verdict only if it says so, and only twice.

THE THREE THINGS THAT WENT WRONG, from the 2,663 build logs of the 2026-09-01..09-06 run.

1. **28.9% of logs (770 of 2,663) carried no verdict line at all.** The harness's own
   BRIEF already said what to do about that — "treat a missing `EXIT=` sentinel as a
   stall, never as progress" — in prose, to a reader. So a truncated log, a killed build
   and a finished build were indistinguishable, and the orchestrator read whichever one
   suited it. Here a missing sentinel is a distinct verdict, `STALL`, and it is not a pass.

2. **`grep error:` is not a health signal, in either direction.** One real log carries 32
   `error:` lines from a broken scratch file and still ends "Build completed successfully";
   285 logs contain `error:` in the tail while exiting 0. Exit status alone is not enough
   either: `lake build` can succeed having compiled nothing (1,408 logs — 53% — compiled
   zero modules, and four builds of one target inside 4m46s were byte-identical after
   normalising lake's drifting job estimate). So a pass needs BOTH an exit-0 sentinel AND
   a positive completion marker naming the jobs it did. Silence is not success.

3. **Nobody ever checked anybody.** `grep -rn "independent|rerun|second"` across this
   harness's prompts returns one weak hit. `cli_tools.lean` was invoked 3,298 times
   against 14,238 raw `lake` calls — the four real gates were routed around 4.3:1 — so in
   practice the author of a proof was also the only witness to its verdict.

   The fix is the one both reference harnesses use, and it is cheap: a second party must
   re-run the check itself and *say that it did*. `AuditRecord.passed` is false unless
   `reran`, `passed`, `statement_matches` are all true, `issues` is empty, AND
   `declarations` is non-empty — a reviewer who approves without naming what it saw
   compiled is mechanically a rejection. That last clause is the one that catches the
   agreeable reviewer.

None of this checks mathematics. It checks that a claim about a build is traceable to a
log that actually says so.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# `lake build` prints this on a real completion, with the job count it actually ran.
COMPLETION = re.compile(r"Build completed successfully\s*(?:\((\d+)\s+jobs?\))?", re.IGNORECASE)

# The sentinel the harness appends: `echo "EXIT=$?"`. Also the prefixed variants it really
# writes — BUILD_EXIT=, MOD EXIT=, FULLEXIT=, SWEEP_EXIT=, PROBE_EXIT=, MUT_EXIT=, AXEXIT=,
# PY_EXIT=. 66 of 2,541 real logs recorded an exit status under one of those names and were
# called STALL for having "no verdict at all", which overstated that bucket by 3.7%.
SENTINEL = re.compile(r"^(?:[A-Z][A-Z0-9_]*[ _])?EXIT=(-?\d+)\s*$", re.MULTILINE)

# `^(?:error|.*\berror:)` case-insensitively matched 41,199 lines across those 2,541 logs
# of which only 2,119 (5.1%) were error-severity diagnostics. The bulk was ONE Mathlib
# linter message that embeds the text "error:" inside an `info:` line, and 33 logs had
# their own summary line `ERRORLINES=0` counted as an error because `^(?:error` had nothing
# after it.
#
# This mattered beyond tidiness: the commit that introduced this file asserted "one real
# log carries 32 `error:` lines and still ends Build completed successfully". That log is
# `base/_int14/logs/build_p0.log`, its `grep -c "^error:"` is ZERO, and its own tail reads
# `ERRORLINES=0`. The claim was an artifact of this regex. A lint that miscounts by 19x is
# how a false number reaches a report — which is the whole subject of the round that wrote
# it. Severity now has to LEAD the line, or be a Lean diagnostic's `file:line:col: error:`.
ERROR_LINE = re.compile(
    r"^\s*(?:error:|error\b(?!\s*(?:lines?|s?\s*[:=]\s*0))"
    r"|[\w./\-]+\.lean:\d+:\d+:\s*error:)",
    re.MULTILINE,
)
# lake prefixes every progress line with a status glyph — `✔ [2754/2771] Replayed X`,
# `⚠ [...] Built Y`. The first version of this anchored on `^\s*\[` and therefore
# matched NOTHING, so `built` was 0 for all 2,541 real logs and the tool cheerfully
# reported "every passing build compiled nothing". That is this round's own subject matter
# happening inside its own tool: a parser that reads a field the artifact does not have,
# agreeing with a fixture that was written to match the parser. The fixtures below now
# carry the real byte sequences, glyph and all.
BUILT = re.compile(r"\[\d+/\d+\]\s+Built\b")
REPLAYED = re.compile(r"\[\d+/\d+\]\s+Replayed\b")

PASS, FAIL, STALL = "PASS", "FAIL", "STALL"


@dataclass
class Verdict:
    log: str
    verdict: str = STALL
    exit_code: int | None = None
    jobs: int | None = None
    built: int = 0
    replayed: int = 0
    errors: int = 0
    sentinels: int = 0
    completions: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict == PASS


def read_log(path: Path, marker: str = "") -> Verdict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return Verdict(log=str(path), verdict=STALL, reasons=[f"unreadable: {exc}"])

    v = Verdict(log=str(path))
    if not text.strip():
        v.reasons.append(
            "the log is EMPTY. An empty input hashes to d41d8cd98f00b204e9800998ecf8427e, "
            "which is why an empty log looks like a real artifact until it is opened."
        )
        return v

    # ORDER MATTERS, and the first version ignored it. `search()` returns the FIRST match,
    # so a log holding an early `EXIT=0` and a later `EXIT=1` — or a completion marker from
    # one build concatenated ahead of the next build's failure — was reported PASS with
    # exit 0. The predicate claimed was "exit 0 AND a completion marker"; what shipped was
    # "an EXIT= somewhere AND a marker somewhere", which is a different and weaker thing.
    # In today's 2,541 logs, 20 carry more than one completion marker and 3 more than one
    # sentinel, so the shape is already present in this harness's own output.
    #
    # The LAST sentinel is the verdict of the last thing that ran, and a completion marker
    # only counts if it appears BEFORE that sentinel.
    sentinels = list(SENTINEL.finditer(text))
    if sentinels:
        last = sentinels[-1]
        v.exit_code = int(last.group(1))
        v.sentinels = len(sentinels)
        completions = [c for c in COMPLETION.finditer(text) if c.start() < last.start()]
    else:
        completions = list(COMPLETION.finditer(text))
    v.completions = len(completions)
    c = completions[-1] if completions else None
    if c and c.group(1):
        v.jobs = int(c.group(1))
    v.built = len(BUILT.findall(text))
    v.replayed = len(REPLAYED.findall(text))
    v.errors = len(ERROR_LINE.findall(text))

    if v.exit_code is None:
        v.reasons.append(
            "no `EXIT=` sentinel. A missing sentinel is a STALL, never progress — 770 of "
            "2,663 logs in the last run had none, and were read as whatever suited."
        )
        return v
    if v.exit_code != 0:
        v.verdict = FAIL
        v.reasons.append(f"EXIT={v.exit_code}")
        return v
    if not c:
        v.verdict = FAIL
        v.reasons.append(
            "EXIT=0 but no completion marker. `lake build` exiting 0 without saying it "
            "completed is a silent success, and a silent success is a failure here."
        )
        return v
    if marker and marker not in text:
        v.verdict = FAIL
        v.reasons.append(f"required marker {marker!r} absent — the project gate did not pass")
        return v

    v.verdict = PASS
    if v.sentinels > 1 or v.completions > 1:
        v.reasons.append(
            f"NOTE: this log records {v.sentinels} exit sentinel(s) and {v.completions} "
            "completion marker(s) before the last one — it is more than one run. The "
            "verdict above is the LAST run's; if you meant to check an earlier one, split "
            "the log."
        )
    if v.built == 0:
        v.reasons.append(
            f"NOTE: passed, but compiled nothing ({v.replayed} replayed, 0 built). 53% of "
            "the last run's logs were like this; it is a cache hit, not evidence that this "
            "edit type-checks."
        )
    if v.errors:
        v.reasons.append(
            f"NOTE: passed with {v.errors} `error:` line(s) in the output — from a scratch "
            "file or a stale target, not from the built target. Do not grep for `error:` "
            "to decide health; one real log has 32 of them and completed successfully."
        )
    return v


@dataclass
class AuditRecord:
    """A second party's verdict. Every field is a claim it has to make explicitly."""

    node: str
    log: str
    reviewer: str = ""
    reran: bool = False
    reran_verdict: str = ""
    statement_matches: bool = False
    declarations: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def refusals(self) -> list[str]:
        out = []
        if not self.reviewer.strip():
            out.append("no reviewer named; an anonymous audit is the author's own opinion")
        if not self.reran:
            out.append(
                "`reran` is false. The reviewer must re-run the check itself. Reading the "
                "author's log is not a second party — it is the same party twice."
            )
        elif self.reran_verdict != PASS:
            out.append(f"the reviewer's own re-run returned {self.reran_verdict or '(nothing)'}")
        if not self.statement_matches:
            out.append(
                "`statement_matches` is false: the proof does not discharge the frozen "
                "statement. This is the check that catches a proof of something adjacent."
            )
        if self.issues:
            out.append(f"{len(self.issues)} unresolved issue(s): {'; '.join(self.issues[:3])}")
        if not self.declarations:
            out.append(
                "`declarations` is empty. A reviewer that approves without naming what it "
                "saw compiled has not looked — this clause exists to catch the agreeable "
                "reviewer, and it is the one that fires most."
            )
        return out

    @property
    def passed(self) -> bool:
        return not self.refusals()


def cmd_read(args) -> int:
    v = read_log(Path(args.log).expanduser(), args.marker or "")
    if args.json:
        print(json.dumps(asdict(v) | {"ok": v.ok}, indent=2, ensure_ascii=False))
    else:
        print(f"{v.verdict}  {v.log}")
        print(f"  exit={v.exit_code}  jobs={v.jobs}  built={v.built}  replayed={v.replayed}"
              f"  error_lines={v.errors}")
        for r in v.reasons:
            print(f"  - {r}")
    return 0 if v.ok else 1


def cmd_audit(args) -> int:
    rec = AuditRecord(
        node=args.node, log=args.log, reviewer=args.reviewer or "",
        reran=args.reran, reran_verdict=args.reran_verdict or "",
        statement_matches=args.statement_matches,
        declarations=[d for d in (args.declarations or "").split(",") if d.strip()],
        issues=[i for i in (args.issue or [])],
    )
    bad = rec.refusals()
    if args.json:
        print(json.dumps(asdict(rec) | {"passed": rec.passed, "refusals": bad},
                         indent=2, ensure_ascii=False))
    elif bad:
        print(f"AUDIT REFUSED for {rec.node}:")
        for b in bad:
            print(f"  - {b}")
    else:
        print(f"AUDIT PASSED for {rec.node} by {rec.reviewer} "
              f"({len(rec.declarations)} declaration(s) named)")
    if rec.passed and args.record:
        p = Path(args.record).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(rec), indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
        print(f"  recorded -> {p}")
    return 0 if rec.passed else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lean verdict", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("read", help="turn one build log into PASS/FAIL/STALL")
    q.add_argument("log")
    q.add_argument("--marker", default="", help="literal project-gate marker that must appear")
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_read)
    q = sub.add_parser("audit", help="record a SECOND party's verdict")
    q.add_argument("--node", required=True)
    q.add_argument("--log", required=True)
    q.add_argument("--reviewer", default="")
    q.add_argument("--reran", action="store_true")
    q.add_argument("--reran-verdict", dest="reran_verdict", default="")
    q.add_argument("--statement-matches", dest="statement_matches", action="store_true")
    q.add_argument("--declarations", default="")
    q.add_argument("--issue", action="append")
    q.add_argument("--record", default="")
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_audit)
    return p


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    args = build_parser().parse_args(argv)
    return args.fn(args)


# --- self-test ----------------------------------------------------------------------
# Every fixture below is a log shape that really occurred in the 2,663 logs.

def self_test() -> int:
    import tempfile
    fails: list[str] = []

    cases = [
        ("clean pass", "\u2714 [1/9223] Built Kakeya.Foo\nBuild completed successfully (9223 jobs).\nEXIT=0\n", PASS),
        ("no sentinel at all (770 real logs)", "\u2714 [1/9223] Built Kakeya.Foo\nBuild completed successfully (9223 jobs).\n", STALL),
        ("empty log", "", STALL),
        ("nonzero exit", "error: unknown identifier\nEXIT=1\n", FAIL),
        ("exit 0 but silent", "\u26a0 [1/9223] Replayed Kakeya.Foo\nEXIT=0\n", FAIL),
        ("killed build (EXIT=143)", "some output\nEXIT=143\n", FAIL),
        # The real one: 32 error: lines and a successful completion.
        ("32 error lines but a real completion", "\n".join(
            ["error: scratch/Broken.lean:1:0: unexpected token"] * 32
            + ["\u2714 [1/9223] Built Kakeya.Foo", "Build completed successfully (9223 jobs).", "EXIT=0"]), PASS),
        # Compiled nothing: a cache hit read as a verdict.
        ("passed having built nothing", "\n".join(
            ["\u26a0 [1/9030] Replayed Kakeya.Foo"] * 5
            + ["Build completed successfully (9030 jobs).", "EXIT=0"]), PASS),

        # --- the three false-PASS logs a change-reviewer built on 2026-09-09 ------------
        # All three were reported PASS with exit 0 by the first version, because `search()`
        # returns the FIRST match and order was never checked. 20 of the harness's own
        # 2,541 logs already carry more than one completion marker.
        ("two runs concatenated, the second one failed", "\n".join([
            "\u2714 [1/1] Built Kakeya.Foo",
            "Build completed successfully (1 jobs).",
            "EXIT=0",
            "=== second build of same target ===",
            "error: unknown identifier",
            "lake build failed",
            "EXIT=1"]), FAIL),
        ("marker and EXIT=0 first, failure after", "\n".join([
            "Build completed successfully (9 jobs).",
            "EXIT=0",
            "error: elaboration failed",
            "lake: build FAILED",
            "EXIT=1"]), FAIL),
        # A completion marker AFTER the last sentinel does not count: nothing says the
        # marker belongs to the run the sentinel reported on.
        ("marker printed after the sentinel", "\n".join([
            "the wrapper printed:",
            "EXIT=0",
            "Build completed successfully",
            "(this text was cat-ed from documentation)"]), FAIL),
        # A prefixed sentinel is a sentinel: 66 real logs recorded one and were called
        # STALL for having no verdict at all.
        ("prefixed sentinel BUILD_EXIT=", "\n".join([
            "\u2714 [1/9] Built Kakeya.Foo",
            "Build completed successfully (9 jobs).",
            "BUILD_EXIT=0"]), PASS),
        ("prefixed sentinel MUT_EXIT= nonzero", "MUT_EXIT=1\n", FAIL),
    ]
    with tempfile.TemporaryDirectory() as td:
        for label, body, want in cases:
            p = Path(td) / (re.sub(r"\W+", "_", label) + ".log")
            p.write_text(body, encoding="utf-8")
            got = read_log(p)
            if got.verdict != want:
                fails.append(f"{label}: expected {want}, got {got.verdict} ({got.reasons})")
        # the marker gate
        p = Path(td) / "marker.log"
        p.write_text("Build completed successfully (9 jobs).\nEXIT=0\n", encoding="utf-8")
        if read_log(p, marker="Your solution is okay!").verdict != FAIL:
            fails.append("a missing project marker was not a FAIL")
        # NOTE lines must be attached, not swallowed
        v = read_log(Path(td) / "passed_having_built_nothing.log")
        if not any("compiled nothing" in r for r in v.reasons):
            fails.append("a pass that built nothing carried no warning")
        if v.replayed != 5:
            fails.append(f"replayed counter: expected 5, got {v.replayed} — the progress-line "
                         "regex is not matching lake's real output")
        v = read_log(Path(td) / "clean_pass.log")
        if v.built != 1:
            fails.append(f"built counter: expected 1, got {v.built} — same regex, other side")

        # ERROR_LINE precision. The lines below are verbatim shapes from the real logs that
        # the first regex counted as errors: a Mathlib linter message embedding "error:"
        # inside an `info:` line, and the harness's own `ERRORLINES=0` summary. It matched
        # 41,199 lines where 2,119 were errors, and that 19x over-count is what put a false
        # sentence into a commit message and a report.
        p = Path(td) / "errprec.log"
        p.write_text("\n".join([
            "info: Kakeya/SetupAbsorption.lean:11:0: linter.style.header:23:23: "
            "error: unexpected token '>'",
            "warning: declaration uses 'sorry'",
            "ERRORLINES=0",
            "errors: 0",
            "error: unknown identifier 'foo'",
            "Kakeya/Bar.lean:12:4: error: type mismatch",
            "Build completed successfully (3 jobs).",
            "EXIT=0",
        ]), encoding="utf-8")
        v = read_log(p)
        if v.errors != 2:
            fails.append(
                f"error_lines: expected 2 real diagnostics, got {v.errors}. The linter "
                "message, the warning, ERRORLINES=0 and 'errors: 0' must not count."
            )

    # the audit record
    full = dict(node="n1", log="/tmp/a.log", reviewer="f-reviewer", reran=True,
                reran_verdict=PASS, statement_matches=True, declarations=["Kakeya.foo"])
    if not AuditRecord(**full).passed:
        fails.append(f"a complete audit was refused: {AuditRecord(**full).refusals()}")
    for missing, label in (
        ({"reran": False}, "an audit that did not re-run"),
        ({"reran_verdict": FAIL}, "an audit whose own re-run failed"),
        ({"statement_matches": False}, "an audit where the statement does not match"),
        ({"declarations": []}, "an audit naming no declarations (the agreeable reviewer)"),
        ({"reviewer": ""}, "an anonymous audit"),
        ({"issues": ["unresolved"]}, "an audit with open issues"),
    ):
        if AuditRecord(**(full | missing)).passed:
            fails.append(f"{label} was ACCEPTED")

    if fails:
        print("VERDICT SELF-TEST FAILED — a claim about a build is not being checked.")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"verdict self-test passed ({len(cases)} real log shapes + 6 audit refusals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
