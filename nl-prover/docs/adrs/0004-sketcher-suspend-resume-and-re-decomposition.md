# ADR 0004: Sketcher Suspend/Resume and Re-Decomposition Protocol

## Status
Accepted

## Context

Problem decomposition is not a one-shot task. A Sketcher may produce a decomposition that looks clean on paper but turns out to be intractable for one or more lemmas. When a Generator gets stuck or a Verifier repeatedly rejects proofs, the system needs a mechanism to revise the decomposition without losing work already completed on other lemmas.

The Archon project handles this via its Plan agent, which runs repeatedly between Prover rounds, reading results and adjusting objectives. The Prover project's Blueprint Agent calls Gemini to refine decompositions when proof agents exhaust their budgets. Both demonstrate that **adaptive re-planning is essential**.

For NL-Prover, we need to balance:
- **Efficiency** — don't re-decompose when a simple proof revision would suffice
- **Freshness** — when the Sketcher is re-activated, it should have full context about what went wrong
- **Stability** — re-decomposition should affect only the problematic parts, not invalidate already-verified lemmas

## Decision

### Sketcher Lifecycle: Suspend/Resume

The Sketcher is **suspended** (not destroyed) after initial decomposition:
- Its output files (`research_notes.md`, `decomposition.md`, `lemmas/*/statement.md`) remain in the workspace
- The Orchestrator remembers which problem the Sketcher was working on

When re-activated, the Sketcher receives:
1. The original problem context
2. A summary of current proof progress (from `STATUS.md`)
3. Specific failure context:
   - Which lemma(s) failed
   - Generator's `status.md` explaining why it's stuck
   - Verifier's `report_v<N>.md` showing what's wrong
4. An instruction to write `revision_<N>.md` with the updated decomposition

### Re-Decomposition Rules

1. **Preserve verified lemmas** — any lemma with Verifier PASS is locked. Re-decomposition cannot remove or modify it.
2. **Only restructure the problematic branch** — if lem:3 is stuck but lem:1 and lem:2 are verified, the Sketcher should only restructure what depends on or leads to lem:3.
3. **New lemmas get new IDs** — re-decomposition produces new lemma IDs (e.g., `lem:3a`, `lem:3b`), never overwrites existing ones.
4. **Dependency DAG is updated** — the revision must include an updated dependency graph that respects all locked lemmas.

### Revision File Format

```markdown
# Revision <N> — <reason>

## Trigger
- Lemma: lem:3
- Failure mode: Generator stuck after 3 attempts / Verifier rejected all 3 versions
- Key issue: <summary of why the approach failed>

## Changes
### Removed
- lem:3 (replaced by lem:3a, lem:3b)

### Added
- lem:3a: <statement> — uses: [lem:2]
- lem:3b: <statement> — uses: [lem:3a]

### Modified
- lem:4: dependency changed from lem:3 to lem:3b

## Updated Dependency DAG
lem:1 → lem:2 → lem:3a → lem:3b → lem:4 → main_theorem

## Rationale
<Why this restructuring should work where the original didn't>
```

### Escalation Thresholds

| Condition | Action |
|-----------|--------|
| Generator stuck (reports "stuck" in status.md) | Orchestrator re-activates Sketcher |
| Verifier rejects N times (N = max_attempts, default 3) | Orchestrator re-activates Sketcher |
| Sketcher revision also fails | Orchestrator reports to human with full context |
| Sketcher revised K times (K = max_revisions, default 2) | Orchestrator reports to human — problem may be genuinely hard |

## Consequences

### Pros
- **Adaptive** — the system can recover from bad decompositions without starting over
- **Incremental** — verified work is preserved, only broken parts are restructured
- **Traceable** — each revision is recorded with rationale, forming a history of the decomposition's evolution
- **Context-rich re-activation** — the Sketcher gets specific failure information, not just "try again"

### Cons
- **Complexity** — the Orchestrator must track which lemmas are locked, which are affected by re-decomposition, and how dependencies shift
- **Potential cascade** — restructuring one lemma may force changes to downstream dependencies
- **Sketcher context management** — re-activating a "suspended" Sketcher means re-reading all its prior output files, which costs tokens
