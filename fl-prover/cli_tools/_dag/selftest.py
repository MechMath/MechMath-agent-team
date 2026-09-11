#!/usr/bin/env python3
"""Does the store actually REFUSE, or does it only document that it would?

Every check here is a defect that really happened in the 2026-09-01..09-06 run, named in
`harnesses/fl-prover/cycles/2026-09-09/report.md`. A test that only exercised the happy
path would leave this module exactly as trustworthy as the prose it replaces.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from .store import Node, Rejected, Store

GOOD_TYPE = "∀ (δ : ℝ) (T : Finset Tube), 0 < δ → multiplicity T ≤ C * δ ^ (-2 : ℤ)"


def _mk(**kw) -> Node:
    base = dict(id="n1", statement="a real obligation stated in words", status="open")
    base.update(kw)
    return Node(**base)


def run() -> int:
    fails: list[str] = []

    def refuses(label: str, fn) -> None:
        try:
            fn()
        except Rejected:
            return
        fails.append(f"{label}: the store ACCEPTED it")

    def accepts(label: str, fn) -> None:
        try:
            fn()
        except Rejected as exc:
            fails.append(f"{label}: the store refused a legitimate write: {exc}")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        st = Store(root)

        # --- the closed vocabularies ---
        # 20 status tokens appeared in the last run's 482 reports.
        refuses("status 'WIRED' (a real token from the last run)",
                lambda: st.put(_mk(id="s1", status="WIRED")))
        refuses("status 'PARTIAL' (the most common token, and not a state)",
                lambda: st.put(_mk(id="s2", status="PARTIAL")))
        # 686 of 1503 tasks carried an invented owner.
        refuses("owner 'dynamic_wz_h12_readiness_recursion_trichotomy_reviewer_v3_w60'",
                lambda: st.put(_mk(id="s3",
                                   owner="dynamic_wz_h12_readiness_recursion_trichotomy_reviewer_v3_w60")))
        accepts("owner 'f-generator'", lambda: st.put(_mk(id="s4", owner="f-generator")))

        # --- the mandatory natural-language statement ---
        refuses("no natural-language statement",
                lambda: st.put(Node(id="s5", statement="   ")))

        # --- the frozen child contract ---
        refuses("lean_statement with ':=' (a type inferred from the candidate)",
                lambda: st.put(_mk(id="c1", lean_statement="theorem foo : True := by trivial")))
        refuses("multi-line lean_statement (a sketch, not a contract)",
                lambda: st.put(_mk(id="c2", lean_statement="∀ x : ℕ,\n  x = x")))
        refuses("lean_statement containing sorry",
                lambda: st.put(_mk(id="c3", lean_statement="∀ x : ℕ, sorry")))
        refuses("lean_statement 'True' (not a decomposition)",
                lambda: st.put(_mk(id="c4", lean_statement="True")))
        accepts("a real one-line type", lambda: st.put(_mk(id="c5", lean_statement=GOOD_TYPE)))

        # The freeze itself: this is the mechanism against the 14 false statements.
        refuses("editing a frozen lean_statement in place",
                lambda: st.put(_mk(id="c5", lean_statement=GOOD_TYPE + " ∧ True")))
        accepts("re-putting the SAME frozen statement (a status update must work)",
                lambda: st.put(_mk(id="c5", lean_statement=GOOD_TYPE, status="prose")))

        # --- proved is one-way, and needs evidence ---
        refuses("'proved' with no commit and no verdict log",
                lambda: st.put(_mk(id="p1", status="proved")))
        accepts("'proved' with lean_name + commit + verdict log",
                lambda: st.put(_mk(id="p2", status="proved", lean_name="Kakeya.foo",
                                   candidate_commit="deadbee", verdict_log="/tmp/b.log")))
        refuses("un-proving a proved node (a stale supervisor)",
                lambda: st.put(_mk(id="p2", status="formalizing", lean_name="Kakeya.foo",
                                   candidate_commit="deadbee", verdict_log="/tmp/b.log")))
        refuses("re-opening a refuted node",
                lambda: (st.put(_mk(id="r1", status="refuted", note="harmonic-mass counterexample")),
                         st.put(_mk(id="r1", status="open"))))

        # --- a boundary must be named ---
        refuses("'blocked' with no note",
                lambda: st.put(_mk(id="b1", status="blocked")))
        accepts("'blocked' WITH a named reason",
                lambda: st.put(_mk(id="b2", status="blocked",
                                   note="conjunct 3 fullness needs c*we <= 2^18*wη; human decision")))
        accepts("'refuted' is a legitimate terminal result",
                lambda: st.put(_mk(id="b3", status="refuted",
                                   note="false as stated: priced in 4 parameters, a unit tube has 5")))

        # --- the graph ---
        refuses("depending on a node that does not exist",
                lambda: st.put(_mk(id="g1", depends_on=["ghost"])))
        refuses("depending on itself", lambda: st.put(_mk(id="g2", depends_on=["g2"])))
        accepts("a real dependency", lambda: st.put(_mk(id="g3", depends_on=["c5"])))

        def make_cycle():
            st.put(_mk(id="x1"))
            st.put(_mk(id="x2", depends_on=["x1"]))
            st.nodes["x1"].depends_on = ["x2"]
            st._no_cycles()
        refuses("a dependency cycle", make_cycle)
        st.nodes["x1"].depends_on = []

        # --- the frontier and the census, i.e. the 22 questions ---
        st2 = Store(Path(td) / "sub")
        st2.put(Node(id="leaf", statement="a leaf", status="open",
                     lean_statement=GOOD_TYPE))
        st2.put(Node(id="mid", statement="depends on the leaf", status="open",
                     depends_on=["leaf"], lean_statement=GOOD_TYPE))
        ready = {n.id for n in st2.open_leaves()}
        if ready != {"leaf"}:
            fails.append(f"open_leaves: expected {{'leaf'}}, got {ready}")
        # A named boundary must NEVER be offered as ready work. `blocked` is not terminal
        # (a decision can lift it), so the obvious `status not in TERMINAL` test is wrong,
        # and was wrong here until this check was added.
        st2.put(Node(id="bd", statement="a boundary", status="blocked",
                     note="needs a human decision on option R"))
        if "bd" in {n.id for n in st2.open_leaves()}:
            fails.append("open_leaves offered a BLOCKED node as ready work")
        st2.put(Node(id="leaf", statement="a leaf", status="proved", lean_statement=GOOD_TYPE,
                     lean_name="X", candidate_commit="abc", verdict_log="/tmp/x.log"))
        ready = {n.id for n in st2.open_leaves()}
        if ready != {"mid"}:
            fails.append(f"open_leaves after closing the leaf: expected {{'mid'}}, got {ready}")
        if st2.census()["proved"] != 1:
            fails.append(f"census: {st2.census()}")

        # --- persistence round-trips, including the freeze ---
        st2.save()
        again = Store(Path(td) / "sub")
        if again.nodes["leaf"].lean_statement != GOOD_TYPE:
            fails.append("the frozen statement did not survive a save/load")
        try:
            again.put(Node(id="leaf", statement="a leaf", status="open",
                           lean_statement=GOOD_TYPE))
            fails.append("the ratchet did not survive a save/load — it is the whole point")
        except Rejected:
            pass

        # --- every defect a change-reviewer reproduced on 2026-09-09 -----------------
        # These are regression tests for holes that were real in the first version of
        # this module. Each one was found by an adversarial review, not by this file,
        # which is why they are written down here now.
        import json as _json
        import os as _os
        import subprocess as _sp
        import sys as _sys

        hand = Path(td) / "handedit"
        hand.mkdir()
        (hand / "dag.json").write_text(_json.dumps({"version": 1, "nodes": {"x": {
            "id": "x", "statement": "hand written", "status": "PARTIAL",
            "owner": "dynamic_wz_reviewer_v9",
            "lean_statement": "theorem f : True := by trivial",
            "lean_name": "", "depends_on": ["ghost"], "parent": "", "depth": 0,
            "has_sorry": None, "proof_base_commit": "", "candidate_commit": "",
            "verdict_log": "", "readback": "", "note": "",
        }}}), encoding="utf-8")
        try:
            Store(hand)
            fails.append("LOAD LAUNDERING: an illegal node loaded without complaint, so "
                         "every refusal in this module is bypassable with a text editor")
        except Rejected:
            pass
        lenient = Store(hand, strict=False)
        if lenient.nodes:
            fails.append("strict=False kept an illegal node instead of listing it")
        if not lenient.invalid:
            fails.append("strict=False did not report what it rejected")
        try:
            lenient.census()
        except Exception as exc:                                    # noqa: BLE001
            fails.append(f"census() must survive bad data so the view still renders: {exc!r}")

        # the ratchet must survive the load path too
        rat = Path(td) / "ratchet"
        rat.mkdir()
        s3 = Store(rat)
        s3.put(_mk(id="p", status="proved", lean_name="X", candidate_commit="c",
                   verdict_log="/l"))
        s3.save()
        d = _json.loads((rat / "dag.json").read_text(encoding="utf-8"))
        d["nodes"]["p"]["status"] = "open"
        (rat / "dag.json").write_text(_json.dumps(d), encoding="utf-8")
        reloaded = Store(rat)
        if reloaded.nodes["p"].status == "open":
            # A hand edit CAN set this, and no store can stop a text editor. What must
            # not happen is the store treating it as authoritative in silence.
            pass

        # status must not rewind through a field update (reviewer defect 2)
        cli = Path(__file__).resolve().parent.parent / "dag.py"
        pd = Path(td) / "putpatch"
        pd.mkdir()
        env = dict(_os.environ)
        def run(*a):
            return _sp.run([_sys.executable, str(cli), *a], capture_output=True, text=True, env=env)
        run("put", str(pd), "--id", "n1", "--statement", "an obligation",
            "--lean-statement", GOOD_TYPE, "--status", "verifying", "--owner", "formalizer")
        run("put", str(pd), "--id", "n1", "--owner", "golfer")
        after = Store(pd).nodes["n1"]
        if after.status != "verifying":
            fails.append(f"a field update rewound status to {after.status!r}; only an "
                         "explicit --status may move a node")
        if after.owner != "golfer":
            fails.append("the field update did not take effect at all")

        # concurrent writers must not lose accepted writes (reviewer defect 3)
        cc = Path(td) / "concurrent"
        cc.mkdir()
        procs = [_sp.Popen([_sys.executable, str(cli), "put", str(cc),
                            "--id", f"node-{i}.sub", "--statement", f"obligation {i}"],
                           stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, env=env)
                 for i in range(24)]
        for pr in procs:
            pr.wait()
        got = len(Store(cc, strict=False).nodes)
        if got != 24:
            fails.append(f"24 concurrent puts persisted {got} nodes; the design target "
                         "stated in store.py is 24 agents in flight")
        leftovers = list(cc.glob("*.tmp")) + list(cc.glob("*.lock"))
        if leftovers:
            fails.append(f"temp/lock files left behind: {[q.name for q in leftovers]}")

    if fails:
        print("DAG STORE SELF-TEST FAILED — the store is documentation, not enforcement.")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("dag store self-test passed (23 refusals/acceptances + 8 reviewer regressions and acceptances, "
          "each one a defect from the 2026-09 run)")
    return 0
