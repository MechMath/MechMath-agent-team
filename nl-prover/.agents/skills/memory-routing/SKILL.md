---
name: memory-routing
description: "Use when deciding where a new piece of knowledge belongs: which of the three memory tiers a result/observation/lesson enters, or whether to write the KB inbox vs the local workspace tier vs the long-term negative-constraint list. Trigger on 'record this', 'remember this', 'should this go to memory / the KB / memory.md', a verifier FAIL or human correction that yields a reusable lesson, or a proven fact worth keeping."
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

On a `verifier` FAIL, `regulator` classification, `ce-hunter` obstruction, or a
human correction, the responsible specialist appends a candidate card (one JSON
object per line) to a managed artifact:

```
memory/candidates/<agent>-<runid>.jsonl
```

Card fields (Experience_* schema, ADR 0017 §2 — pointers, never inline
statements):

```json
{"kind": "negative-constraint", "statement": "<one-line boundary>",
 "trigger": "<structural cue to recall it>", "why": "<failure it prevents>",
 "failure_modes": "<when this card itself misleads>",
 "provenance": ["verifier-block"], "scope": "general", "refs": ["[[Concept_X]]"]}
```

If the FAIL/obstruction/correction yields nothing generalizable, record that
explicitly instead (this satisfies the production-side lint):

```json
{"no_constraint": "<why this failure has no transferable lesson>"}
```

Before **every** stop — not only a completed proof — the Orchestrator promotes
the candidates, then clears the stop gate:

```
uv run python cli_tools/memory.py aggregate-candidates <workspace>
uv run python cli_tools/gate.py stop <workspace> [--verified-proof]
```

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
