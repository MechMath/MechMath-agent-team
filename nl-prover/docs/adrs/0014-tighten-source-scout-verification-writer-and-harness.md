# ADR 0014: Tighten Source Scout, Verifier, Writer, and Harness

## Status

Accepted for implementation on `experimental`.

## Context

This upgrade addresses five related problems:

1. Searcher often fails to find theorems that a human expert can
   locate by tracing the literature.
2. The structural verifier has high orchestration cost and low practical value;
   format errors are not the main failure mode.
3. AhhProver has useful paper-card and parallel fan-out discipline that we can
   borrow without adopting its fixed pipeline.
4. Writer output quality is inconsistent across runs.
5. The harness has accumulated prompts, skills, CLI tools, and state files that
   need a tighter separation of responsibility.

ADR text is for human design discussion. Executable behavior must be reflected
in `AGENTS.md`, prompts, skills, CLI references, and deterministic tools.

## Decision

### 1. Keep The Name, Change Searcher's Responsibility

Keep the custom-agent name `Searcher`. Its responsibility expands
from theorem-package auditing to literature tracing plus theorem-package
auditing.

The new workflow is:

```text
problem / target reading / active route context
  -> source-theorem obligation
  -> keyword extraction
  -> local reference scan
  -> Matlas / arXiv / Collector query
  -> candidate paper cards
  -> citation-chain tracing
  -> statement extraction
  -> source theorem package
```

The Scout must not merely run one search query and fill a template. It should
act more like a human literature searcher:

- extract terms from the target, route, blocker, and theorem obligation;
- read local references and existing query outputs first;
- use Matlas for precise theorem statements when possible;
- use arXiv and papers for surveys, related work, and reference chains;
- trace at least one relevant citation layer when a paper is plausible, and
  more when the theorem appears to be inherited from earlier work;
- record which papers were retained or rejected and why;
- distinguish original theorem statements from secondary mentions;
- say whether the next move is another keyword family, citation tracing, local
  derivation, definition audit, route change, or human input.

The primary output remains `routes/source_theorem_<N>.md`. The Scout may also
write literature-tracing artifacts:

```text
routes/source_literature_trace_<N>.md
references/papers/<paper_id>/note.md
references/papers/<paper_id>/statements.jsonl
references/papers/<paper_id>/citation_trail.md
```

These paper cards are AI-facing reference summaries, not human UI features.

### 2. Use Layered Search, Not Infinite Web Search

Search is layered:

1. workspace local references via `reference_extract.py`;
2. existing query outputs via `query_index.py`;
3. Collector summary and narrowly scoped Collector reads;
4. Matlas for exact theorem statements;
5. arXiv for papers, surveys, related work, and reference chains;
6. broader web sources only as a supplement;
7. citation-chain tracing from plausible papers.

Every layer attempted must leave a record. A route is not exhausted just
because a single search call failed or returned sparse results.

Memory use is lightweight: Searcher should read only recent failed
paths, source findings, and local-reference memory that is relevant to the
current obligation.

### 3. Remove Structural Verification Entirely

Remove the mandatory structural verifier gate. Do not keep a compatibility
`--mode structural` in `review_packet_lint.py`, and do not use
`PROCEED_TO_DETAILED`.

Verifier now produces one full review packet per check. That packet still
contains the information previously split between structural and detailed
verification:

- statement preservation;
- problem-reading and normalization audit;
- dependency and theorem ledger;
- definition and source-theorem audit;
- load-bearing obligation ledger;
- finite-case or computation audit when applicable;
- adversarial route audit;
- open obligations;
- merge blockers;
- next action.

This is not a weaker verification standard. It is one stronger Verifier pass
instead of two prompt layers.

### 4. Borrow AhhProver Selectively

Borrow:

- per-paper cards or directories for reusable paper notes;
- clear per-lemma or per-route fan-out discipline, where the Orchestrator only
  dispatches and collects state;
- the idea of a centralized human-hint entry point, but not in this round.

Do not borrow:

- AhhProver's per-problem workspace structure;
- a fixed sketch-to-lemma-to-proof pipeline;
- proof writer internal verification committees;
- compiling every intermediate proof stage to PDF;
- infinite self-repair loops inside a lemma worker.

NL-Prover remains a specialist-agent harness with Orchestrator routing,
branch queues, and file-based handoffs.

### 5. Tighten Writer Modes

Writer remains a presentation specialist, not a proof-search agent. It is used
in two situations:

1. after a proof is mathematically complete and Refiner has been accepted,
   rejected, or explicitly skipped;
2. when the human asks for an article, local rewrite, progress explanation, or
   pause/stop report.

`FULL_ARTICLE` and `COMPLETE_PROOF` are treated as complete-proof presentation
modes. They must use theorem/lemma/proof structure, keep hypotheses visible,
expand definitions and dependency bridges, and avoid agent-run history.

> **Amendment (2026-08-25).** The `PROGRESS_NOTE` paragraph immediately below is
> **superseded by ADR 0021 §B and ADR 0025 §B**, and is kept as the record of
> what was decided here. Two things in it are now wrong: the output type is
> named `PROGRESS_NOTES` (ADR 0021 §C), and its four-way split — verified facts /
> candidate facts / open blockers / next mathematical evidence — is not the
> current section list. Three incompatible lists existed in the record
> (ADR 0011 §3's five bullets, this paragraph's four-way split, ADR 0021 §B's
> five numbered sections); **ADR 0021 §B is the only live one**, its SSOT is
> `.agents/skills/article-writing/references/progress-note.md`, and the separate
> six-heading summary format of ADR 0025 lives in `prompts/writer.md`. The
> sentence after the paragraph — Writer must never present restartable state, a
> missing theorem, or a failed tool call as a final proof or final obstruction —
> is not amended and still holds.

`PROGRESS_NOTE` is still mathematical prose. It must begin from the precise
statement, scope, hypotheses, and notation. It must separate verified facts,
candidate facts, open blockers, and next mathematical evidence. It may mention
route history only as support for a blocker, not as the main narrative.

Writer must never present restartable state, a missing theorem, or a failed
tool call as a final proof or final obstruction.

### 6. Tighten The Harness Boundary

Keep the responsibility split:

- `AGENTS.md`: hard invariants and entry points;
- prompts: role contract and output format;
- skills: when to use a workflow, cookbook, and concrete tool commands;
- CLI: deterministic checks, indexes, and transforms;
- ADRs: design history and decisions.

Implementation should remove or update current structural-verifier references
from executable prompt/skill/tooling so the harness has one verification model.

## Implementation Order

1. Update Searcher and the `source-theorem` skill with literature
   tracing and paper-card output.
2. Remove structural verifier mode from Verifier prompt, verification skill,
   human-review, orchestration references, and review-packet lint.
3. Tighten Writer prompt and article-writing skill modes.
4. Clean up conflicting harness references without rewriting historical ADRs.
