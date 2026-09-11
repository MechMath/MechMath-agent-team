#!/usr/bin/env python3
"""Speed gate — the run's own cost telemetry (ADR 0024 §J).

Every other gate in this package checks whether the mathematics is *shaped*
right. None of them reads a clock or counts a byte, so a change that halves the
cost of a run and a change that doubles it look identical from the outside. This
gate reports cost. It is the scale, not the recipe: it changes no behaviour and,
by default, blocks nothing.

    gate speed <workspace> [--json] [--strict] [--read-budget KB] [--waste-ratio R]

It reports three problem-independent observables — a harder problem makes a run
longer, but it does not make 96% of a document reappear verbatim in its
successor, and it does not make `STATUS.md` accumulate closed branch rows:

- **rewrite waste**: across every versioned artifact family (`*_v<N>.md`) with
  at least two versions, the fraction of bytes written that a later version
  superseded. A Generator that repairs its proof scores low; one that re-emits
  the whole document for a localised defect scores high. Measured at 0.79 on a
  26-hour run.
- **accretion**: families whose artifact grows monotonically across revisions.
  Growth per revision is the signature of accumulated rebuttal rather than
  closed obligations, and it makes every subsequent revision more expensive
  than the last.
- **required-read bytes**: the size of the set `orchestrator-cookbook.md` asks
  the Orchestrator to read at the start of every round. This one grows with run
  length rather than with problem difficulty, so it makes round N cost more than
  round 1 regardless of what round N is doing.
- **observed concurrency**: peak overlap of dispatch windows from
  `logs/dispatch.jsonl` when it has them, falling back to the largest number of
  distinct lemmas whose generator artifacts landed inside one window. The
  fallback is trustworthy only when *low* — a bulk copy rewrites every mtime at
  once — and it undercounts badly on a one-lemma run, where it reported 1
  against a logged peak of 4. Declared capacity is 6.
- **real batches (ADR 0024 §3.A3)**: a group ran concurrently iff its landing
  spread is strictly under one agent's median turnaround. Turnaround is read
  from `logs/dispatch.jsonl` and **reported as unmeasured without it** — it
  cannot be estimated from the gaps between artifacts, because when a run is one
  large batch those gaps *are* the batch's own spread and the estimate chases
  its own tail.
- **dispatch prompt shape**: how many verifier dispatches were anchored (framed
  by the Generator's own account or by a prior verdict), named a budget, or
  named a stopping condition — from the `prompt_shape` booleans the dispatch
  hook records. Reported, never scored. Baseline from a hand-read sample of 87
  verifier dispatches: 84% anchored, 48% budgeted, 1% with a stopping condition,
  5.3x length spread. **A log whose records carry no `prompt_shape` reads as
  unmeasured, not as 0% anchored** — the two look identical in a number and mean
  opposite things.
- **status hygiene**: whether `STATUS.md` still carries the append-only
  `## History` narrative or rows that already reached `rejected`/`done`. Both
  are re-read every round and neither is used for routing.
- **timing record**: whether the run left a `logs/dispatch.jsonl`. Without it
  every later timing has to be reconstructed from mtimes, which cannot separate
  a stalled harness from an operator who stepped away. No timing, no
  optimisation.

Nothing here is a mathematical judgement. A high score is a question to ask, not
a verdict — a genuinely hard lemma may deserve eleven revisions. What it should
not do is pay for the first ten of them twice.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

from _gate import waiver

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.indexing import version_of  # noqa: E402


# What the Orchestrator is told to read at the start of every non-trivial cycle
# (.agents/skills/nl-prover/references/orchestrator-cookbook.md step 1). Globs,
# because "latest review packets" and "recovery packets" are plural there.
REQUIRED_READ_GLOBS = (
    "problem.md",
    "STATUS.md",
    "recovery/route_history.md",
    "recovery/*.md",
    "**/review_packet_v*.md",
)

# Directories that are inputs to the run, not products of it.
SKIP_PARTS = ("references", "__pycache__", ".git", ".venv", "node_modules")

DEFAULT_READ_BUDGET_KB = 60
DEFAULT_WASTE_RATIO = 0.5
DEFAULT_TOP_N = 5

# A batch dispatched together lands together. 10 minutes is wide enough that a
# slow member of a genuine batch still counts, and narrow enough that two
# sequential dispatches do not get merged into one apparent batch.
CONCURRENCY_WINDOW_S = 600
# The policy ceiling, and its SSOT is orchestrator-cookbook.md. `gate contracts`
# checks that this constant and that file agree, because this one is what the
# warning below compares against: a stale copy here tells every run that obeyed
# the policy that its own concurrency was unmeasured.
#
# Briefly 12 on 2026-08-25, reverted the same day. `.codex/config.toml` enforces
# `max_threads = 6`, so on Codex 6 is not a number in a file, it is the limit —
# and the cookbook is read by both platforms. The two now agree at 6 and the
# question of whether they should both move is ADR 0024 Q8, whose unlock
# condition is a dispatch log that has never been written.
DECLARED_CONCURRENCY = 6

# Statuses whose rows are finished and no longer routing input. Must stay in
# step with _gate/discovery.ALLOWED_STATUSES.
ARCHIVABLE_STATUSES = ("rejected", "done")

# The routing shape from prompts/references/status-and-recovery.md. A STATUS.md
# that has drifted off this shape has stopped being a routing file and become a
# lab notebook: sections accrete freely because nothing says which ones belong,
# and every one of them is re-read at the start of every round.
TEMPLATE_SECTIONS = (
    "problem",
    "target contract",
    "phase",
    "lemma status",
    "open proof obligations",
    "active branch queue",
)
DRIFT_SECTION_LIMIT = 12

REQUIREMENT = waiver.requirement_text(
    checks="what a run cost itself: bytes written that a later version superseded, artifact\n"
           "families that grow monotonically across revisions, and the size of the set the\n"
           "Orchestrator re-reads every round.\n"
           "\n"
           "Also reported, advisory: the shape of the dispatch prompts, from the\n"
           "prompt_shape field written by .claude/hooks/dispatch_log.py. Measured baseline,\n"
           "hand-read from 87 verifier dispatches before the ADR 0003 contract landed:\n"
           "anchored 84%, names a budget 48%, names a stopping condition 1%, length spread\n"
           "5.3x. The contract's expected-fix set is anchored <=20%, stopping >=80%, spread\n"
           "<=2.5x. Neither set is a threshold here — this gate reports the number and\n"
           "leaves the comparison to the reader. A log whose records carry no prompt_shape\n"
           "is reported as unmeasured, never as 0%.",
    legal="any workspace. Exits 1 on an error; --strict promotes warnings too.\nThresholds are --read-budget (KB, default 60) and --waste-ratio (default 0.5).",
    fix="High rewrite waste means revisions are re-emitting the document instead of\nrepairing it: see prompts/generator.md, Generate/Revise Protocol. High\nrequired-read bytes means STATUS.md is carrying closed rows or appended\nhistory that routing no longer needs; archive them.",
)


@dataclass
class SpeedResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def collect_families(workspace: Path) -> dict[str, list[tuple[int, int, Path]]]:
    """Group `*_v<N>.md` artifacts into families keyed by directory + stem.

    Returns {family_key: [(version, size, path), ...]} sorted by version.
    """
    families: dict[str, list[tuple[int, int, Path]]] = {}
    for path in workspace.rglob("*.md"):
        if _skip(path.relative_to(workspace)) or not path.is_file():
            continue
        parsed = version_of(path)
        if not parsed:
            continue
        abs_key, index = parsed
        # version_of keys on the absolute parent; report workspace-relative.
        key = abs_key[len(workspace.as_posix()) + 1 :]
        try:
            size = path.stat().st_size
        except OSError:
            continue
        families.setdefault(key, []).append((index, size, path))
    for versions in families.values():
        versions.sort()
    return {k: v for k, v in families.items() if len(v) >= 2}


def rewrite_waste(families: dict[str, list[tuple[int, int, Path]]]) -> tuple[float, int, int]:
    """Fraction of bytes written that a later version superseded.

    The final version of each family is the product; every earlier version is a
    version of the same document that was paid for and thrown away.
    """
    total = sum(size for versions in families.values() for _, size, _ in versions)
    final = sum(versions[-1][1] for versions in families.values())
    if total == 0:
        return 0.0, 0, 0
    return (total - final) / total, total, final


def monotone_growth(versions: list[tuple[int, int, Path]]) -> bool:
    """True when every revision was larger than the one before it."""
    sizes = [size for _, size, _ in versions]
    return len(sizes) >= 3 and all(b > a for a, b in zip(sizes, sizes[1:]))


def required_read_bytes(workspace: Path) -> tuple[int, dict[str, int]]:
    """Size of the set the Orchestrator re-reads at the start of every round.

    The cookbook says "*latest* review packets", so a versioned artifact
    contributes only its highest version — counting every superseded packet
    would inflate this into the rewrite-waste metric, which is measured
    separately and means something different.
    """
    breakdown: dict[str, int] = {}
    seen: set[Path] = set()
    latest: dict[str, tuple[int, Path]] = {}
    for pattern in REQUIRED_READ_GLOBS:
        for path in sorted(workspace.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            if _skip(path.relative_to(workspace)):
                continue
            seen.add(path)
            parsed = version_of(path)
            if parsed:
                key, index = parsed
                if key not in latest or index > latest[key][0]:
                    latest[key] = (index, path)
                continue
            try:
                breakdown[path.relative_to(workspace).as_posix()] = path.stat().st_size
            except OSError:
                continue
    for _, path in latest.values():
        try:
            breakdown[path.relative_to(workspace).as_posix()] = path.stat().st_size
        except OSError:
            continue
    return sum(breakdown.values()), breakdown


def observed_concurrency(workspace: Path) -> tuple[int, int]:
    """Largest number of distinct lemmas landing generator artifacts in one window.

    Returns (max_concurrent, sample_size). **This is inferred from mtimes, so it
    is only trustworthy when it is LOW.** A run that never gets two lemmas into
    the same window did not batch, and no artefact of the filesystem can fake
    that. A high number proves much less: two agents that genuinely ran together
    but finished 11 minutes apart are counted separately, and — in the other
    direction — extracting an archive, restoring a backup, or any bulk copy
    rewrites every mtime at once and reports concurrency far above the declared
    cap. A value greater than the declared cap means the mtimes are not dispatch
    times; treat it as unmeasured rather than as good news.

    **When `logs/dispatch.jsonl` has real windows, use those instead.** Overlap
    of `[started, ended]` intervals is what concurrency *is*; the mtime count is
    a proxy for it and a poor one. On `testprime` the proxy reported 1 while the
    log showed a peak of 4 — the run had one lemma, so counting lemma landings
    could not see the four specialists that were genuinely in flight together.
    The number the human watched happen was in the log all along.
    """
    from_log = _concurrency_from_log(workspace)
    if from_log is not None:
        return from_log

    landings: list[tuple[float, str]] = []
    lemmas = workspace / "lemmas"
    if lemmas.is_dir():
        for path in lemmas.glob("*/generator/*.md"):
            try:
                landings.append((path.stat().st_mtime, path.parent.parent.name))
            except OSError:
                continue
    landings.sort()
    best = 0
    for start, _ in landings:
        window = {name for when, name in landings if start <= when < start + CONCURRENCY_WINDOW_S}
        best = max(best, len(window))
    return best, len({name for _, name in landings})


def _concurrency_from_log(workspace: Path) -> tuple[int, int] | None:
    """Peak overlap of dispatch windows, and how many dispatches were logged.

    Returns None when fewer than two entries carry a usable window — one
    interval cannot overlap anything, and an empty answer must not be reported
    as concurrency 1.

    Note what this deliberately ignores: the `batch` field. On `testprime` 14 of
    18 dispatches were labelled `batch: "serial"` and **10 of those overlapped
    something**. The label meant "sent individually rather than as a named
    batch", which is not the same as "ran alone" — the cookbook tells the
    Orchestrator to keep dispatching while earlier work is still in flight, so
    individually-sent dispatches overlap by design. Concurrency is a property of
    the clock, never of what a dispatch was called.
    """
    spans = []
    for entry in _dispatch_entries(workspace):
        begin = _parse_stamp(entry.get("started"))
        finish = _parse_stamp(entry.get("ended"))
        if begin is None or finish is None or finish < begin:
            continue
        spans.append((begin, finish))
    if len(spans) < 2:
        return None
    events = [(begin, 1) for begin, _ in spans] + [(finish, -1) for _, finish in spans]
    # Close before open at equal timestamps: a dispatch that ends exactly when
    # the next begins was not concurrent with it.
    events.sort(key=lambda item: (item[0], item[1]))
    live = peak = 0
    for _, delta in events:
        live += delta
        peak = max(peak, live)
    return peak, len(spans)


def _log_provenance(workspace: Path) -> dict:
    """Who wrote the dispatch log, counted by row.

    `dispatch_log.py` stamps `"source": "hook"`, `verify.py` stamps
    `"source": "verify.py"`, and the cookbook asks a Codex orchestrator to stamp
    `"source": "hand"` -- because it has no hook mechanism and must append the
    lines itself. Until this existed, that instruction asked for a field no
    reader consumed, which is the same defect as a rule nothing enforces.

    It matters because the two kinds of row carry different guarantees. A hook
    row is written per dispatch and cannot be forgotten; a hand row can, and is
    -- measured at 5 of 352 on a busy run. A completeness shortfall means
    "the hook is not firing" in one case and "expected under load" in the other,
    and reporting them the same way makes one of the two answers wrong.
    """
    counts: dict[str, int] = {}
    for entry in _dispatch_entries(workspace):
        source = entry.get("source")
        key = source if isinstance(source, str) and source else "unstated"
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return {"known": False, "why": "no dispatch log"}
    return {
        "known": True,
        "counts": counts,
        # An unstated row predates the field or was hand-kept without it. Not an
        # error: the field is younger than most of the corpus.
        "hand_or_unstated": sum(
            n for k, n in counts.items() if k in ("hand", "unstated")
        ),
    }


def _dispatch_entries(workspace: Path) -> list[dict]:
    path = workspace / "logs" / "dispatch.jsonl"
    if not path.is_file():
        return []
    entries = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                entries.append(_normalise_entry(record))
    except OSError:
        return []
    return entries


def _normalise_entry(record: dict) -> dict:
    """Accept the shapes an Orchestrator actually writes, not just the hook's.

    Two schemas exist in the corpus and neither was invented here. The hook
    writes `started`/`ended`/`target`. Orchestrators keeping the log by hand
    have written `end` + `duration_s` (the window backwards from its close) and
    `output` instead of `target`, and a scalar `tokens` total rather than the
    four-way split.

    Reading only one shape is how this gate reported *"18 of 18 dispatches
    produced no artifact"* for a run in which every dispatch produced its file:
    it could not see `output`, so it fell back to window attribution, and it
    could not see the window either. **A parser that silently declines to
    understand a record scores it as a failure of the run.**
    """
    entry = dict(record)
    if not entry.get("target") and isinstance(entry.get("output"), str):
        entry["target"] = entry["output"]
    if not entry.get("ended") and isinstance(entry.get("end"), str):
        entry["ended"] = entry["end"]
    if not entry.get("started"):
        finish = _parse_stamp(entry.get("ended"))
        duration = entry.get("duration_s")
        if finish is not None and isinstance(duration, (int, float)) and duration > 0:
            entry["started"] = (
                datetime.fromtimestamp(finish - duration, tz=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
    tokens = entry.get("tokens")
    if isinstance(tokens, (int, float)):
        # A scalar total cannot be split into in/out/cache, and inventing a
        # split would be worse than recording that only the total is known.
        entry["tokens"] = {"total": int(tokens)}
    return entry


def _parse_stamp(value: object) -> float | None:
    """An ISO-8601 UTC stamp as seconds since the epoch, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _duration_s(entry: dict) -> float | None:
    """Seconds between `started` and `ended`, when both parse as ISO-8601 UTC."""
    begin = _parse_stamp(entry.get("started"))
    finish = _parse_stamp(entry.get("ended"))
    if begin is None or finish is None:
        return None
    seconds = finish - begin
    return seconds if seconds > 0 else None


