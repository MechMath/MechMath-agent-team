# ADR 0017: Long-Term Memory Cards in the Collector KB — Card Family and Schema

## Status

Accepted — **implemented, except the one-time live migration.** P1 (the
`Experience_*` schema in `cli_tools/_memory/experience.py` + `collector_write.py --card-type`) and
P3 (`collector_summary.py` `## Experience` parse, read through
`memory.py --tier kb`) are implemented and tested. P2's migration tool
(`migrate_memory_md.py`) is delivered and tested in a scratch dir but **not
applied to the live KB / `memory.md`** — that is a human-run step, since it
mutates the external KB and reformats the curated `memory.md`.

> **This ADR has been narrowed** (see the convergence after ADR 0016's revisions).
> The memory system's **tier model, recall path, unified entry, candidate-card
> aggregation, and tool defects (`collector_write.py` bug)** have all been folded
> into **ADR 0016**; this ADR no longer repeats them. The settled overall division
> is **"full content in the KB, index (recall) in `memory.md`"** (0016 §3.3). After
> that, only **one thing 0016 leaves undetailed, and which is inherently KB-side**,
> remains for this ADR:
>
> **When a long-term experience card's full body is stored in the Collector
> (KB-Manager), which card family and what frontmatter schema does it use.** I.e.
> the "what does the KB card actually look like" inside "full content in the KB".
>
> This corresponds to user fix-point **#1** ("can memory be folded into the
> Collector") — its **content-unification-into-the-KB** thrust is absorbed by 0016;
> this ADR only lands its concrete form in the KB card-family system.

## Background (only the slice this ADR cares about)

0016 has settled: recall of long-term negative constraints goes through the local
resident `memory.md` index (a read-only projection of KB content), while **full
cards live only in the KB, read on demand**. What remains is purely KB-side:

- Collector's existing card families (confirmed in code): `Concept_`, `Source_`,
  `Lean_`, `Analysis_`, `Conjecture_`, including `Analysis_*ErrorKnowledge` and
  `Analysis_*CounterexampleKnowledge` pages.
- The paper (§3.3) treats the KB-Manager itself as a memory graph whose cognitive
  layer holds `PartialProof` and `Obstruction` cards. Long-term experience/negative-
  constraint cards should land as **first-class citizens of this card-family
  system**, not float outside as a lone `memory.md` — `memory.md` is only their
  rendered recall index (0016 §3.3).
- **One inconsistency to unify:** 0016 §3.3 sketched a frontmatter for long-term
  cards (`id: neg-<slug>` / `kind: negative-constraint | heuristic-threshold` …),
  while this ADR's early draft gave another (`Experience_*`, `type: experience` /
  `kind: … | tactic | episode` …). Since "full content lives in the KB", the
  long-term full card in the KB must have **exactly one schema**. §2 below merges
  the two into a single definition; both `memory.md` and 0016 §3.3 defer to it.

## Decision

### 1. Long-term cards are the Collector's `Experience_*` card family

Keep ADR 0015's "declarative / procedural" boundary, both hosted in the Collector
(the single content authority), mapped to card families:

