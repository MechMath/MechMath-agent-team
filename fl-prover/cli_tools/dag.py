#!/usr/bin/env python3
"""dag — the node store, the frontier, and the one view the human kept asking for.

    dag state   <root>                          the whole picture, in one screen
    dag render  <root>                          write STATUS.md + dag.mmd for `watch -n 1`
    dag leaves  <root> [--json]                 what is ready to work RIGHT NOW
    dag put     <root> --id X --statement "..." [--lean-statement T] [--status S]
                       [--owner R] [--depends A,B] [--note "..."] [--lean-name N]
                       [--candidate-commit SHA] [--verdict-log P] [--has-sorry N]
    dag import  <root> --from <proof_tasks.json> [--apply]   what the old ledger costs

`state` and `render` exist because of one measurement. Of 121 prompts the human typed
across 174 hours, **22 were requests for state**, and this 23-character question was typed
verbatim **11 times**:

    现在什么情况，行数，时间预估，还有无数学gap

There was no view. So the human typed the query and a model answered it by re-reading the
tree with a 500,000-token context, at roughly ten seconds and several dollars a go. The
comparison that makes this embarrassing: flowverse renders its `dag.json` to a Mermaid
`DAG.md` with a status table, and says in the code that it is meant to be left under
`watch -n 1`. That is ~300 lines of store code standing in for 22 conversations.

`import` is not a migration convenience. It is the audit: run it against the 3.6 MB
`.claude/state/proof_tasks.json` and it prints, per task, what the typed store refuses and
why — 428 owner strings, `has_sorry: null` on all 429 `s9-*` tasks, statements that are
proof sketches rather than types. Read that output before deciding what to port.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _dag.store import OWNERS, STATUS, TERMINAL, Node, Rejected, Store  # noqa: E402

BAR = "─" * 72


def _load(root: str) -> Store:
    return Store(Path(root).expanduser())


def cmd_state(args) -> int:
    st = _load(args.root)
    if not st.nodes:
        print(f"no dag.json under {args.root} — nothing stated yet.\n"
              "State the top obligation first: dag put <root> --id ... --statement ...")
        return 0
    c = st.census()
    leaves = st.open_leaves()
    total = len(st.nodes)
    done = c["proved"]
    print(BAR)
    print(f"  {total} nodes · {done} proved · {total - done - c['refuted'] - c['superseded']} open"
          f" · {c['refuted']} refuted · {c['blocked']} blocked")
    print(f"  census: " + "  ".join(f"{k}={v}" for k, v in c.items() if v))
    print(BAR)
    known = sum(1 for n in st.nodes.values() if n.has_sorry is not None)
    print(f"  sorry counts recorded on {known}/{total} nodes"
          + ("" if known == total else "   <- unrecorded nodes cannot be reported on"))
    unfrozen = [n.id for n in st.nodes.values() if not n.lean_statement and n.status not in TERMINAL]
    if unfrozen:
        print(f"  {len(unfrozen)} open node(s) have NO frozen contract: {', '.join(unfrozen[:8])}"
              + (" ..." if len(unfrozen) > 8 else ""))
    noread = [n.id for n in st.nodes.values() if n.status == "proved" and not n.readback]
    if noread:
        print(f"  {len(noread)} proved node(s) have NO blind read-back: {', '.join(noread[:8])}"
              + (" ..." if len(noread) > 8 else ""))
    print(BAR)
    print(f"  READY NOW ({len(leaves)}):")
    for n in sorted(leaves, key=lambda x: (x.status, x.id))[:20]:
        own = f" [{n.owner}]" if n.owner else " [unowned]"
        print(f"    {n.status:<12}{n.id}{own}")
        print(f"                {n.statement[:66]}")
    blocked = [n for n in st.nodes.values() if n.status == "blocked"]
    if blocked:
        print(BAR)
        print(f"  NAMED BOUNDARIES ({len(blocked)}) — these need a decision, not another agent:")
        for n in blocked:
            print(f"    {n.id}: {n.note[:80]}")
    ref = [n for n in st.nodes.values() if n.status == "refuted"]
    if ref:
        print(BAR)
        print(f"  REFUTED ({len(ref)}) — results, not failures:")
        for n in ref:
            print(f"    {n.id}: {n.note[:80]}")
    print(BAR)
    return 0


def cmd_leaves(args) -> int:
    st = _load(args.root)
    ls = st.open_leaves()
    if args.json:
        print(json.dumps([{"id": n.id, "status": n.status, "owner": n.owner,
                           "statement": n.statement, "lean_statement": n.lean_statement}
                          for n in ls], indent=2, ensure_ascii=False))
    else:
        for n in ls:
            print(f"{n.id}\t{n.status}\t{n.owner or '-'}\t{n.statement[:60]}")
    return 0


MERMAID_CLASS = {
    "proved": "fill:#d4f7d4,stroke:#2a7", "refuted": "fill:#ffe0e0,stroke:#a33",
    "blocked": "fill:#ffe9c9,stroke:#c80", "superseded": "fill:#eee,stroke:#999",
}


def cmd_render(args) -> int:
    root = Path(args.root).expanduser()
    st = _load(args.root)
    c = st.census()
    total = len(st.nodes)
    lines = [
        "# Status", "",
        "Generated by `dag render`. **Do not hand-edit** — this file is a view, and the last",
        "run's hand-maintained ledger reached 20 different status tokens and could not be",
        "counted. Leave it under `watch -n 2 'cat STATUS.md'`.", "",
        f"- **{total} nodes** · {c['proved']} proved · {c['refuted']} refuted · "
        f"{c['blocked']} blocked",
        f"- census: " + ", ".join(f"`{k}`={v}" for k, v in c.items() if v), "",
        "## Ready now", "",
        "| node | status | owner | statement |", "|---|---|---|---|",
    ]
    for n in sorted(st.open_leaves(), key=lambda x: x.id):
        lines.append(f"| `{n.id}` | {n.status} | {n.owner or '—'} | {n.statement[:70]} |")
    boundaries = [n for n in st.nodes.values() if n.status == "blocked"]
    if boundaries:
        lines += ["", "## Named boundaries — a decision, not another agent", ""]
        lines += [f"- **`{n.id}`** — {n.note}" for n in boundaries]
    refuted = [n for n in st.nodes.values() if n.status == "refuted"]
    if refuted:
        lines += ["", "## Refuted — results, not failures", ""]
        lines += [f"- **`{n.id}`** — {n.note}" for n in refuted]
    (root / "STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Mermaid node ids may not contain '-' or '.', but node ids here are human-chosen and
    # nearly always do. Emitting them raw produces a diagram that silently fails to render,
    # which is the same class of defect as a glob that matches nothing.
    def mid(nid: str) -> str:
        # A plain character substitution is NOT injective: `x-1` and `x.1` both became
        # `n_x_1`, collapsing two obligations into one mermaid node and rewiring the
        # edges onto whichever survived; ids that are entirely non-ASCII collided by
        # length alone (引理一 and 引理二 both became `n____`). Ids mixing `-` and `.`
        # are exactly the style the 2026-09 run used. A short hash of the original makes
        # the mapping injective while keeping the id readable.
        safe = re.sub(r"[^0-9A-Za-z_]", "_", nid)
        return "n_" + safe + "_" + hashlib.sha1(nid.encode("utf-8")).hexdigest()[:6]

    mm = ["graph TD"]
    for n in st.nodes.values():
        label = n.id.replace('"', "'")
        mm.append(f'  {mid(n.id)}["{label}<br/>{n.status}"]')
        for d in n.depends_on:
            mm.append(f"  {mid(d)} --> {mid(n.id)}")
    for n in st.nodes.values():
        if n.status in MERMAID_CLASS:
            mm.append(f"  style {mid(n.id)} {MERMAID_CLASS[n.status]}")
    (root / "dag.mmd").write_text("\n".join(mm) + "\n", encoding="utf-8")
    print(f"wrote {root/'STATUS.md'} and {root/'dag.mmd'} ({total} nodes)")
    return 0


def cmd_put(args) -> int:
    with Store.hold_lock(Path(args.root).expanduser()):
        return _put_locked(args)


def _put_locked(args) -> int:
    st = _load(args.root)
    node = Node(
        id=args.id, statement=args.statement or "", lean_name=args.lean_name or "",
        lean_statement=args.lean_statement or "", status=args.status,
        owner=args.owner or "", note=args.note or "",
        depends_on=[d for d in (args.depends or "").split(",") if d],
        parent=args.parent or "", depth=args.depth,
        candidate_commit=args.candidate_commit or "", verdict_log=args.verdict_log or "",
        proof_base_commit=args.proof_base_commit or "",
        has_sorry=args.has_sorry,
        readback=args.readback or "",
    )
    prev = st.nodes.get(args.id)
    if prev is not None:
        # A put is a patch: unspecified fields keep their recorded value, so a status
        # update cannot silently blank a frozen contract or a landed commit.
        for f in ("statement", "lean_name", "lean_statement", "owner", "note", "parent",
                  "candidate_commit", "verdict_log", "proof_base_commit", "readback"):
            if not getattr(node, f):
                setattr(node, f, getattr(prev, f))
        if not node.depends_on:
            node.depends_on = prev.depends_on
        if node.has_sorry is None:
            node.has_sorry = prev.has_sorry
        # `status` and `depth` were NOT in that list, and both have a non-empty argparse
        # default, so `dag put --id n1 --owner golfer` on a node at `verifying` silently
        # rewound it to `open`. The comment above claimed unspecified fields keep their
        # value; for the single most important field it was false. Only an explicit
        # --status may move a node now.
        if "--status" not in sys.argv:
            node.status = prev.status
        if "--depth" not in sys.argv:
            node.depth = prev.depth
    try:
        st.put(node)
    except Rejected as exc:
        print(f"REFUSED\n{exc}", file=sys.stderr)
        return 1
    st.save()
    print(f"{args.id}: {node.status}" + (f" [{node.owner}]" if node.owner else ""))
    return 0


def cmd_import(args) -> int:
    """Report what the old free-text ledger contains that a typed store will not accept."""
    src = Path(args.source).expanduser()
    raw = json.loads(src.read_text(encoding="utf-8"))
    tasks = raw.get("tasks", raw)
    if isinstance(tasks, dict):
        tasks = list(tasks.values())
    tasks = [t for t in tasks if isinstance(t, dict)]
    bad_owner: dict[str, int] = {}
    bad_status: dict[str, int] = {}
    prot: dict[str, int] = {}
    no_sorry = no_statement = has_decl = policy_review = 0
    for t in tasks:
        o = t.get("owner")
        if o and o not in OWNERS:
            bad_owner[o] = bad_owner.get(o, 0) + 1
        s = t.get("status")
        if s and s not in STATUS:
            bad_status[s] = bad_status.get(s, 0) + 1
        if (t.get("proof_state") or {}).get("has_sorry") is None:
            no_sorry += 1
        if not str(t.get("statement") or t.get("goal") or t.get("description") or "").strip():
            no_statement += 1
        if str(t.get("declaration") or "").strip():
            has_decl += 1
        ps = t.get("protected_statement") or {}
        prot[str(ps.get("state"))] = prot.get(str(ps.get("state")), 0) + 1
        if ps.get("change_policy") == "review-required":
            policy_review += 1
    print(f"{src}: {len(tasks)} tasks")
    print(f"  owners outside the roster : {sum(bad_owner.values())} tasks / "
          f"{len(bad_owner)} distinct strings")
    for o, n in sorted(bad_owner.items(), key=lambda kv: -kv[1])[:8]:
        print(f"      {n:>4}x  {o[:66]}")
    print(f"  statuses outside the enum : {sum(bad_status.values())} tasks / "
          f"{len(bad_status)} distinct tokens")
    for s, n in sorted(bad_status.items(), key=lambda kv: -kv[1])[:12]:
        print(f"      {n:>4}x  {s}")
    print(f"  has_sorry unrecorded      : {no_sorry} tasks")
    print(f"  no natural-language statement : {no_statement} tasks"
          f"  ({has_decl} do carry a `declaration`, i.e. a Lean NAME)")
    print("      A Lean name is not a statement. Nothing can index it, and a blind reader")
    print("      given only a name cannot say what the code asserts — which is the check")
    print("      that would have caught 14 false-but-compiling statements.")
    print(f"  protected_statement.state : "
          + ", ".join(f"{k}={v}" for k, v in sorted(prot.items(), key=lambda kv: -kv[1])))
    print(f"      change_policy=review-required on {policy_review} tasks")
    print("      This is the freeze mechanism, and it already exists with hashes. What it")
    print("      lacks is a writer that refuses: the policy is recorded, never enforced.")
    print("\nNothing was written. This is the cost of the old ledger, not a plan to port it:")
    print("  every line above is a value the typed store would have refused at write time.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dag", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("state", cmd_state), ("render", cmd_render)):
        q = sub.add_parser(name)
        q.add_argument("root")
        q.set_defaults(fn=fn)
    q = sub.add_parser("leaves"); q.add_argument("root")
    q.add_argument("--json", action="store_true"); q.set_defaults(fn=cmd_leaves)
    q = sub.add_parser("put"); q.add_argument("root")
    q.add_argument("--id", required=True)
    q.add_argument("--statement", default="")
    q.add_argument("--lean-statement", dest="lean_statement", default="")
    q.add_argument("--lean-name", dest="lean_name", default="")
    q.add_argument("--status", default="open", choices=STATUS)
    q.add_argument("--owner", default="", choices=("", *OWNERS))
    q.add_argument("--depends", default="")
    q.add_argument("--parent", default="")
    q.add_argument("--depth", type=int, default=0)
    q.add_argument("--note", default="")
    q.add_argument("--candidate-commit", dest="candidate_commit", default="")
    q.add_argument("--proof-base-commit", dest="proof_base_commit", default="")
    q.add_argument("--verdict-log", dest="verdict_log", default="")
    q.add_argument("--has-sorry", dest="has_sorry", type=int, default=None)
    # `Node.readback` existed as a field, `dag state` listed proved nodes that lacked one,
    # and there was NO WRITER for it anywhere in the CLI — so that list could only ever be
    # emptied by proving nothing. The one mechanical consumer of P6 was unsatisfiable.
    q.add_argument("--readback", default="",
                   help="what a blind reader said this statement literally asserts")
    q.set_defaults(fn=cmd_put)
    # `import` is an AUDIT, not a migration: it reports what the typed store would refuse
    # and writes nothing. It used to take an unused positional `root` and an `--apply`
    # flag that no code read, so the interface promised a migration that did not exist.
    q = sub.add_parser("import", help="audit a free-text ledger against this store")
    q.add_argument("--from", dest="source", required=True)
    q.set_defaults(fn=cmd_import)
    return p


def main() -> int:
    if "--self-test" in sys.argv:
        from _dag import selftest
        return selftest.run()
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