def stalled_dispatches(workspace: Path) -> dict[str, object]:
    """Dispatches that were paid for and produced nothing.

    These are the expensive failures and the only ones no amount of looking at
    the workspace can find: a stalled owner leaves no artifact, so the run's
    file tree shows a gap and nothing else. Only `logs/dispatch.jsonl` records
    that a dispatch happened at all.

    A stall is a logged dispatch whose `target` does not exist on disk **and
    which was not deliberately discarded**. A losing shadow also leaves no
    artifact, by design — it is insurance that went unclaimed, not a failure.
    Counting the two together makes a healthy run look like it wasted a third
    of its dispatches, which is exactly what this gate reported on `newtestc`
    before the distinction existed. `result` is what separates them, so a
    dispatch log without a `result` field cannot tell the two apart and its
    losing shadows will be counted as stalls.

    Entries written by `.claude/hooks/dispatch_log.py` carry no `target` at all,
    deliberately: the hook records the window a dispatch ran in and leaves
    attribution to `_produced_in_window`, which reads mtimes. A guessed target
    parsed out of prose fails silently in the flattering direction; an empty
    window is checkable.
    """
    entries = _dispatch_entries(workspace)
    if not entries:
        return {"known": False}
    stamps = _artifact_stamps(workspace)
    missing = []
    discarded = []
    unattributable = 0
    for entry in entries:
        target = entry.get("target")
        result = entry.get("result")
        if isinstance(target, str) and target:
            if _target_exists(workspace, target):
                continue
            record = {"role": entry.get("role"), "target": target}
        else:
            produced = _produced_in_window(entry, stamps)
            if produced is None:
                unattributable += 1
                continue
            if produced:
                continue
            record = {"role": entry.get("role"), "target": "(window: nothing landed)"}
        if isinstance(result, str) and "discard" in result.lower():
            discarded.append(record)
        else:
            missing.append(record)
    return {
        "known": True,
        "dispatches": len(entries),
        "produced_nothing": len(missing),
        "discarded_by_design": len(discarded),
        "unattributable": unattributable,
        "examples": missing[:DEFAULT_TOP_N],
    }


