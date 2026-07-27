---
name: memory-routing
description: "Use when deciding where a new piece of knowledge belongs: which of the three memory tiers a result/observation/lesson enters, or whether to write the KB inbox vs the local workspace tier vs the long-term negative-constraint list. Trigger on 'record this', 'remember this', 'should this go to memory / the KB / memory.md', an F-Reviewer rejection, a gate failure, or a human correction that yields a reusable lesson, or a proved helper lemma worth keeping."
---

# Memory Routing

FL-Prover has **three memory tiers**. Before writing anything down,
classify it with the rule below so it lands in exactly one tier — and reach every
tier through the single entry `cli_tools/memory.py` (plus `memory.py inbox-write`
for the KB inbox write). Never invent a fourth store.

| Tier | Scope | Holds | Entry |
|------|-------|-------|-------|
| local | this workspace | branch state, explored routes, dead ends, notation | `memory.py refresh/read/append --tier local` |
| long-term | across problems | distilled negative constraints / heuristic thresholds ("don't do X") | resident `memory.md`, rendered from `memory/experience/*.md` cards |
| KB | across problems | dense facts: proved helper lemmas and their exact statements, Mathlib gaps, audited sources | inbox via `memory.py inbox-write` → human/formal check → wiki |

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
       aggregates candidates at run-end.

otherwise -> do not memorize (transient noise).
```

## Emitting a long-term candidate card (P1)

On an `f-reviewer` rejection, a `regulator` classification, a gate failure that
cost a wave, or a human correction, the responsible specialist appends a
candidate card (one JSON
object per line) to a managed artifact:

```
memory/candidates/<agent>-<runid>.jsonl
```

Card fields (`Experience_*` schema — pointers, never inline statements):

```json
{"kind": "negative-constraint", "statement": "<one-line boundary>",
 "trigger": "<structural cue to recall it>", "why": "<failure it prevents>",
 "failure_modes": "<when this card itself misleads>",
 "provenance": ["f-reviewer-reject"], "scope": "general", "refs": ["[[Concept_X]]"]}
```

If the FAIL/obstruction/correction yields nothing generalizable, record that
explicitly instead (this satisfies the production-side lint):

```json
{"no_constraint": "<why this failure has no transferable lesson>"}
```

At run-end the Orchestrator dedups and folds candidates into the inbox:

```
uv run python cli_tools/memory.py aggregate-candidates <workspace>
```

Promotion of a candidate into a resident long-term constraint is gated by a human
check; after promotion, re-render the resident list:

```
uv run python cli_tools/memory.py render-longterm
```

## Hard rules

- Agents never write the KB wiki directly. Math facts go `inbox -> check -> wiki`.
- Long-term recall is the resident `memory.md` (read every wave), never a KB
  pull. `memory.md` is generated; edit the cards in `memory/experience/` and
  re-render.
- Experience cards hold **pointers** (`refs: [[Concept_X]]`), never copied
  theorem statements (this is what keeps statement drift out of memory).
- The Orchestrator, not a script, decides which candidates to keep/merge;
  `aggregate-candidates` is only its deterministic pre-dedup helper.
