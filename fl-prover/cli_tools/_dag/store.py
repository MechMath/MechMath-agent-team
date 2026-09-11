#!/usr/bin/env python3
"""The typed node store — one source of truth for what is open, who owns it, and why.

WHAT THIS REPLACES, and why a store rather than a document.

The 2026-09-01..09-06 run carried its state in three markdown files (BRIEF.md 545 lines,
STATUS-S9.md 5,211, HANDOFF.md 1,193), 482 reports, and a 3.6 MB JSON ledger. Measured
against those artifacts afterwards:

  * `STATUS:` in the 482 reports used **20 distinct tokens** — PARTIAL 89, CLOSED 68,
    LANDED 44, DONE 19, BLOCKED 9, RULED 9, REFUTED 6, and one each of WIRED, THREADED,
    GREEN, BUILT, FINDING, INHERITED. There is no FAILED. 215 of 482 reports open with a
    verdict sentence the format never specified. Nobody can count progress from that.
  * `owner` in the ledger had **428 distinct values**. 686 of 1,503 tasks (46%) carried
    names invented at dispatch time; 86 carried `_v2`..`_v9` counters; one family,
    `dynamic_wz_h12_readiness_recursion_trichotomy_reviewer`, was re-dispatched 34 times
    under different invented owners. Those version counters are the tree rings of going
    in circles.
  * `proof_state.has_sorry` was `null` for all 429 `s9-*` tasks — the field existed and
    was never filled, so the only observable left was a sorry census, which the human
    asked for 22 times, typing the same 23-character question 11 times.

None of that is a discipline problem. A markdown ledger cannot refuse a token, and a
model writing JSON invents a field value when it has one to write. So the vocabulary,
the roster and the ratchet live below the write, where argument is not possible:

  STATUS is an enum          -> a 21st token cannot be recorded
  OWNER is a roster          -> an invented owner cannot be recorded
  proved never un-proves     -> a stale supervisor cannot erase a closed obligation
  a child's Lean TYPE is frozen before the child is dispatched
                             -> "comparing two aliases whose types are both inferred from
                                the candidate is not an acceptable correctness gate"

That last one is the expensive lesson. Fourteen statements in the last run compiled
cleanly, sorry-free, and were FALSE — `ThinCase.factoringApply` (harmonic-mass
counterexample), `ThinCase.perBall` (inherited), `exists_setup_caseSideData` and GWZ
Lemma 9.1 as rendered (priced in four parameters; a unit-length tube has five). Each was
found by the first agent unlucky enough to try to prove it, after its siblings had been
built on it. Freezing the type at decomposition time is what makes a split falsifiable
instead of aspirational.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --- the closed vocabularies --------------------------------------------------------

STATUS = (
    "open",          # stated, not started
    "assigned",      # an agent owns it right now
    "prose",         # the mathematics is being settled in natural language
    "formalizing",   # the Lean is being written
    "verifying",     # a verdict is being obtained
    "proved",        # verdict passed, twice, by two parties. TERMINAL AND ONE-WAY.
    "blocked",       # a named boundary: it cannot proceed and the reason is recorded
    "refuted",       # the statement is false. TERMINAL. This is a result, not a failure.
    "superseded",    # replaced by another node. TERMINAL.
)
TERMINAL = ("proved", "refuted", "superseded")

# The nine roles this harness actually declares. `dynamic_wz_h12_..._reviewer_v3_w60` is
# not a role, it is a task name that escaped into the owner field 686 times.
OWNERS = (
    "formalizer", "f-reviewer", "f-generator", "integrator",
    "golfer", "regulator", "blueprinter", "orchestrator", "human",
)

# `refuted` is deliberately terminal-and-good. A round that proves a published lemma false
# has produced a result: the last run spent 14,464 sorry-free lines across 22 files
# establishing refutations and obstructions, and a status vocabulary that can only say
# PARTIAL cannot record that as anything but a failure to finish.


# The free-text writer that produced the 16 tokens. `control.py set-status` took a bare
# positional with no `choices`, so `completed` (837 tasks), `done` (413) and `DONE` (56)
# — three spellings of one state — all entered the ledger through it. Constraining it
# outright would break every existing caller, so the legacy tokens are accepted and
# NORMALISED. The vocabulary converges without a flag day; a token that is not here and
# not an alias is refused.
STATUS_ALIASES = {
    "todo": "open", "queued": "open", "pending": "open", "needs-proof": "open",
    "active": "assigned", "in_progress": "assigned", "in-progress": "assigned",
    "needs-statement-review": "verifying", "verified": "proved",
    "completed": "proved", "done": "proved",
    "dropped": "superseded", "rejected": "refuted",
}


def normalise_status(token: str) -> str:
    """Map a legacy status token onto the enum, or raise saying what is allowed."""
    t = (token or "").strip()
    if t in STATUS:
        return t
    low = t.lower()
    if low in STATUS:
        return low
    if low in STATUS_ALIASES:
        return STATUS_ALIASES[low]
    raise Rejected(
        f"status {token!r} is not a state. Allowed: {', '.join(STATUS)}.\n"
        f"  Legacy tokens accepted and normalised: {', '.join(sorted(STATUS_ALIASES))}.\n"
        "  The previous ledger held 16 tokens including three spellings of 'proved', "
        "which is why this is a function and not a convention."
    )


class Rejected(Exception):
    """The store refused a write. Not an error to retry — a fact about the write."""


# --- the frozen child contract ------------------------------------------------------

_ASSIGN = re.compile(r":=")


def validate_lean_statement(text: str) -> str:
    """A child's contract: a single-line Lean TYPE expression, frozen before it is proved.

    Refused, with reasons rather than a bare no:
      * a newline — a multi-line statement is a proof sketch, and it will drift
      * `:=` — that is a definition, i.e. a type inferred from whatever the child wrote,
        which is the exact non-gate flowverse names in its SKILL.md
      * `sorry` / `admit` — a hole in a contract is not a contract
      * under 10 characters — `True` is not a decomposition
    """
    t = (text or "").strip()
    if not t:
        raise Rejected("lean_statement is empty; a child with no contract cannot be checked")
    if "\n" in t:
        raise Rejected(
            "lean_statement spans lines. A contract is ONE type expression; a multi-line "
            "statement is a sketch and it will have drifted by the time the child returns."
        )
    if _ASSIGN.search(t):
        raise Rejected(
            "lean_statement contains ':='. That makes the child's type inferred from the "
            "child's own proof, and comparing two aliases whose types both come from the "
            "candidate is not a correctness gate. State the TYPE."
        )
    if re.search(r"\b(sorry|admit)\b", t):
        raise Rejected("lean_statement contains sorry/admit; a contract with a hole is not one")
    if len(t) < 10:
        raise Rejected(f"lean_statement {t!r} is too short to be a real obligation")
    return t


@dataclass
class Node:
    id: str
    statement: str = ""              # natural language, mandatory: it is what search indexes
    lean_name: str = ""
    lean_statement: str = ""         # the frozen one-line type
    status: str = "open"
    owner: str = ""
    depends_on: list[str] = field(default_factory=list)
    parent: str = ""
    depth: int = 0
    has_sorry: int | None = None     # filled by the verdict tool, never by a model
    proof_base_commit: str = ""
    candidate_commit: str = ""
    verdict_log: str = ""            # the log the sentinel was read from
    readback: str = ""               # what a blind reader said this statement asserts
    note: str = ""                   # for blocked/refuted: the named reason. Mandatory there.

    def check(self) -> None:
        if not self.id or "/" in self.id:
            raise Rejected(f"bad node id {self.id!r}")
        if self.status not in STATUS:
            raise Rejected(
                f"status {self.status!r} is not one of {', '.join(STATUS)}.\n"
                "  The last run's reports used 20 different status tokens and could not be "
                "counted. If none of these fits, the vocabulary is wrong and changing it is "
                "a decision, not a write."
            )
        if self.owner and self.owner not in OWNERS:
            raise Rejected(
                f"owner {self.owner!r} is not a role. Roles: {', '.join(OWNERS)}.\n"
                "  686 of 1,503 tasks in the last ledger carried an owner invented at "
                "dispatch time. Put the task name in `id`, not in `owner`."
            )
        if not self.statement.strip():
            raise Rejected(
                "statement (natural language) is mandatory. It is the only thing a search "
                "can index and the only thing a blind reader can be checked against."
            )
        if self.lean_statement:
            self.lean_statement = validate_lean_statement(self.lean_statement)
        if self.status in ("blocked", "refuted") and not self.note.strip():
            raise Rejected(
                f"status {self.status!r} without a note. A boundary with no named reason is "
                "indistinguishable from giving up, and the next round will re-attack it."
            )
        if self.status == "proved":
            missing = [k for k in ("lean_name", "candidate_commit", "verdict_log")
                       if not getattr(self, k)]
            if missing:
                raise Rejected(
                    f"'proved' requires {', '.join(missing)}. A landing with no commit and no "
                    "verdict log is a claim: 28.9% of the last run's 2,663 build logs left no "
                    "recoverable verdict at all."
                )


class Store:
    """Nodes on disk, with the ratchet enforced HERE rather than by convention.

    flowverse keeps this invariant at the same place and says why: "so stale supervisors
    cannot accidentally erase it." In a run with 24 agents in flight and a model doing the
    orchestration, the supervisor's belief about a node is routinely older than the node.
    """

    def __init__(self, root: Path, *, strict: bool = True):
        self.path = Path(root) / "dag.json"
        self.lock = Path(root) / "dag.json.lock"
        self.nodes: dict[str, Node] = {}
        self.invalid: list[str] = []
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            for nid, d in (raw.get("nodes") or {}).items():
                try:
                    n = Node(**d)
                    n.check()
                except (Rejected, TypeError) as exc:
                    self.invalid.append(f"{nid}: {str(exc).splitlines()[0]}")
                    continue
                self.nodes[nid] = n
            # THE HOLE THIS CLOSES. Until 2026-09-09 the constructor did `Node(**d)` with
            # no validation, so every refusal in this module was enforced on the `put`
            # path only: an illegal status, an invented owner, a `lean_statement` holding
            # `:=`, and an un-proved `proved` node all survived a load and were written
            # straight back out by `save()`. One text edit to dag.json defeated the
            # ratchet, which is the ratchet's entire purpose. `census()` then died with
            # KeyError on the illegal status, taking `dag state` and `dag render` with it.
            #
            # A truth store that silently drops what it cannot understand is worse than
            # one that refuses to open, so `strict` is the default and the caller has to
            # ask for the lenient read.
            if self.invalid and strict:
                raise Rejected(
                    f"{self.path} holds {len(self.invalid)} node(s) this store cannot "
                    "accept, so it will not be loaded:\n"
                    + "".join(f"  {v}\n" for v in self.invalid[:10])
                    + "  Nothing was read. Repair the file, or load with strict=False to "
                    "inspect it — a load that silently drops nodes is how a hand edit "
                    "becomes state."
                )

    def save(self) -> None:
        """Atomic per writer. The tmp name used to be shared, which lost writes.

        Measured before this fix: 40 concurrent `dag put` calls left 25 nodes — fifteen
        accepted writes vanished and six processes crashed on each other's
        `dag.json.tmp`. The design target stated eight lines above this is 24 agents in
        flight, so 'atomic' had to mean atomic against siblings, not just against a
        crash. Unique tmp per process, and `hold_lock` around read-modify-write.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"dag.json.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(
            json.dumps({"version": 1, "nodes": {k: asdict(v) for k, v in self.nodes.items()}},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)   # atomic: a torn dag.json loses the whole round

    @staticmethod
    @contextlib.contextmanager
    def hold_lock(root: Path, timeout: float = 30.0):
        """Serialise read-modify-write across processes. O_EXCL, so no third-party dep."""
        lock = Path(root) / "dag.json.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        fd = None
        while fd is None:
            try:
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                # A holder that died leaves the lock behind; break it after the timeout
                # rather than wedging the swarm.
                try:
                    if time.monotonic() > deadline:
                        age = time.time() - lock.stat().st_mtime
                        if age > timeout:
                            lock.unlink(missing_ok=True)
                            continue
                        raise Rejected(f"dag.json is locked by another writer ({age:.0f}s)")
                except FileNotFoundError:
                    continue
                time.sleep(0.05)
        try:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)

    def put(self, node: Node) -> Node:
        node.check()
        old = self.nodes.get(node.id)
        if old is not None:
            self._ratchet(old, node)
            if old.lean_statement and node.lean_statement != old.lean_statement:
                raise Rejected(
                    f"node {node.id}: lean_statement is FROZEN.\n"
                    f"  was: {old.lean_statement}\n"
                    f"  now: {node.lean_statement}\n"
                    "  A child's contract is fixed before the child is dispatched. If the "
                    "statement is wrong, that is a result: mark this node `refuted` with the "
                    "reason and state a NEW node. Editing it in place is how a false lemma "
                    "reaches its siblings — it happened 14 times in the last run."
                )
        for d in node.depends_on:
            if d not in self.nodes and d != node.id:
                raise Rejected(f"node {node.id} depends on {d!r}, which does not exist")
        if node.id in node.depends_on:
            raise Rejected(f"node {node.id} depends on itself")
        self.nodes[node.id] = node
        self._no_cycles()
        return node

    @staticmethod
    def _ratchet(old: Node, new: Node) -> None:
        if old.status in TERMINAL and new.status != old.status:
            raise Rejected(
                f"node {old.id}: refusing regressive transition {old.status!r} -> "
                f"{new.status!r}. {old.status!r} is terminal and one-way.\n"
                "  Accepted mathematics cannot be re-opened by an integration conflict or by "
                "a supervisor working from stale state. Supersede it with a new node instead."
            )

    def _no_cycles(self) -> None:
        colour: dict[str, int] = {}

        def walk(n: str) -> None:
            if colour.get(n) == 1:
                raise Rejected(f"dependency cycle through {n!r}")
            if colour.get(n) == 2:
                return
            colour[n] = 1
            for d in (self.nodes[n].depends_on if n in self.nodes else []):
                walk(d)
            colour[n] = 2

        for nid in list(self.nodes):
            walk(nid)

    # --- the two questions the human asked 22 times --------------------------------

    def open_leaves(self) -> list[Node]:
        """Nodes ready to work NOW: not terminal, not blocked, every dependency proved.

        `blocked` is excluded deliberately, and the first version of this method got it
        wrong: `blocked` is not terminal (a decision can unblock it), so a bare
        `status not in TERMINAL` listed a named boundary as ready work. That is the exact
        failure the status was invented to prevent — the last run re-attacked its own
        boundaries under new task ids, 34 times for one family. A boundary needs a
        decision, not another agent, so it is reported by `state` under its own heading
        and never offered to the scheduler.
        """
        return [
            n for n in self.nodes.values()
            if n.status not in TERMINAL and n.status != "blocked"
            and all(self.nodes[d].status == "proved" for d in n.depends_on if d in self.nodes)
        ]

    def census(self) -> dict[str, int]:
        # `out[n.status] += 1` raised KeyError on any status outside the enum, which took
        # `dag state` and `dag render` down with it. Defensive on purpose: a view must
        # still render when the data is wrong, or the operator loses the one thing that
        # would show them it is wrong.
        out = dict.fromkeys(STATUS, 0)
        for n in self.nodes.values():
            out[n.status] = out.get(n.status, 0) + 1
        return out