def _target_exists(workspace: Path, target: str) -> bool:
    """Did any file this dispatch claimed to write actually land?

    A hand-written target is prose, not a path. Real entries in the corpus:

        "computation/*.c, computation/*.txt"
        "sketch/plan.md, lemmas/reduction/statement.md"
        "accepted readings of TestPrime.pdf"

    So: split on commas, glob what has a wildcard, and treat a comma-list as
    satisfied when **any** member exists — a dispatch that wrote three of its
    four files stalled on none of them.

    A target with no path separator and no extension is a description rather
    than a filename; it cannot be checked and must not be scored as missing.
    That misreading is what produced *"18 of 18 dispatches produced no
    artifact"* on a run where all 18 delivered.
    """
    checkable = False
    for part in (piece.strip() for piece in target.split(",")):
        if not part:
            continue
        if "/" not in part and "." not in part:
            continue  # prose, not a path
        checkable = True
        if any(char in part for char in "*?["):
            try:
                if next(workspace.glob(part), None) is not None:
                    return True
            except (ValueError, OSError):
                continue
        elif (workspace / part).exists():
            return True
    # Nothing was checkable — unknown, and unknown is not "missing".
    return not checkable


def _artifact_stamps(workspace: Path) -> list[float]:
    """mtimes of every artifact a dispatch could have produced, seconds since epoch."""
    stamps = []
    for path in workspace.rglob("*.md"):
        relative = path.relative_to(workspace)
        if _skip(relative) or relative.parts[0] == "logs":
            continue
        try:
            stamps.append(path.stat().st_mtime)
        except OSError:
            continue
    return sorted(stamps)


