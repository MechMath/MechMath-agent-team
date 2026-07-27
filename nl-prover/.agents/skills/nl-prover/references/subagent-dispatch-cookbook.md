# Subagent Dispatch Cookbook

Use the smallest specialist that owns the current blocker. Do not default to
Sketcher/Generator/Verifier when another prompt owns the work.

| Situation | Dispatch | Advantage | Output | Next |
|-----------|----------|-----------|--------|------|
| No generator-ready DAG, route unclear, or repeated strategy failure | Explorer x2-3 with distinct constraints | Produces diverse mechanisms and prevents single-route overfitting | `routes/brainstorm_<N>.md` | Synthesizer |
| Multiple candidate routes or conflicting advice | Synthesizer | Ranks, merges, rejects duplicates, and builds a queue | `routes/synthesizer_<N>.md` | Sketcher or active queue |
| Failure class or owner unclear | Regulator | Separates proof-local, DAG, source, definition, route, and obstruction blockers | `recovery/regulator_decision_<N>.md` | Active dispatch plus queued alternates |
| Proof attempt locally incomplete while statement and plan look sound | Generator | Repairs proof text without changing the global plan | `lemmas/<id>/generator/proof_v<N>.md` | Fresh Verifier |
| Lemma statement, dependency edge, final bridge, or DAG incomplete | Sketcher or Refiner | Repairs canonical plan instead of forcing proof text | `sketch/revision_<N>.md` or refined plan | Plan verification |
| Named theorem, folklore result, classification, theorem package, or major estimate carries the proof | Searcher | Traces literature, audits exact statement, source route, preconditions, and circularity | `routes/source_theorem_<N>.md` | Sketcher/Generator |
| Specialized notation, named family, convention, or target reading is unstable | Auditor or target-reading workflow | Prevents guessed definitions from supporting proof or obstruction | `routes/definition_audit_<N>.md` or `sketch/target_contract.md` | Sketcher/Verifier |
| KB-Manager/local knowledge may resolve a source or definition | KB-Manager through query workflow | Grounds work in local knowledge without polluting proof text | `queries/<id>/kb-manager.md` | Source/definition owner |
| Boundary failure, degenerate case, possible falsehood, or impossible precondition appears | CE-Hunter, then Regulator using proof-review workflow | Attacks the target while preventing premature terminal claims | `routes/counterexample_<N>.md` plus optional proof-review artifact | Verifier only if Regulator says obstruction-ready |
| Finite enumeration, exhaustive check, or computation evidence is load-bearing | Code Executor | Audits finite/computed evidence before it carries proof weight | `routes/computation_audit_<N>.md` | Verifier |
| Complete proof has passed fresh verification | Refiner | Shortens accepted proof while preserving fallback | `refinement/proof_refined.tex` | Fresh Verifier |
| Verified proof needs final presentation, local rewrite is requested, or the human asks for progress reporting | Writer using article-writing skill | Keeps exposition separate from proof search and prevents Orchestrator from authoring mathematical prose | `writer/article_candidate.tex`, `writer/local_revision_candidate.tex`, or `writer/progress_note.tex` | Orchestrator compiles/exports PDF; Verifier only if mathematics may change |

## Diversity Constraints

When launching multiple Explorers or Sketchers, assign distinct constraints:

- `direct-elementary`: avoid heavy theorem packages where possible.
- `known-theorem`: search for a load-bearing known theorem and list source
  risks.
- `counterexample-risk`: attack the statement through boundary cases and
  obstruction shapes.
- `bypass-current-dag`: avoid the current decomposition entirely.
- `minimal-lemma`: minimize the number of lemmas and final assembly steps.
- `max-verifiability`: prefer obligations that Verifier can check locally.
- `construction-first`: start from the key object, map, invariant, or witness.
- `obstruction-first`: start from no-go theorems or global invariants.

Do not launch two agents with nearly identical constraints in the same round.

## Prompt-Only Specialization

Different subagents remain useful even when they share the same base model. The
separation comes from:

- different input files;
- different allowed write targets;
- different forbidden actions;
- different output schemas;
- different success and failure criteria;
- different completion markers;
- different cognitive role in the route queue.

The goal is not more votes. The goal is to prevent the Orchestrator from
privately doing route design, proof repair, verification, source auditing, and
counterexample search, or article writing in the same context.
