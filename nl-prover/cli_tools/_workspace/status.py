"""Where a run stands, on one page.

Built from what every run actually has, which is a much shorter list than it
looks: `gate dag --json` (the proof graph), `gate speed --json` (what it cost),
`STATUS.md` size and mtime, and the file tree. `logs/dispatch.jsonl` is NOT a
source: it exists in 6 of 54 run roots, in four mutually incompatible
hand-written schemas, and in the one workspace that has it the rows undercount
activity by 4.4x. A page whose numbers appear on a tenth of runs is not a page.

Two rules the whole module is shaped around.

**Every absent field says why it is absent.** Nothing prints `0` for something
it could not measure. This harness has already lost months to a metric reading
0.0 because a parser silently decoded nothing, and a dashboard is the point where
that lie reaches a person, not a log.

**Nothing is invented.** Four things a reader obviously wants -- a run-level
phase, a last-progress timestamp, a machine-readable current focus, and cost --
are recorded by no file anywhere. They are printed as missing, by name. A page
that quietly omits what it cannot answer teaches the reader that the question
was not worth asking.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gate import dag as dag_gate  # noqa: E402
from _gate import speed as speed_gate  # noqa: E402


HOUR = 3600.0

# A run root is a directory holding a STATUS.md. It is NOT a top-level directory
# under the workspace tree: ESConjecture/ alone holds 22 of the corpus's 54.
RUN_MARKER = "STATUS.md"

# Liveness, from the newest artifact under lemmas/ and verification/. The slack
# is wide on purpose. A round in this harness legitimately runs for tens of
# minutes and the human legitimately walks away for a day, so a label that fires
# early is a label the reader learns to ignore.
FRESH_H = 2.0
QUIET_H = 12.0

MISSING = {
    "phase": "no file records a run-level phase",
    "last_progress": "derived from artifact mtimes; no file records it",
    "current_focus": "no file records what the run is working on right now",
    "cost": "no run records tokens or spend; bytes written is the only proxy",
}


def run_roots(root: Path) -> list[Path]:
    """Every directory below `root` that holds a STATUS.md, `root` included."""
    found = []
    if (root / RUN_MARKER).is_file():
        found.append(root)
    for path in sorted(root.rglob(RUN_MARKER)):
        directory = path.parent
        if directory != root:
            found.append(directory)
    return found


def _newest(workspace: Path, *relatives: str) -> tuple[float | None, Path | None]:
    newest_at: float | None = None
    newest_path: Path | None = None
    for relative in relatives:
        base = workspace / relative
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                at = path.stat().st_mtime
            except OSError:
                continue
            if newest_at is None or at > newest_at:
                newest_at, newest_path = at, path
    return newest_at, newest_path


def _age(seconds: float) -> str:
    if seconds < HOUR:
        return f"{seconds / 60:.0f}m"
    if seconds < 48 * HOUR:
        return f"{seconds / HOUR:.1f}h"
    return f"{seconds / (24 * HOUR):.0f}d"


def liveness(workspace: Path, now: float) -> dict:
    at, path = _newest(workspace, "lemmas", "verification", "verifier", "sketch",
                       "recovery", "routes", "writer", "logs")
    # STATUS.md counts. A run can be worked entirely through it -- one in the
    # corpus has a 472-line, 26 KB STATUS.md and nothing under the directories
    # above, and read as `empty`, i.e. never started.
    status = workspace / RUN_MARKER
    if status.is_file():
        try:
            status_at = status.stat().st_mtime
            if at is None or status_at > at:
                at, path = status_at, status
        except OSError:
            pass
    if at is None:
        return {
            "label": "empty",
            "why": "no STATUS.md and no artifact under any run directory",
        }
    idle = max(now - at, 0.0)
    if idle < FRESH_H * HOUR:
        label = "working"
    elif idle < QUIET_H * HOUR:
        label = "quiet"
    else:
        label = "idle"
    return {
        "label": label,
        "idle_seconds": round(idle),
        "idle": _age(idle),
        "newest_artifact": str(path.relative_to(workspace)) if path else None,
        "why": (
            "from artifact mtimes, not from a recorded event: a copy or an "
            "archive extraction moves this, and time the human spent away from "
            "the keyboard reads the same as time the run spent stuck"
        ),
    }


def graph(workspace: Path) -> dict:
    result = dag_gate.analyse(workspace)
    metrics = result.metrics or {}
    if metrics.get("lemmas_dir") == "absent":
        return {"available": False, "why": "no lemmas/ directory in this run"}
    findings = metrics.get("findings", {})
    return {
        "available": True,
        "nodes": metrics.get("nodes", 0),
        "edges": metrics.get("edges", 0),
        "status_counts": metrics.get("status_counts", {}),
        # The assembly nodes and whichever of them nothing vouches for. `dag.py` has
        # computed both already and handed them over in the same dict; nothing read
        # them, so a count could be rendered as progress with no way to know whether
        # the one open item was the thing the run existed to prove.
        "top_nodes": list(metrics.get("top_nodes", []) or []),
        "unaccepted_top_nodes": list(metrics.get("unaccepted_top_node", []) or []),
        "statement_missing": len(metrics.get("statement_missing", [])),
        "status_dialect": metrics.get("status_dialect"),
        # Only what is non-zero. Nine findings all reading 0 is a wall of noise
        # a reader stops looking at, and the ones that matter hide in it.
        "findings": {
            name: len(items) for name, items in findings.items() if items
        },
        "mtime_based": metrics.get("mtime_based", []),
    }


def economics(workspace: Path) -> dict:
    result = speed_gate.lint_workspace(workspace)
    metrics = result.metrics or {}
    out = {
        "families": metrics.get("families"),
        "artifacts": metrics.get("lane_artifacts"),
        "bytes_written": metrics.get("bytes_written"),
        "bytes_final": metrics.get("bytes_final"),
        "rewrite_waste_ratio": metrics.get("rewrite_waste_ratio"),
        "required_read_bytes": metrics.get("required_read_bytes"),
        "observed_concurrency": metrics.get("observed_concurrency"),
        "concurrency_source": metrics.get("concurrency_source"),
        "declared_concurrency": metrics.get("declared_concurrency"),
    }
    token = metrics.get("token_cost") or {}
    out["cost"] = (
        token if token.get("known") else {"known": False, "why": MISSING["cost"]}
    )
    return out


def memory(workspace: Path) -> dict:
    index = workspace / "memory" / "index.json"
    if not index.is_file():
        return {"available": False, "why": "no memory/index.json — run memory.py refresh"}
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"available": False, "why": f"memory/index.json unreadable: {error}"}
    candidates = workspace / "memory" / "candidates"
    pending = 0
    if candidates.is_dir():
        for path in candidates.glob("*.jsonl"):
            try:
                pending += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            except OSError:
                continue
    promoted_path = workspace / "memory" / "candidates_promoted.json"
    promoted = None
    if promoted_path.is_file():
        try:
            promoted = len(json.loads(promoted_path.read_text(encoding="utf-8")).get("promoted", []))
        except (OSError, json.JSONDecodeError, AttributeError):
            promoted = None
    channels = data.get("channels") or {}
    return {
        "available": True,
        "channels": {k: (v.get("count") if isinstance(v, dict) else v) for k, v in channels.items()},
        "candidates_pending": pending,
        "candidates_promoted": promoted,
    }


def documents(workspace: Path) -> dict:
    out = {}
    for label, relative in (
        ("proof", "proof.pdf"),
        ("progress_notes", "progress_notes.pdf"),
        ("progress_summary", "progress_summary.pdf"),
    ):
        path = workspace / relative
        out[label] = str(relative) if path.is_file() else None
    return out


def status_file(workspace: Path) -> dict:
    path = workspace / RUN_MARKER
    if not path.is_file():
        return {"available": False, "why": "no STATUS.md — this is not a run root"}
    try:
        stat = path.stat()
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return {"available": False, "why": f"STATUS.md unreadable: {error}"}
    headings = re.findall(r"(?m)^##\s+(.+?)\s*$", text)
    return {
        "available": True,
        "bytes": stat.st_size,
        "lines": len(text.splitlines()),
        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
        "modified_at": stat.st_mtime,
        "sections": headings,
    }


def collect(workspace: Path, *, now: float | None = None) -> dict:
    workspace = Path(workspace).resolve()
    now = time.time() if now is None else now
    return {
        "workspace": str(workspace),
        "name": workspace.name,
        "status": status_file(workspace),
        "liveness": liveness(workspace, now),
        "graph": graph(workspace),
        "economics": economics(workspace),
        "memory": memory(workspace),
        "documents": documents(workspace),
        "not_recorded": MISSING,
    }


# --- rendering -----------------------------------------------------------


def _line(label: str, value) -> str:
    return f"  {label:<22}{value}"


def render(report: dict) -> str:
    out: list[str] = []
    status = report["status"]
    live = report["liveness"]
    out.append(f"# {report['name']}")
    out.append(f"  {report['workspace']}")
    out.append("")

    head = live["label"]
    if "idle" in live:
        head += f" — nothing written for {live['idle']}"
    out.append(_line("state", head))
    out.append(_line("", f"({live['why']})"))
    if status.get("available"):
        out.append(_line("STATUS.md", f"{status['lines']} lines, {status['bytes']:,} B, {status['modified']}"))
    else:
        out.append(_line("STATUS.md", status["why"]))
    out.append("")

    graph_report = report["graph"]
    out.append("## proof graph")
    if not graph_report.get("available"):
        out.append(_line("", graph_report["why"]))
    else:
        counts = graph_report["status_counts"]
        rendered = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"
        out.append(_line("lemmas", f"{graph_report['nodes']} ({rendered})"))
        out.append(_line("edges", graph_report["edges"]))
        tops = graph_report.get("top_nodes") or []
        open_top = graph_report.get("unaccepted_top_nodes") or []
        if tops:
            out.append(
                _line(
                    "target",
                    ", ".join(tops)
                    + (f" — OPEN ({len(open_top)} unaccepted)" if open_top else " — accepted"),
                )
            )
        if graph_report.get("statement_missing"):
            out.append(_line("no statement.md", graph_report["statement_missing"]))
        if graph_report.get("status_dialect"):
            out.append(_line("tracked in", graph_report["status_dialect"]))
        findings = graph_report["findings"]
        if findings:
            for name, count in sorted(findings.items()):
                mark = "*" if name in graph_report.get("mtime_based", []) else " "
                out.append(_line(f"{name}{mark}", count))
            if any(n in graph_report.get("mtime_based", []) for n in findings):
                out.append(_line("", "* read from mtimes — circumstantial"))
        else:
            out.append(_line("findings", "none of the nine fired"))
    out.append("")

    economy = report["economics"]
    out.append("## what it cost")
    # A zero here is the lie this module exists to refuse: `rewrite waste 0.0`
    # over a run with no artifacts at all is `wall_clock_ms = 0.0` printed on a
    # page a person reads. Measured across the corpus, 125 rendered lines were
    # exactly that. Nothing derived from an empty sample is printed as a number.
    # Keyed on `families`, not on `artifacts`. Bytes and rewrite waste are
    # derived from VERSIONED families -- a run with artifacts but no `_v<N>`
    # series yields 0 bytes and 0.0 waste from a sample of nothing, which is
    # what eight run roots in the corpus printed.
    families = economy.get("families")
    nothing_measured = not families
    for label, key in (
        ("artifacts", "artifacts"),
        ("bytes written", "bytes_written"),
        ("bytes final", "bytes_final"),
        ("rewrite waste", "rewrite_waste_ratio"),
        ("required read", "required_read_bytes"),
    ):
        value = economy.get(key)
        if value is None:
            out.append(_line(label, "not reported by gate speed"))
        elif key in ("bytes_written", "bytes_final", "rewrite_waste_ratio") and nothing_measured:
            out.append(_line(label, "— (no versioned artifact families to measure)"))
        else:
            out.append(_line(label, f"{value:,}" if isinstance(value, int) else value))
    concurrency = economy.get("observed_concurrency")
    source = economy.get("concurrency_source") or "unknown"
    declared = economy.get("declared_concurrency")
    if not concurrency:
        out.append(_line(
            "concurrency",
            f"unmeasured — nothing overlapped in the {source} sample"
            + (f" (ceiling {declared})" if declared else ""),
        ))
    else:
        out.append(_line("concurrency", f"{concurrency} of {declared} (from {source})"))
    cost = economy.get("cost") or {}
    if not cost.get("known"):
        out.append(_line("cost", f"unknown — {cost.get('why', 'not recorded')}"))
    out.append("")

    mem = report["memory"]
    out.append("## memory")
    if not mem.get("available"):
        out.append(_line("", mem["why"]))
    else:
        channels = ", ".join(f"{k} {v}" for k, v in sorted(mem["channels"].items()))
        out.append(_line("channels", channels or "none"))
        promoted = mem["candidates_promoted"]
        promoted_text = (
            f"{promoted} promoted" if promoted is not None
            else "promotion not run (no memory/candidates_promoted.json)"
        )
        out.append(_line("candidates", f"{mem['candidates_pending']} pending, {promoted_text}"))
    out.append("")

    docs = report["documents"]
    out.append("## documents")
    for label, value in docs.items():
        out.append(_line(label, value if value else "absent"))
    out.append("")

    out.append("## not recorded by anything")
    for name, why in report["not_recorded"].items():
        out.append(_line(name, why))
    out.append("")
    out.append("  These are printed because a page that omits what it cannot")
    out.append("  answer teaches the reader the question was not worth asking.")
    return "\n".join(out)


def render_index(reports: list[dict], root: Path | None = None) -> str:
    """One line per run root, newest first.

    Keyed on the path relative to the tree root, not the directory name: the
    corpus has two directories called `old` and a `CLT` that is both a container
    of runs and a run, so a basename index silently merges rows.
    """
    out = [f"# {len(reports)} run root(s), newest first", ""]
    out.append(f"  {'run':<48}{'state':<10}{'lemmas':<26}{'modified':<18}docs")
    for report in reports:
        graph_report = report["graph"]
        if graph_report.get("available"):
            counts = graph_report["status_counts"]
            total = graph_report["nodes"]
            # An unweighted fraction is the one place in this harness a
            # percentage-shaped progress claim is manufactured, and `gate summary`
            # exists to refuse exactly that shape in the document a person reads
            # ("a guess wearing a measurement as a costume"). Seven trivial lemmas
            # closed and the target open renders 7/8: visually finished, and no
            # closer to a proof than an empty run. The fraction stays — it is a real
            # count — with the fact that makes it readable next to it.
            open_top = graph_report.get("unaccepted_top_nodes") or []
            if "PASS" in counts:
                lemmas = f"{counts['PASS']}/{total} PASS"
                if open_top:
                    lemmas += ", target open"
            elif counts:
                # 11 of 54 run roots use a status vocabulary with no PASS value
                # at all. `0/8 PASS` reads as no progress; one of them has two
                # lemmas `done`. Name the states rather than scoring against a
                # word this run does not use.
                top = max(counts, key=lambda k: counts[k])
                lemmas = f"{total} lemmas, no PASS ({top} {counts[top]})"
            else:
                lemmas = f"{total} lemmas, no verdicts"
        else:
            lemmas = "no lemmas/"
        status = report["status"]
        modified = status.get("modified", "?") if status.get("available") else "?"
        docs = ",".join(k for k, v in report["documents"].items() if v) or "—"
        label = report.get("relative") or report["name"]
        if len(label) > 47:
            label = "…" + label[-46:]
        out.append(
            f"  {label:<48}{report['liveness']['label']:<10}"
            f"{lemmas:<26}{modified:<18}{docs}"
        )
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Where a run stands: one page per run, or an index over many.",
    )
    parser.add_argument("workspace", type=Path, help="A run root, or a tree of them with --index.")
    parser.add_argument(
        "--index",
        action="store_true",
        help="Walk every directory holding a STATUS.md and print one line each.",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.workspace)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    if args.index:
        roots = run_roots(root)
        if not roots:
            print(f"no STATUS.md anywhere below {root}", file=sys.stderr)
            return 1
        reports = []
        for path in roots:
            report = collect(path)
            try:
                report["relative"] = str(path.resolve().relative_to(root.resolve()))
            except ValueError:
                report["relative"] = report["name"]
            reports.append(report)
        reports.sort(
            key=lambda r: r["status"].get("modified_at", 0.0), reverse=True
        )
        if args.json:
            print(json.dumps(reports, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_index(reports, root))
        return 0

    if not (root / RUN_MARKER).is_file():
        below = run_roots(root)
        print(f"{root} has no {RUN_MARKER}", file=sys.stderr)
        if below:
            print(
                f"but {len(below)} run root(s) live below it — try --index",
                file=sys.stderr,
            )
        return 1
    report = collect(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