def _produced_in_window(entry: dict, stamps: list[float]) -> int | None:
    """How many artifacts landed while this dispatch was running.

    `None` means the question cannot be asked — no usable timestamps, so the
    dispatch is neither a stall nor a success and is counted as unattributable
    rather than folded into either. A run whose whole log is unattributable
    must not read as a run with no stalls.

    The window is closed at both ends and widened by a grace period, because a
    subagent's last write lands a moment before the tool call returns and
    filesystem mtime resolution is coarser than the log's one-second stamps.
    """
    begin = _parse_stamp(entry.get("started"))
    finish = _parse_stamp(entry.get("ended"))
    if begin is None or finish is None or entry.get("duration_unknown"):
        return None
    grace = 2.0
    return sum(1 for stamp in stamps if begin - grace <= stamp <= finish + grace)


def unsplit_chains(workspace: Path) -> dict[str, object]:
    """Lemmas that kept revising past the point where splitting was cheaper.

    Widening the DAG cannot take a run below its worst lemma's revision chain.
    On the 26-hour run that chain was 11 rounds and 7.9 hours for one lemma, so
    perfect lemma-level parallelism would still have left 7.9 hours on the
    clock. The chain is the only thing left to attack past ~3x.

    A chain is reported when it passed the split threshold **and did not
    converge** — successive versions the same size or larger. Convergence is the
    legitimate case: an artifact that is shrinking as blocking issues narrow is
    finishing, and interrupting it to re-decompose would throw away the work.
    """
    families = collect_families(workspace)
    long_chains = []
    for key, versions in sorted(families.items()):
        # The directory must *be* `generator`, not merely start with it:
        # `logs/generator_<lemma>_v3.md` is a dispatch note, not a proof attempt,
        # and splitting a lemma because its log file has many versions is advice
        # about the wrong object.
        directory = key.rsplit("/", 1)[0] if "/" in key else ""
        if directory == "logs" or directory.startswith("logs/"):
            continue
        if not directory.endswith("/generator") or len(versions) <= SPLIT_THRESHOLD:
            continue
        ordered = [size for _, size, _ in sorted(versions)]
        # Converging = the tail is getting smaller. Compare the last two.
        converging = ordered[-1] < ordered[-2]
        if converging:
            continue
        long_chains.append(
            {
                "family": key,
                "versions": len(ordered),
                "first_kb": ordered[0] // 1024,
                "last_kb": ordered[-1] // 1024,
            }
        )
    return {
        "known": True,
        "threshold": SPLIT_THRESHOLD,
        "chains": sorted(long_chains, key=lambda item: -item["versions"]),
    }


SPLIT_THRESHOLD = 3


def platform_mix(workspace: Path) -> dict[str, object]:
    """Which platform ran each dispatch.

    **A workspace is not a platform.** `newtestb` was worked by 5 Claude Code
    sessions and 12 Codex ones; `newtestc` by 38 Codex sessions and no Claude
    ones. Any conclusion drawn by comparing two workspaces without this is
    comparing two models while believing it is comparing two configurations.

    Only hook-written entries can state their platform. A log of hand-written
    entries reports `unstated`, which is the honest answer and not `mixed`.
    """
    entries = _dispatch_entries(workspace)
    if not entries:
        return {"known": False}
    counts: dict[str, int] = {}
    for entry in entries:
        platform = entry.get("platform")
        key = platform if isinstance(platform, str) and platform else "unstated"
        counts[key] = counts.get(key, 0) + 1
    stated = {name: total for name, total in counts.items() if name != "unstated"}
    return {
        "known": True,
        "counts": counts,
        "mixed": len(stated) > 1,
        "unstated": counts.get("unstated", 0),
    }


def token_cost(workspace: Path) -> dict[str, object]:
    """What the run actually cost, in tokens, from the hook's per-dispatch record.

    Cache reads are kept separate from fresh input on purpose. On a real session
    they ran 225M against 1.4M output — a 160:1 ratio — so folding them into one
    "tokens" number makes every run look enormous and hides the only thing worth
    acting on: `cache_read` is the per-round required-read set being paid for
    again on every round, which is what `required_read_bytes` measures in bytes
    and this measures in the unit that is billed.
    """
    entries = _dispatch_entries(workspace)
    if not entries:
        return {"known": False}
    totals = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "total": 0}
    counted = 0
    for entry in entries:
        tokens = entry.get("tokens")
        if not isinstance(tokens, dict):
            continue
        counted += 1
        for key in totals:
            value = tokens.get(key)
            if isinstance(value, (int, float)):
                totals[key] += int(value)
    # A hand-kept log records one total per dispatch; the hook records the split.
    # Report whichever is present rather than printing zeros for the other.
    split_known = any(totals[key] for key in ("in", "out", "cache_read", "cache_write"))
    if not counted:
        return {"known": False, "dispatches": len(entries)}
    return {
        "known": True,
        "dispatches": len(entries),
        "with_tokens": counted,
        "totals": totals,
        "split_known": split_known,
        # Reading dwarfs writing, so this ratio is the token story in one number.
        "read_write_ratio": (
            totals["cache_read"] / totals["out"] if totals["out"] else None
        ),
    }


