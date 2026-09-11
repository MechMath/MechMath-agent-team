---
name: memory-routing
description: "Use when deciding where a new piece of knowledge belongs: which of the three memory tiers a result/observation/lesson enters, or whether to write the KB inbox vs the local workspace tier vs the long-term memory. Trigger on 'record this', 'remember this', 'should this go to memory / the KB / memory.md', a verifier FAIL or human correction that yields a reusable lesson, or a proven fact worth keeping."
---

# Memory Routing

NL-Prover has **three memory tiers** (ADR 0016). Before writing anything down,
classify it with the rule below so it lands in exactly one tier — and reach every
tier through the single entry `cli_tools/memory.py` (plus `memory.py inbox-write`
for the KB inbox write). Never invent a fourth store.

| Tier | Scope | Holds | Entry |
|------|-------|-------|-------|
| local | this workspace | branch state, explored routes, dead ends, notation | `memory.py refresh/read/append --tier local` |
| long-term | across problems | distilled negative constraints / heuristic thresholds ("don't do X") | resident `memory.md`, rendered from repo-local `memory/experience/*.md` |
| KB | across problems | dense facts: statements, verified lemmas, counterexamples, audited sources | inbox via `memory.py inbox-write` → human/formal check → wiki |

## The delete-the-object test (P1 vs P2)

Delete the problem-specific concrete objects from the candidate and see what
remains:

- What remains is essentially **a statement / object / number / theorem** (delete
  the objects and nothing is left) → it is a **fact** (P2 → KB).
- What remains is a reusable **"how to do / how not to do / threshold
  distinction"** (still holds after deleting the objects) → it is a **negative
  constraint / experience** (P1 → long-term).

Mechanical boundary check: `uv run python cli_tools/memory.py card-lint <file>
[--fact]` lints a candidate card / fact for the long-term vs KB boundary (e.g. a
statement-shaped card that copied a theorem, or a "fact" that is really a negative
constraint). Use it to catch a mis-tiered card before it is promoted.

## Decision tree

```
Is it a concrete math fact, theorem statement, verified lemma, counterexample
instance, or dense computation result (P2)?
    -> yes: KB. Do NOT write the wiki directly. Write the inbox, declaring the
       target card family so the Ingester can file it:
       uv run python cli_tools/memory.py inbox-write --content "<card>" \
         --filename "<problem_id>_<slug>.md" --card-type Concept_
       Enters the wiki only after human check or formal (Lean) check + ingest.

Is it valid only within the current problem (notation binding, local convention,
this workspace's exploration history)?
    -> yes: local tier. It is already an artifact in your own directory; the
       Orchestrator sediments it with:
       uv run python cli_tools/memory.py refresh <workspace>
       (or `memory.py append <workspace> --channel <c> --source <f> --kind <k>`
       for an artifact the refresh glob misses).

Is it a transferable behavioral boundary or heuristic threshold ("don't do X",
"interval A != interval B"; still holds after deleting the objects) (P1)?
    -> yes: long-term. Do NOT hand-edit memory.md and do NOT stuff it into the KB
       as a recall path. Emit a *candidate* card (see below); the Orchestrator
       promotes candidates into memory/experience/ before every stop.

otherwise -> do not memorize (transient noise).
```

## Emitting a long-term candidate card (P1)

Write a card whenever a run produces something that could apply to another
problem. Two occasions, weighted equally:

- **A route worked.** A mechanism, a way of choosing coordinates, a duality, a
  reduction, an identification of what an object really is — anything you would
  want to be reminded of on a similar problem.
- **A route failed** in a way that generalises: a `verifier` FAIL, an obstruction,
  a human correction.

The second occasion is the only one earlier versions of this file described, and
the resident tier ended up 100% prohibitions as a result. It is not a prohibition
list; it is memory.

**Admission test, and the only one:** could this be useful on a different
problem? Everything else — how the run went, what the artifact was called, how
confident you are — is irrelevant to it. Content that only makes sense on this
problem is written with `scope: this-problem-only`: it stays on disk and stays
retrievable, but does not enter the every-cycle read set.

The responsible specialist records a candidate card **through the tool**:

```bash
uv run python cli_tools/memory.py candidate <workspace> \
  --agent verifier --run-id <runid> \
  --kind negative-constraint \
  --statement "<what was learned, one line>" \
  --trigger  "<structural cue that should bring it back>" \
  --why      "<the conditions under which it applies>" \
  --failure-modes "<when this card itself misleads>" \
  --scope class-level
```

It appends to `memory/candidates/<agent>-<runid>.jsonl` and validates before it
writes. **Do not hand-edit that file.** It used to be written by hand — the one
ledger in the harness whose format lived only in a code fence beside the
instruction. A malformed line is not refused where it is written; it is silently
skipped at aggregation, after the run that knew the lesson is over.

`kind` is `transferable-idea` or `negative-constraint`; `scope` is `class-level`
or `this-problem-only`. Only `class-level` is rendered into the resident
`memory.md`.

`trigger`, `why` and `failure_modes` are all required, and the tool refuses a
card without them. A card that cannot be recalled only makes the resident file
longer. A card that cannot say **when it applies** fires on the wrong problem,
and one that cannot say **when it misleads** is a prohibition nobody can ever
argue with — which is how a growing list of "do not" closes off the search.

Fields are pointers, never inline statements (Experience_* schema, ADR 0017 §2);
use `--refs "[[Concept_X]]"` rather than quoting a theorem.

If the FAIL/obstruction/correction yields nothing generalizable, record that
explicitly instead — same tool, and it satisfies the production-side lint:

```bash
uv run python cli_tools/memory.py candidate <workspace> \
  --agent verifier --run-id <runid> \
  --no-constraint "<why this failure has no transferable lesson>"
```

Before **every** stop — not only a completed proof — the Orchestrator promotes
the candidates. That is this skill's step, and it is one of seven:

```
uv run python cli_tools/memory.py aggregate-candidates <workspace>
```

**The full pre-stop sequence lives in
`.agents/skills/nl-prover/references/stop-conditions.md` and is not restated
here.** This block used to carry a two-step version — promote, then `gate stop`
— which omitted `memory.py refresh`. A run following it verbatim fails `gate
stop` on index freshness, caused by the step the shortcut dropped. A sequence
worth abbreviating is a sequence worth linking to.

`aggregate-candidates` dedups the run's cards, dedups them again against the
cards already in `memory/experience/`, writes the survivors there, and re-renders
`memory.md` — so a lesson learned in one run is resident in the next with no
inbox hop and no human promotion step. Skipping it strands the lessons in
`memory/candidates/`, which is why `gate stop` checks it mechanically (ADR 0022).
A run that recorded failures and produced no card at all fails the gate: if there
is genuinely nothing to learn, write the `no_constraint` marker above and say why.

A card without a `trigger` is rejected rather than stored — it could never be
recalled, so it would only grow `memory.md` without ever firing. Keep the file
under its 100-line cap by merging near-duplicate constraints in
`memory/experience/` and re-rendering.

## Hard rules

- Agents never write the KB wiki directly. Math facts go `inbox -> check -> wiki`.
- Long-term recall is the resident `memory.md` (read every cycle), never a KB
  pull. `memory.md` is generated; edit `memory/experience/*.md` and re-render.
- Experience cards hold **pointers** (`refs: [[Concept_X]]`), never copied
  theorem statements. Declarative content stays authoritative in the KB, which is
  also why the cards themselves are safe to keep locally.
- The Orchestrator, not a script, decides which candidates to keep/merge;
  `aggregate-candidates` dedups and promotes, but curating and compacting
  `memory/experience/` remains the Orchestrator's call.