| Knowledge kind | Card family (Collector `wiki/`) | Content authority | Recall path |
|----------------|----------------------------------|-------------------|-------------|
| Declarative (exact statements, definitions, sources, verified lemmas, counterexample instances) | `Concept_`, `Source_`, `Lean_`, `Conjecture_` | KB (sole) | on-demand read via query workflow |
| Experiential/procedural (negative constraints, heuristic thresholds, error modes, dead ends) | `Analysis_*ErrorKnowledge`, `Analysis_*CounterexampleKnowledge`, and the new **`Experience_*`** family | KB (sole) | **local `memory.md` resident index** (0016 §3.3), then read the full card back in the KB on a hit |
| Session-local (notation binding, branch state, this run's findings) | **not in the KB**, stays in `workspace_memory.py` | workspace | local index |

The "pointer, not inline statement" invariant (experience cards reference
declarative cards via `[[Concept_X]]` / `2401.12345 Thm 3.2`, never copy the
statement text) is detailed in 0016 §3.4 and enforced naturally by this table.
One KB, no drift.

### 2. Unified `Experience_*` card schema (merging 0016 §3.3's `neg-*` draft)

The long-term full card lives in the KB with the frontmatter below; **this is the
sole authoritative format for long-term cards, absorbing 0016 §3.3's `neg-*` draft
— this section is authoritative.** The `memory.md` resident index = the
`trigger + statement` two lines rendered from these cards (`memory render-longterm`,
0016 §3.7).

```yaml
---
type: experience                                    # experience | error | obstruction
kind: negative-constraint | heuristic-threshold     # the two load-bearing kinds, consistent with 0016 §3.3
id: neg-<slug>                                       # stable id (per 0016 §3.3 naming)
statement: <the boundary, one line>                  # load-bearing (rendered into the memory.md index)
trigger: <structural cue that should recall this card>   # load-bearing (recall; rendered into the memory.md index)
why: <the failure it prevents>
failure_modes: <when this card itself misleads / when it does not apply>   # load-bearing (honesty)
provenance: [verifier-block | human-correction | ce-hunter | regulator]
scope: <applicable domain, or "general">
refs: [[Concept_X]], 2401.12345                       # pointers only, never the statement (0016 §3.4)
used:                                                 # append-only usage record
  - <problem_id> <stage> ✓|✗ (one-line note)
---
<one-line claim / the boundary>
```

`memory.md`'s existing ~35 error rules are **migrated once** into `Experience_*`
cards (`kind: negative-constraint`), full cards into the KB; `memory.md` then
becomes the resident recall index rendered from these cards (**not a second store,
not the content authority** — see 0016 §3.3's "read-only projection" positioning).

### 3. `collector_summary.py`'s `## Experience` section

Extend `collector_summary.py` to add a `## Experience` section alongside
`## Concepts` / `## Analyses & Comparisons`, **used only as a KB-side browse/audit
view + one of the inputs to `memory render-longterm`**, **not as the model's recall
path** (recall always goes through `memory.md`, 0016 §4/§3.3).

## Non-goals (everything else defers to 0016)

- **Do not repeat what 0016 already settled**: the tier model, recall mechanism,
  unified `memory.py` entry, candidate-card production/aggregation (the
  Orchestrator's), the `collector_write.py` bug fix, the "pointer, not inline"
  detail — **all in ADR 0016.**
- Do not build a second knowledge store (content layer): see 0016 §5.
- Do not implement the Collector's Ingester/ingest pipeline here (it belongs to the
  KB-Manager project); this ADR only defines the long-term card's **family and
  schema** in the KB.

## Phased plan (all KB card-family related)

- **P1** — Define and document the unified `Experience_*` schema (§2); add a
  `--card-type`/frontmatter convention to `collector_write.py` to declare the
  target family. *(docs + cli_tools; the bug fix itself is 0016 P0)*
- **P2** — Migrate `memory.md`'s ~35 rules → `Experience_*` cards (full cards into
  the KB); `memory.md` becomes the rendered index (rendering logic is 0016 §3.7's
  `memory render-longterm`). *(one migration)*
- **P3** — `collector_summary.py` parses the `## Experience` section (§3).
  *(cli_tools)*

## Open questions (within the KB card-family scope)

- **Q1 `Experience_*` vs `Analysis_*ErrorKnowledge` overlap**: both families hold
  error knowledge. Reuse the existing `Analysis_*ErrorKnowledge` convention instead
  of adding an `Experience_` prefix? (fewer types vs clearer recall semantics.)
- **Q2 where heuristic thresholds go**: if the KB is partitioned by project and a
  threshold is cross-project (the paper puts thresholds in long-term memory), a
  per-project wiki may not be the right home, or a `general` scope is needed.
  (Echoes 0016 §7 Q5.)

> **Other former open questions migrated/closed:** whether Reflector is a separate
> role, recall-carrier confirmation, etc. are all folded into 0016 (§7 Q2, and the
> closed Q4).