def prompt_shape(workspace: Path) -> dict[str, object]:
    """What shape the dispatch prompts had, from the hook's `prompt_shape` field.

    ADR 0003 and `prompts/verifier.md` state a contract about what a
    verification dispatch may contain: no prior verdict, no Generator account of
    its own work, a named budget, a stopping condition. Until the hook recorded
    prompt shape, nothing in the harness could see whether it held — the 84%
    violation figure behind the contract came from hand-parsing session
    transcripts, which is not a measurement that gets repeated.

    Percentages are over **verifier** records only, because the contract's
    thresholds are stated over verifier dispatches. The length spread is over
    all roles: it is a symptom of dispatch discipline generally, not of one
    role's contract.

    **A log with no `prompt_shape` on any record returns `known: False`, and the
    caller must say so rather than print 0%.** Every hand-kept log in the corpus
    predates the field, and "0% anchored" is the exact opposite of what those
    runs did. An unrecorded event is unmeasured, never clean.

    **`known: False` has two causes and they are not the same fact.** The hook
    writes `prompt_shape` as a dict of booleans; the hand-kept convention writes
    it as a hyphenated string (`...-budget-no-prior-verdict`). Only the dict can
    be scored against the contract's four booleans, so a string-form log is
    still `known: False` — but reporting it as "no record carries prompt_shape"
    is a false statement about the data, and it cost a reviewer a wrong reading:
    63 of 63 records carried the field and the gate said none did. `form` names
    which case it is, and `with_text_shape` counts what was set aside. Not
    parsed into booleans: a substring match on free text would fail silently in
    the flattering direction, which is the failure this whole module is written
    against.
    """
    entries = _dispatch_entries(workspace)
    shapes = [
        (entry.get("role"), entry["prompt_shape"])
        for entry in entries
        if isinstance(entry.get("prompt_shape"), dict)
    ]
    if not shapes:
        text_shapes = [
            entry for entry in entries
            if isinstance(entry.get("prompt_shape"), str) and entry["prompt_shape"].strip()
        ]
        if text_shapes:
            return {
                "known": False,
                "form": "text",
                "dispatches": len(entries),
                "with_text_shape": len(text_shapes),
                "verifier_records": sum(1 for e in text_shapes if e.get("role") == "verifier"),
            }
        return {"known": False, "form": "absent", "dispatches": len(entries)}

    verifier = [shape for role, shape in shapes if role == "verifier"]

    def _count(key: str) -> int:
        return sum(1 for shape in verifier if shape.get(key) is True)

    anchored = sum(
        1
        for shape in verifier
        if shape.get("generator_framing") is True or shape.get("prior_verdict") is True
    )
    lengths = [
        shape.get("chars")
        for _role, shape in shapes
        if isinstance(shape.get("chars"), int) and shape.get("chars") > 0
    ]
    spread = round(max(lengths) / min(lengths), 1) if len(lengths) >= 2 else None
    return {
        "known": True,
        "dispatches": len(entries),
        "with_shape": len(shapes),
        "verifier_records": len(verifier),
        "anchored": anchored,
        "budget": _count("budget"),
        "stopping_condition": _count("stopping_condition"),
        "freshness_claim": _count("freshness_claim"),
        "length_spread": spread,
        "chars_max": max(lengths) if lengths else None,
        "chars_min": min(lengths) if lengths else None,
    }


def plan_width(workspace: Path) -> dict[str, object]:
    """Whether the plan declared how much of itself can run at once.

    The Orchestrator dispatches from the decomposition, so the decomposition's
    shape sets the run's floor: a plan drawn as a chain is dispatched as a
    chain no matter what the lemmas would have supported. Of the two runs that
    could be compared, the one whose decomposition named its parallel roots hit
    six concurrent specialists; the one that named none hit one.

    This reports the fact, not a judgement. A genuine chain is a legitimate
    plan — what is not legitimate is leaving the reader to infer width from a
    drawing, which is how a schedulable plan gets walked one lemma at a time.
    """
    plans = sorted((workspace / "sketch").glob("decomposition*.md")) if (
        workspace / "sketch"
    ).is_dir() else []
    if not plans:
        return {"known": False}
    declared = []
    for plan in plans:
        try:
            text = plan.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        declared.append(
            {
                "plan": plan.name,
                "frontier": "parallel frontier" in lowered,
                # Two workspaces stated their frontier before any rule asked for
                # one, in their own words: "dispatchable immediately, in
                # parallel" and "dispatchable immediately, no unresolved
                # dependencies". Matching only the heading scored the second as
                # silent even though it reached six concurrent specialists.
                # What matters is whether the information is there.
                "parallel_roots": any(
                    phrase in lowered
                    for phrase in ("in parallel", "dispatchable immediately", "dispatchable now")
                ),
            }
        )
    if not declared:
        return {"known": False}
    return {
        "known": True,
        "plans": declared,
        "silent": [
            entry["plan"]
            for entry in declared
            if not entry["frontier"] and not entry["parallel_roots"]
        ],
    }


def shadow_overhead(workspace: Path) -> dict[str, object]:
    """How many dispatches were shadows, and how many of them were ever adopted.

    The shadow rule buys latency by spending a dispatch: on a stall the shadow
    lands while the escalation ladder would still be polling. It only pays when
    a shadow is sometimes *adopted*. A run where every dispatch has a shadow and
    no shadow ever wins has not bought latency — it has doubled its dispatch
    count for nothing, which is what `newtestc` did (18 shadows, 18 discarded,
    peak concurrency 2 and that 2 was always a primary and its own shadow).

    A shadow is identified by `_shadow` in `target` or `shadow` in `batch`;
    adoption is the absence of a discard `result`.
    """
    entries = _dispatch_entries(workspace)
    if not entries:
        return {"known": False}
    shadows = [
        entry
        for entry in entries
        if "_shadow" in str(entry.get("target", ""))
        or "shadow" in str(entry.get("batch") or "")
    ]
    adopted = [
        entry
        for entry in shadows
        if "discard" not in str(entry.get("result") or "").lower()
    ]
    return {
        "known": True,
        "dispatches": len(entries),
        "shadows": len(shadows),
        "adopted": len(adopted),
    }


