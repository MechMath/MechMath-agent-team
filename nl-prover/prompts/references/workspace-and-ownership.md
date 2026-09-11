# Workspace and Ownership

Each problem lives in `../data/workspace/<problem_id>/`.

`<id>` in the table below is a path under `lemmas/`, not necessarily one
segment. Runs group lemmas by branch — `lemmas/<branch>/<lemma>/statement.md` —
and that is fine; the owner of a file is decided by its name inside the lemma
directory, not by how deep the lemma sits. Every reference to a lemma elsewhere
(a `Depends-on:` line, a STATUS.md row, a packet) names the lemma alone, and the
tools resolve it.

Core files and directories:

```text
proof.tex
problem.md
STATUS.md
verification/
recovery/
routes/
sketch/
lemmas/<lemma_id>/
queries/
references/
memory/
presentation/
refinement/
writer/
logs/
```

Ownership:

| File or directory | Owner |
|-------------------|-------|
| `proof.tex`, `STATUS.md` | Orchestrator |
| `problem*.md` | Human, except explicit mechanical copy/format requests |
| `recovery/route_recovery_<N>.md` | Orchestrator or assigned recovery owner |
| `recovery/route_history.md` | Orchestrator or Regulator when assigned |
| `recovery/regulator_decision_<N>.md` | Regulator |
| `routes/brainstorm_<N>.md` | Explorer |
| `routes/synthesizer_<N>.md` | Synthesizer |
| `routes/counterexample_<N>.md` | CE-Hunter |
| `routes/proof_review_*.md`, `review/proof_review.md` | Orchestrator workflow artifact or Regulator when assigned |
| `routes/source_theorem_<N>.md` | Searcher |
| `routes/source_literature_trace_<N>.md` | Searcher |
| `routes/definition_audit_<N>.md` | Auditor |
| `routes/computation_audit_<N>.md` | Code Executor |
| `sketch/research_notes.md`, `sketch/decomposition*.md` | Sketcher |
| `sketch/target_contract*.md` | Sketcher or target-reading workflow |
| `sketch/revision_*.md` | Sketcher or Refiner |
| `sketch/plan_refinement.md`, `sketch/decomposition_refined.md`, `sketch/refined_lemmas/*` | Refiner |
| `sketch/*_report.md`, `sketch/*_review_packet.md`, `sketch/*_verdict.md` | Verifier |
| `lemmas/<id>/statement.md` | Sketcher or selected refined plan |
| `lemmas/<id>/generator/*` | Generator |
| `lemmas/<id>/verifier/*` | Verifier |
| `verification/<name>/*` | Verifier — packets for checks that are not a lemma's (obstruction, plan logic, source-theorem) |
| `queries/index.md`, `queries/<query_id>/request.md`, `queries/<query_id>/status.md` | Orchestrator |
| `queries/<query_id>/kb-manager.md` | KB-Manager |
| `queries/<query_id>/index.json`, `queries/<query_id>/index.md` | `search.py index` mechanical output |
| `references/index.json`, `references/index.md`, `references/.extracted/*` | `workspace.py references` mechanical output |
| `references/papers/<paper_id>/note.md`, `references/papers/<paper_id>/statements.jsonl`, `references/papers/<paper_id>/citation_trail.md` | Searcher or assigned reference owner |
| `references/ledger.jsonl` | dual owner: Searcher (provenance fields) / fresh Verifier (trust field); `cite_key` mechanical via `refs-bib` (ADR 0019) |
| `references/refs.bib` | `workspace.py refs-bib` mechanical output (ADR 0019) |
| `knowledge/findings.md`, `knowledge/map.md`, `knowledge/leads.md` | Searcher (ADR 0018 digest) |
| `knowledge/frontier.jsonl` | `search.py frontier` mechanical output, Searcher-driven (ADR 0018) |
| `memory/*.jsonl`, `memory/index.json`, `memory/index.md` | `memory.py` local-tier mechanical output |
| `presentation/index.json`, `presentation/index.md`, `presentation/static/*` | `workspace.py presentation` mechanical output |
| `refinement/original_*` | Orchestrator |
| `refinement/proof_refinement.md`, `refinement/proof_refined.tex`, `refinement/decomposition_refined.md` | Refiner |
| `refinement/verifier_*`, `refinement/review_packet.md`, `refinement/verdict.md` | Verifier |
| `writer/article_candidate.tex`, `writer/local_revision_candidate.tex`, `writer/progress_notes.tex` | Writer |
| `writer/style_profile.md`, `writer/article_plan.md`, `writer/revision_notes.md` | Writer |
| `proof.pdf`, `progress_notes.pdf` | Orchestrator mechanical export from Writer PDF |

## Shadow and parallel-attempt targets

A stalled dispatch is replaced by a **shadow** at a suffixed path, and a lemma
that keeps failing may get **two Generators at once** at suffixed paths:

| Pattern | Owner |
|---------|-------|
| `<owned_path>_shadow<K>.md` | the same role as `<owned_path>` |
| `lemmas/<id>/generator/proof_v<N>b.md` | Generator, the parallel second attempt |

The suffixed file is owned by whoever owns the file it shadows, so the ownership
model does not change: **still exactly one writer per file.** That is the whole
point of giving the shadow its own path rather than letting two agents race on one.

Exactly one of a shadow pair is adopted and the other is discarded unread.
**Never splice two independent attempts together** — that is authoring
mathematics, and the Orchestrator does not author mathematics.

Agents may read context broadly but should write only owned files. The
Orchestrator may merge already verified content into `proof.tex`, update
`STATUS.md`, route queries, run mechanical tools, and write recovery/route
state. It must not author, revise, simplify, or repair mathematical proof text
or target contracts itself. It must also route reader-facing article prose,
local rewrites, and progress notes to Writer instead of drafting them privately.