def batch_spread(workspace: Path) -> dict[str, object]:
    """ADR 0024 §3.A3: a batch of N same-role specialists ran concurrently iff
    the spread of their artifact landings is below one agent's median turnaround.

    The window count above answers "how many could have been in flight"; this
    answers "did they actually go out together". A batch dispatched as a batch
    lands inside one agent's turnaround, because they were all working at once.
    A batch walked one at a time lands spread across N turnarounds. Verified on
    a workspace whose one documented parallel pair landed 23 seconds apart while
    its serial batches averaged 8 minutes between members.

    **Turnaround must come from `logs/dispatch.jsonl`, and this returns
    `known: False` without it.** Estimating turnaround from the gaps between
    artifacts is circular: when a run is one big batch, those gaps *are* the
    batch's internal spread, so the estimate shrinks to match whatever it is
    measuring and every batch looks serial. An unmeasurable quantity is reported
    as unmeasured; it is not approximated into a number that reads like a verdict.
    """
    entries = _dispatch_entries(workspace)
    durations = [d for d in (_duration_s(e) for e in entries) if d is not None]
    if len(durations) < 3:
        return {"known": False, "reason": "needs logs/dispatch.jsonl with >=3 timed dispatches"}
    durations.sort()
    turnaround = durations[len(durations) // 2]

    landings: list[tuple[float, str]] = []
    lemmas = workspace / "lemmas"
    if lemmas.is_dir():
        for path in lemmas.glob("*/generator/*.md"):
            try:
                landings.append((path.stat().st_mtime, path.parent.parent.name))
            except OSError:
                continue
    landings.sort()
    if not landings:
        return {"known": False, "reason": "no generator artifacts"}
    # Largest group of distinct lemmas landing inside one turnaround.
    # Strictly less than one turnaround: artifacts spaced exactly a turnaround
    # apart are the textbook serial case and must not read as a batch.
    widest, spread = 0, 0.0
    for start, _ in landings:
        members = [when for when, _n in landings if start <= when < start + turnaround]
        group = {name for when, name in landings if start <= when < start + turnaround}
        if len(group) > widest:
            widest, spread = len(group), max(members) - min(members)
    return {
        "known": True,
        "widest_real_batch": widest,
        "median_turnaround_s": round(turnaround, 1),
        "spread_s": round(spread, 1),
        "concurrent": widest >= 2,
    }


def status_hygiene(workspace: Path) -> dict[str, object]:
    """Is STATUS.md still carrying what routing does not read?"""
    status = workspace / "STATUS.md"
    if not status.is_file():
        return {"present": False}
    try:
        text = status.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"present": False}
    lines = text.splitlines()
    history = sum(1 for line in lines if line.strip().lower().startswith("## history"))
    closed = 0
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().strip("`").lower() for c in stripped.strip("|").split("|")]
        if any(cell in ARCHIVABLE_STATUSES for cell in cells):
            closed += 1
    headings = [line.strip()[3:].strip().lower() for line in lines if line.strip().startswith("## ")]
    matched = sum(1 for name in TEMPLATE_SECTIONS if any(h.startswith(name) for h in headings))
    return {
        "present": True,
        "bytes": status.stat().st_size,
        "has_history_section": history > 0,
        "closed_rows": closed,
        "template_sections": matched,
        "template_total": len(TEMPLATE_SECTIONS),
        "sections": len(headings),
    }


def lint_workspace(
    workspace: Path,
    *,
    read_budget_kb: int = DEFAULT_READ_BUDGET_KB,
    waste_ratio: float = DEFAULT_WASTE_RATIO,
) -> SpeedResult:
    result = SpeedResult()
    workspace = Path(workspace)
    if not workspace.is_dir():
        result.ok = False
        result.errors.append(f"workspace not found: {workspace}")
        return result

    families = collect_families(workspace)
    waste, total, final = rewrite_waste(families)
    read_bytes, breakdown = required_read_bytes(workspace)

    growing = sorted(
        (
            (versions[-1][1] - versions[0][1], key, len(versions), versions[0][1], versions[-1][1])
            for key, versions in families.items()
            if monotone_growth(versions)
        ),
        reverse=True,
    )
    expensive = sorted(
        (
            (sum(s for _, s, _ in versions), key, len(versions), versions[-1][1])
            for key, versions in families.items()
        ),
        reverse=True,
    )[:DEFAULT_TOP_N]

    concurrency, sample_size = observed_concurrency(workspace)
    # Measured from dispatch windows when the log has them, from lemma landings
    # otherwise. The two count different things, so the label has to follow.
    measured_from_log = _concurrency_from_log(workspace) is not None
    batch = batch_spread(workspace)
    stalls = stalled_dispatches(workspace)
    shadows = shadow_overhead(workspace)
    width = plan_width(workspace)
    platforms = platform_mix(workspace)
    shapes = prompt_shape(workspace)
    tokens = token_cost(workspace)
    chains = unsplit_chains(workspace)
    hygiene = status_hygiene(workspace)
    has_dispatch_log = (workspace / "logs" / "dispatch.jsonl").is_file()
    dispatch_lines = 0
    if has_dispatch_log:
        try:
            dispatch_lines = sum(
                1
                for line in (workspace / "logs" / "dispatch.jsonl").read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
                if line.strip()
            )
        except OSError:
            dispatch_lines = 0
    # Every artifact took at least one dispatch, so artifacts are a lower bound on
    # dispatches. Dispatches that produced nothing are exactly the expensive ones,
    # so a log with fewer lines than artifacts is provably missing entries.
    artifact_count = sum(
        1
        for path in workspace.rglob("*.md")
        if not _skip(path.relative_to(workspace))
        and path.parent.name in ("generator", "verifier")
    )

    result.metrics = {
        "observed_concurrency": concurrency,
        "batch_spread": batch,
        "stalled_dispatches": stalls,
        "shadow_overhead": shadows,
        "plan_width": width,
        "platform_mix": platforms,
        "prompt_shape": shapes,
        "token_cost": tokens,
        "unsplit_chains": chains,
        "declared_concurrency": DECLARED_CONCURRENCY,
        "sample_size": sample_size,
        "concurrency_source": "dispatch log" if measured_from_log else "lemma mtimes",
        "status_hygiene": hygiene,
        "has_dispatch_log": has_dispatch_log,
        "dispatch_lines": dispatch_lines,
        "log_provenance": _log_provenance(workspace),
        "lane_artifacts": artifact_count,
        "families": len(families),
        "bytes_written": total,
        "bytes_final": final,
        "rewrite_waste_ratio": round(waste, 4),
        "required_read_bytes": read_bytes,
        "required_read_breakdown": breakdown,
        "monotone_growth_families": [
            {"family": key, "versions": n, "first": a, "last": b}
            for _, key, n, a, b in growing[:DEFAULT_TOP_N]
        ],
        "most_expensive_families": [
            {"family": key, "versions": n, "written": w, "final": f}
            for w, key, n, f in expensive
        ],
    }

    if waste > waste_ratio:
        result.warnings.append(
            f"rewrite waste {waste:.0%} of {total // 1024} KB written is superseded "
            f"(threshold {waste_ratio:.0%}) — revisions are re-emitting documents, not repairing them"
        )
    if read_bytes > read_budget_kb * 1024:
        biggest = max(breakdown.items(), key=lambda kv: kv[1], default=("", 0))
        result.warnings.append(
            f"required-read set is {read_bytes // 1024} KB (budget {read_budget_kb} KB); "
            f"largest is {biggest[0]} at {biggest[1] // 1024} KB — archive what routing no longer needs"
        )
    for _, key, n, a, b in growing[:DEFAULT_TOP_N]:
        result.warnings.append(
            f"{key}: grew every revision, {a // 1024} KB -> {b // 1024} KB over {n} versions"
        )

    # Only meaningful once there were enough independent lemmas to batch at all.
    if stalls.get("known") and stalls.get("produced_nothing"):
        result.warnings.append(
            f"{stalls['produced_nothing']} of {stalls['dispatches']} logged dispatch(es) produced "
            f"no artifact — these are paid for in full and are invisible in the file tree. "
            f"Send a shadow owner on the first missed checkpoint rather than running an "
            f"escalation ladder (orchestrator-cookbook.md)"
        )
    # A shadow is insurance. Insurance that never pays out and is bought on every
    # single dispatch is not insurance, it is a doubled dispatch count. Warn only
    # when both hold: near-universal shadowing AND no shadow ever adopted.
    if shadows.get("known") and shadows.get("shadows"):
        primaries = shadows["dispatches"] - shadows["shadows"]
        if shadows["adopted"] == 0 and primaries and shadows["shadows"] >= primaries * 0.5:
            result.warnings.append(
                f"{shadows['shadows']} of {shadows['dispatches']} dispatches were shadows and "
                f"none was ever adopted — a shadow is for a missed checkpoint, not for every "
                f"dispatch. Dispatch it only after the primary has passed its role's median "
                f"turnaround (orchestrator-cookbook.md)"
            )
    for chain in chains.get("chains", [])[:DEFAULT_TOP_N]:
        result.warnings.append(
            f"{chain['family']}: {chain['versions']} revisions and still not converging "
            f"({chain['first_kb']} KB -> {chain['last_kb']} KB). Past revision "
            f"{chains['threshold']} the cheaper move is to split the lemma and prove the "
            f"pieces in parallel — a revision chain is the one thing a wider DAG cannot "
            f"shorten (orchestrator-cookbook.md)"
        )
    if platforms.get("known") and platforms.get("mixed"):
        shown = ", ".join(f"{name} {count}" for name, count in sorted(platforms["counts"].items()))
        result.warnings.append(
            f"this workspace was worked by more than one platform ({shown}) — every number "
            f"above mixes them, so do not read a difference between two workspaces as a "
            f"difference between two configurations without splitting by platform first"
        )
    if width.get("known") and width.get("silent"):
        result.warnings.append(
            f"{', '.join(width['silent'])} draws a DAG but never says how much of it can run "
            f"at once — the Orchestrator dispatches from this file, and an unstated frontier "
            f"is dispatched as a chain. Add '## Parallel Frontier' (prompts/sketcher.md)"
        )
    if batch.get("known") and not batch.get("concurrent"):
        result.warnings.append(
            f"no real batch (ADR 0024 A3): the widest group of lemmas landing inside one "
            f"agent's median turnaround ({batch['median_turnaround_s'] / 60:.1f} min) is "
            f"{batch['widest_real_batch']} — specialists are going out one at a time"
        )
    if concurrency > DECLARED_CONCURRENCY and not measured_from_log:
        result.warnings.append(
            f"observed concurrency {concurrency} exceeds the declared cap of {DECLARED_CONCURRENCY} "
            f"— artifact mtimes are not dispatch times here (an archive extraction or bulk copy "
            f"rewrites them all at once). Treat concurrency as unmeasured for this workspace"
        )
    elif sample_size >= 2 and concurrency < 2:
        subject = "dispatches" if measured_from_log else "lemmas"
        result.warnings.append(
            f"observed concurrency {concurrency} across {sample_size} {subject} — nothing ever "
            f"overlapped anything; declared capacity is {DECLARED_CONCURRENCY}, so independent "
            f"work is going out one at a time"
        )
    if hygiene.get("present") and hygiene.get("sections", 0) > DRIFT_SECTION_LIMIT:
        result.warnings.append(
            f"STATUS.md has {hygiene['sections']} sections but only "
            f"{hygiene['template_sections']}/{hygiene['template_total']} of the routing shape "
            f"(prompts/references/status-and-recovery.md) — it has drifted into a narrative "
            f"file, and every section in it is re-read at the start of every round"
        )
    if hygiene.get("has_history_section"):
        result.warnings.append(
            "STATUS.md still carries the append-only '## History' section — it is re-read every "
            "round and routing does not use it; move it to STATUS_history.md"
        )
    if hygiene.get("closed_rows", 0) > 0:
        result.warnings.append(
            f"STATUS.md carries {hygiene['closed_rows']} branch row(s) already at "
            f"{'/'.join(ARCHIVABLE_STATUSES)} — archive them to STATUS_closed.md"
        )
    if not has_dispatch_log:
        result.warnings.append(
            "no logs/dispatch.jsonl — dispatch count, roles, and durations are unrecoverable, "
            "so concurrency above is a floor inferred from artifact mtimes, not a measurement"
        )
    elif dispatch_lines < artifact_count:
        result.warnings.append(
            f"logs/dispatch.jsonl has {dispatch_lines} entries but there are {artifact_count} "
            f"generator/verifier artifacts — at least {artifact_count - dispatch_lines} dispatch(es) "
            f"went unlogged, and dispatches that produced no artifact are missing on top of that. "
            f"Treat the log as incomplete rather than as a measurement"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report what a run cost itself: rewrite waste, artifact accretion, per-round required-read bytes.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", type=Path, help="Problem workspace to measure.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when a threshold is exceeded. Off by default: this gate reports, it does not block a run.",
    )
    parser.add_argument(
        "--read-budget",
        type=int,
        default=DEFAULT_READ_BUDGET_KB,
        metavar="KB",
        help=f"Per-round required-read budget in KB (default {DEFAULT_READ_BUDGET_KB}).",
    )
    parser.add_argument(
        "--waste-ratio",
        type=float,
        default=DEFAULT_WASTE_RATIO,
        metavar="R",
        help=f"Superseded-bytes fraction that triggers a warning (default {DEFAULT_WASTE_RATIO}).",
    )
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_workspace(
        args.workspace,
        read_budget_kb=args.read_budget,
        waste_ratio=args.waste_ratio,
    )

    # Waive before reporting. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` listed errors the waiver
    # had already excused and carried an `ok` that disagreed with the
    # human output on the same run. The two views are one computation.
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="speed", workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "metrics": result.metrics,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        metrics = result.metrics
        print(f"speed_gate: {args.workspace}")
        if metrics:
            print(
                f"  versioned families      {metrics['families']}"
                f"  written {metrics['bytes_written'] // 1024} KB"
                f"  final {metrics['bytes_final'] // 1024} KB"
            )
            print(f"  rewrite waste           {metrics['rewrite_waste_ratio']:.0%}")
            print(f"  required-read set       {metrics['required_read_bytes'] // 1024} KB")
            print(
                f"  observed concurrency    {metrics['observed_concurrency']}"
                f" of {metrics['declared_concurrency']} declared"
                f"  (from {metrics['concurrency_source']}, n={metrics['sample_size']})"
            )
            hyg = metrics["status_hygiene"]
            if hyg.get("present"):
                print(
                    f"  STATUS.md               {hyg['bytes'] // 1024} KB,"
                    f" {hyg['sections']} sections,"
                    f" {hyg['template_sections']}/{hyg['template_total']} of the routing shape"
                )
            print(
                f"  dispatch log {'yes' if metrics['has_dispatch_log'] else 'no'}"
            )
            mix = metrics["platform_mix"]
            if mix.get("known"):
                shown = ", ".join(f"{name} {count}" for name, count in sorted(mix["counts"].items()))
                print(f"  platform                {shown}")
            shape = metrics["prompt_shape"]
            if shape.get("known"):
                print(
                    f"  dispatch prompt shape   n={shape['with_shape']}"
                    f" of {shape['dispatches']} records"
                )

                def _pct(count: int) -> str:
                    total = shape["verifier_records"]
                    if not total:
                        return "n/a (no verifier records)"
                    return f"{count} ({count / total:.0%})"

                print(f"    anchored, verifier (generator framing or prior verdict)   "
                      f"{_pct(shape['anchored'])}")
                print(f"    names a budget, verifier                                  "
                      f"{_pct(shape['budget'])}")
                print(f"    names a stopping condition, verifier                      "
                      f"{_pct(shape['stopping_condition'])}")
                spread = shape["length_spread"]
                print(f"    length spread max/min, all roles                          "
                      f"{f'{spread}x' if spread is not None else 'n/a (one record)'}")
            elif shape.get("form") == "text":
                # The field is there. It is the hand-kept string convention,
                # which carries the same intent and cannot be scored against
                # four booleans. Say which of the two facts this is: "no record
                # carries it" was reported for a log where every record did.
                print(
                    f"  dispatch prompt shape   {shape['with_text_shape']} of "
                    f"{shape['dispatches']} records carry prompt_shape as free text\n"
                    "                          (the hand-kept convention), not as the hook's "
                    "booleans, so the\n"
                    "                          contract cannot be scored from it. "
                    "This is not 0% and not absent."
                )
            else:
                # NOT zero. A hand-kept log has no such field, and printing
                # "0% anchored" for a run nobody classified reports the exact
                # opposite of what those runs did.
                print(
                    "  dispatch prompt shape   unmeasured — no record carries prompt_shape "
                    "(log predates\n"
                    "                          the field or was kept by hand). "
                    "This is not 0%."
                )
            cost = metrics["token_cost"]
            if cost.get("known"):
                totals = cost["totals"]
                ratio = cost["read_write_ratio"]
                if cost.get("split_known"):
                    body = (
                        f"in {totals['in'] / 1000:.0f}k"
                        f"  out {totals['out'] / 1000:.0f}k"
                        f"  cache-read {totals['cache_read'] / 1000:.0f}k"
                        f"  cache-write {totals['cache_write'] / 1000:.0f}k"
                        + (f"   (read/write {ratio:.0f}:1)" if ratio else "")
                    )
                else:
                    body = f"{totals['total'] / 1000:.0f}k total (log records no split)"
                print(
                    f"  tokens                  {body}"
                    f"   [{cost['with_tokens']}/{cost['dispatches']} dispatches]"
                )
            for item in metrics["most_expensive_families"]:
                print(
                    f"    {item['family']}: {item['versions']} versions, "
                    f"{item['written'] // 1024} KB written for a {item['final'] // 1024} KB result"
                )
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")

    if not args.json:
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        # Not under --json: the epilogue is prose, and printing prose after a
        # JSON document makes the document unparseable exactly when it carries
        # something to report. Six of the ten gates did this; only the ones that
        # happened to pass on the workspace they were tried against looked healthy.
        print()
        print(REQUIREMENT)
    # The verdict is not part of that. It used to sit inside the block above, so
    # `--json` — the mode a script runs — reported `"ok": false` and exited 0, while
    # the same workspace in text mode exited 1. A gate whose answer depends on how it
    # was asked to print is not a gate.
    if result.errors:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
