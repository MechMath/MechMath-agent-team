# ADR 0009: Rule-Governed Autonomous Orchestration

## Status

Proposed, experimental.

This ADR defines the orchestration direction for the `experimental` branch:
NL-Prover should stop modeling proof work as a fixed pipeline and instead
let the Orchestrator choose subagents and tools under hard rules.

## Context

The current system is often described as:

```text
read problem -> sketch -> verify plan -> prove -> verify -> merge -> gate -> summarize
```

This is clear and auditable, but research-level proof search is usually not
linear. A failure may come from a local proof detail, the DAG, a source theorem,
a definition, final assembly, or the entire route. A fixed pipeline tends to
compress all of these into "continue proving" or "resketch".

The current system is also not a normal retry mechanism. In practice, agents
are allowed to push forward; when a Generator or Verifier exposes a blocker
that cannot be repaired locally, the problem is classified and routed back to
Sketcher or another owner. The legacy `orchestrator.py` already follows this
shape: it reads `generator/status.md`, verifier verdicts, or review packets,
and if the result is not `done/PASS`, the lemma is marked `stuck` and rerouted.

This ADR therefore does not optimize for "more retries". The core operation is:

```text
failure -> classify -> choose the smallest owner -> change route or resketch if needed
```

## Decision

Adopt **Rule-Governed Autonomous Orchestration**.

Meaning:

- The Orchestrator is not driven by a fixed default pipeline.
- The Orchestrator owns global state, file permissions, merge authority, and
  final interpretation authority.
- Subagents are callable cognitive tools, not fixed pipeline stages.
- Verifiers and gates decide what may enter the canonical proof.
- The Regulator classifies failures and recommends next actions, but does not
  merge and does not verify mathematics.
- Existing agents such as Collector, Refiner, and Refiner remain part
  of the system.
- Important state must be written to files so the run is auditable and
  resumable.

Canonical state remains conservative:

- `proof.tex` is the authoritative proof document.
- `STATUS.md` is the current run summary.
- A stuck route, missing source theorem, missing definition, failed search, or
  exhausted attempt is not a mathematical final answer.

## Core Roles

### Orchestrator

The Orchestrator is the system owner.

It is responsible for:

- maintaining `STATUS.md` and `proof.tex`;
- creating workspaces, routing files, and spawning or resuming subagents;
- executing existing deterministic helper tools;
- running review-packet lint and completion gates;
- merging verified material;
- enforcing hard invariants;
- retaining final execution authority when recommendations conflict.

It is not responsible for:

- proving mathematics;
- verifying mathematics;
- diagnosing subtle proof failures by itself;
- guessing definitions or theorem preconditions;
- brainstorming novel routes by itself;
- accepting counterexamples by itself.

To keep the Orchestrator's context small, diagnostic agents must return short
routing cards: conclusion, paths, next owner, and a one-line blocker.

### Regulator

The Regulator is an independent custom agent, not a Verifier mode.

It is responsible for:

- reading failed proofs, verification reports, review packets, `STATUS.md`,
  recovery packets, and route history;
- classifying failures;
- recommending the next owner and file target;
- recording what must not be retried;
- recording reusable partial work;
- updating route history when needed.

The Regulator does not write `proof.tex`, does not merge, does not verify
proofs, and does not spawn subagents.

When route history shows repeated failures of the same kind, the Regulator
enters escalation mode. It may recommend changing the search mechanism: launch
more diverse branches, force counterexample search, build a source-theorem
portfolio first, forbid a repeatedly failed route class, or send the problem
back to target reading.

## Verification

The existing single-layer Verifier design is replaced by two Verifier modes:

```text
Structural Verification -> Detailed Verification
```

Initially these are two modes of the same Verifier custom agent. If the prompt
becomes too large, they may later become separate custom agents.

### Structural Verification

Structural verification decides whether an artifact deserves step-by-step
mathematical checking.

It checks:

- statement preservation;
- target contract compatibility;
- dependency coverage;
- final assembly coverage;
- source theorem and citation shape;
- definition and notation audit shape;
- load-bearing obligation ledger completeness;
- finite-case audit applicability;
- whether process failure is being presented as a proof conclusion;
- whether an open blocker is being presented as proof.

If structural verification fails, detailed verification does not run. The
failure is sent to the Regulator for classification.

### Detailed Verification

Detailed verification checks mathematical content:

- proof steps;
- theorem preconditions;
- dependency preconditions;
- case coverage;
- hidden hypothesis strengthening;
- finite or computation evidence;
- final implication.

If detailed verification fails, the Regulator classifies whether the failure is
proof-local or deeper.

### Structural Packet Contract

Structural verification must not invent a parallel packet format that drifts
from the existing review-packet contract.

Each structural check writes two files:

```text
structural_report_v<N>.md
structural_packet_v<N>.md
```

- `structural_report_v<N>.md` is prose for humans and later agents.
- `structural_packet_v<N>.md` is a compact, linter-friendly routing artifact.

`structural_packet_v<N>.md` should reuse the review-packet section names where
possible:

- `Inputs Checked`
- `Verdict Snapshot`
- `Problem Reading and Normalization`
- `Dependency and Theorem Ledger`
- `Definition and Source-Theorem Audit`
- `Load-Bearing Obligation Ledger`
- `Adversarial Route Audit`
- `Open Proof Obligations`
- `Blocking Issues`
- `Uncertainty`
- `Next Action`

Structural mode has its own allowed next actions:

```text
PROCEED_TO_DETAILED
REVISE_PROOF
REVISE_PLAN
SEARCH_SOURCE
LOOKUP_DEFINITION
BRAINSTORM_ALTERNATIVES
HUMAN_REVIEW
```

Detailed verification runs only after `PROCEED_TO_DETAILED`. If detailed
verification passes, the final `review_packet_v<N>.md` may cite the structural
packet:

```markdown
- Structural packet: lemmas/<id>/verifier/structural_packet_v<N>.md
```

Merge decisions still use the final `review_packet_v<N>.md`, not the structural
packet alone.

Implementation implication: `review_packet_lint.py` should gain a `structural`
mode rather than forcing structural reports to masquerade as final merge
packets.

## Hard Invariants

These rules must never be violated:

- The Orchestrator does not prove or verify mathematics.
- Rule-governed autonomy is routing autonomy only. The Orchestrator chooses the
  next specialist owner; it must not perform specialist work itself.
- Only the Orchestrator may write `proof.tex` and `STATUS.md`.
- The Orchestrator writes `proof.tex` only to merge or assemble already
  verified specialist-owned artifacts.
- Verifiers must be fresh.
- Generator, Refiner, Refiner, and Explorer must not spawn
  Verifiers.
- A proof candidate must pass structural and detailed verification.
- A proof candidate, proof repair, proof simplification, target contract,
  decomposition, source-theorem package, definition audit, computation audit,
  route synthesizer, or obstruction candidate must be produced by its specialist
  owner, not by the Orchestrator.
- A Verifier `PASS` is not enough for merge; the review packet must pass
  structural lint.
- A prior `PASS` applies only to the exact artifact checked. Any later change to
  proof text, theorem statement, target contract, complexity ledger,
  source-theorem package, definition reading, or final assembly must be routed
  through the responsible specialist and fresh verification.
- Mechanical checks such as LaTeX compilation, grep audits, local linters, and
  result-contract gates are not mathematical verification.
- If a required specialist owner cannot be spawned or resumed, the Orchestrator
  must leave restartable state instead of doing the specialist work itself.
- Open obligations, stuck routes, missing source theorems, missing definitions,
  and failed searches are not final answers.
- A named theorem can carry a proof only after exact statement, source or
  derivation route, and preconditions are recorded.
- Specialized notation or named families need accepted definition sources.
- A terminal counterexample or obstruction requires proof-review style routing
  and fresh verification.
- If an agent skipped a required check, verification, or output file, it must
  not declare completion.
- Long tasks must write checkpoints or `STATUS.md` updates: completed work,
  verified results, remaining work, and next owner.

## Routing Principles

No fixed pipeline is prescribed. The Orchestrator may try better routes, but it
must obey these principles:

- After a proof candidate is written, run structural verification first, then
  detailed verification.
- After verification failure, classify the failure; do not blindly ask the same
  agent to rephrase the same attempt.
- The Orchestrator may merge only after review-packet lint passes.
- A source theorem blocker routes to Searcher or the search
  workflow.
- A definition or notation blocker routes to Auditor, Collector, or
  a human.
- If the route is unclear, the Orchestrator may spawn multiple Explorers or
  Sketchers.
- A possible counterexample or obstruction routes to CE-Hunter,
  then proof-review and fresh verification.
- If a required artifact is missing, fail loud, write state, and route to the
  responsible owner.
- If rules or agent recommendations conflict, record the conflict explicitly;
  the Orchestrator chooses one or asks a human.
- Proof shortening is not important before correctness is complete. First make
  it complete, then make it pretty.

## Parallel Exploration

The Orchestrator may explore in parallel:

- forward proof routes;
- counterexample or obstruction search;
- source theorem search;
- definition or convention audit;
- multiple Explorers;
- multiple Sketchers.

The key constraint is diversity, not budget. Different subagents should receive
different constraints:

- elementary/direct route;
- known theorem route;
- counterexample-risk route;
- bypass-current-DAG route;
- minimal-lemma route;
- maximal-verifiability route;
- construction-first route;
- obstruction-first route.

Parallel outputs do not enter the canonical plan directly. The Orchestrator may
send them to the Regulator or Synthesizer, then ask Sketcher to write a
canonical candidate, then run structural verification.

### Diversity Constraints

Explorer and multi-sketch tasks must not merely say "try another idea".
The Orchestrator must provide mutually different constraints.

Standard constraints:

| Constraint | Requirement |
|---|---|
| `direct-elementary` | Avoid heavy theorem packages where possible; look for direct constructions, elementary estimates, or explicit calculations. |
| `known-theorem` | Search for a load-bearing known theorem, while listing source and precondition risks. |
| `counterexample-risk` | Attack the statement first; look for boundary cases, counterexample shapes, or obstructions. |
| `bypass-current-dag` | Do not follow the current DAG; try to bypass it completely. |
| `minimal-lemma` | Minimize the number of lemmas and compress the route. |
| `max-verifiability` | Prefer fine-grained obligations that are easy for Verifier to check. |
| `construction-first` | Start from the key object, map, invariant, or witness. |
| `obstruction-first` | Start from global invariants, conservation laws, boundary conditions, or no-go theorems. |

The Orchestrator may combine constraints, but should not launch two
Explorers with nearly identical constraints in the same round.

### Candidate Synthesizer

The Orchestrator does not judge mathematical feasibility by itself. It performs
structural filtering; mathematical plausibility is handled by the Regulator,
Synthesizer, and Verifier.

Recommended scoring dimensions:

- exact target preservation;
- dependency clarity;
- source theorem risk;
- definition or notation risk;
- verifier checkability;
- overlap with route history;
- counterexample risk;
- final assembly clarity.

The Synthesizer returns a ranked synthesizer, but does not write the
canonical decomposition. After the Orchestrator chooses a candidate direction,
Sketcher writes the formal decomposition and Structural Verifier checks it.

## Failure Classes

The Regulator outputs one primary class plus optional tags.

### Primary Classes

| Class | Meaning | Suggested owner |
|---|---|---|
| `proof-local` | The statement and plan are acceptable; the problem is mainly proof execution. | Generator |
| `plan-dag` | The lemma statement, dependency, final bridge, or assembly route is wrong or incomplete. | Sketcher / Refiner |
| `context-source` | A source theorem, definition, notation, or convention audit is missing. | Searcher / Auditor / Collector |
| `route-strategy` | The overall route is unsuitable; the system needs a different strategy or multiple routes. | Explorer / Sketcher / Synthesizer |
| `target-obstruction` | There may be a counterexample, boundary failure, or obstruction. | CE-Hunter / ProofReview / Verifier |
| `human-needed` | The accepted reading or mathematical target needs human clarification. | Human |

### Optional Tags

```text
source-theorem
definition-notation
final-assembly
finite-case
computation
dependency-precondition
statement-drift
counterexample-risk
repeated-blocker
```

## Subagent Toolbox

Codex usually does not allow subagents to spawn subagents. All parallel and
compound scheduling is performed by the Orchestrator.

Every role must have clear inputs, outputs, and forbidden actions.

### Existing Agents

**Sketcher**

- Inputs: `problem.md`, target contract, research notes, route history, and
  required recovery packets.
- Outputs: `sketch/decomposition.md`, lemma statements, risk checklist.
- Forbidden: writing proofs, `proof.tex`, or verifier outputs.
- Role: write the canonical lemma DAG or repair the plan/DAG.

**Generator**

- Inputs: `problem.md`, one lemma statement, dependency proofs, and Verifier
  feedback.
- Outputs: `generator/proof_v<N>.md`, `generator/status.md`.
- Forbidden: spawning Verifiers, writing verifier directories, writing
  `proof.tex`.
- Role: prove one forward lemma or theorem. It may report obstruction signals,
  but it does not systematically search for counterexamples.

**Verifier**

- Inputs: problem, statement, proof or decomposition, dependencies, risk
  checklist.
- Outputs: report, review packet, verdict.
- Forbidden: modifying proof, modifying plan, merging.
- Role: fresh mathematical checking, in structural mode or detailed mode.

**Refiner**

- Inputs: verified or failed decomposition, plan-level feedback, route history.
- Outputs: refined plan candidate.
- Forbidden: writing proofs or `proof.tex`.
- Role: compress, repair, or replace the DAG at plan level.

**Refiner**

- Inputs: completed and gated `proof.tex`, accepted packets, decomposition.
- Outputs: refined proof candidate.
- Forbidden: replacing the correctness workflow.
- Role: shorten and improve exposition after correctness is complete.

**Collector**

- Inputs: query request, Collector/wiki index, context file.
- Outputs: `queries/<query_id>/collector.md`.
- Forbidden: external search, writing proofs, modifying Collector source files.
- Role: read the local knowledge base.

### New Agents

**Regulator**

- Inputs: failed proof, structural/detailed report, review packet, `STATUS.md`,
  recovery packet, route history.
- Outputs: failure class, tags, recommended owner, file target, one-line
  blocker, what not to retry, reusable work, route-history update or
  compression recommendation.
- Forbidden: proving, verifying, merging, spawning subagents.
- Role: classify failures and recommend routing; suggest search-mechanism
  changes after repeated failures.

**Explorer**

- Inputs: problem, target contract, current decomposition, route history,
  diversity constraint.
- Outputs: ranked candidate routes, key lemmas, likely blockers, search needs,
  counterexample risks.
- Forbidden: writing proofs, writing canonical plans, writing `STATUS.md`,
  spawning subagents.
- Role: divergent route design. It is not Sketcher; it only proposes candidate
  routes.

**CE-Hunter**

- Inputs: problem, target contract, current lemma or route, accepted
  definitions, route history.
- Outputs: candidate counterexamples, boundary risks, obstruction arguments,
  conventions requiring audit.
- Forbidden: final answers, writing `proof.tex`, replacing Verifier.
- Role: attack the statement or route. Generator proves forward; CE-Hunter searches for reverse evidence and boundary failures.

**Searcher**

- Inputs: problem, lemma statement, proof obligation, candidate theorem name,
  research/query outputs.
- Outputs: exact usable statement, source or derivation route, preconditions,
  circularity/strength audit, usable location.
- Forbidden: proving the target theorem, merging.
- Role: turn named theorem use into an auditable theorem package.

**Auditor**

- Inputs: problem, target contract, unresolved notation/name, Collector or
  research context.
- Outputs: accepted definition, source, ambiguity status, human clarification
  need.
- Forbidden: guessing definitions to prove or refute.
- Role: resolve notation, named families, and boundary conventions.

**Code Executor**

- Inputs: proof step, computation output, finite case claim, script/table path.
- Outputs: finite universe, exhaustiveness, symmetry reductions, boundary
  cases, evidence files, conclusion mapping.
- Forbidden: using black-box computation as a substitute for proof.
- Role: audit finite checks and computation evidence.

**Synthesizer**

- Inputs: multiple Explorer/Sketcher route candidates, route history, risk
  notes.
- Outputs: ranked synthesizer, recommended route, rejected-route reasons.
- Forbidden: proving, verifying, writing canonical decomposition.
- Role: compress multiple candidate routes into a direction that can be sent to
  Sketcher or Verifier.

Synthesizer is an independent custom agent. Its output cannot directly
become the canonical plan. The Orchestrator must send the synthesizer to Sketcher
to write the formal decomposition, and then to Structural Verifier.

**Route Historian**

Route Historian is not a first-round independent custom agent. Its
responsibility is initially folded into Regulator to avoid role bloat.

The Regulator writes route-history entries when needed. When history gets too
long, the Regulator also recommends compression. If route-history maintenance
later becomes complex, it can be split into an independent agent.

## Route History and Recovery

Recovery and route rewrite are not the same:

- **Recovery** is an artifact/protocol: it records the current blocker, owner,
  next file target, and resumable state.
- **Route rewrite** is an action: it abandons or replaces the current proof
  route.
- **Route history** is long-term memory: it records which routes failed, why
  they failed, and what must not be retried.

Files:

```text
recovery/route_history.md
recovery/route_recovery_<N>.md
```

Suggested route-history entry:

```markdown
## Route <N>: <short name>

- Status: abandoned | revised | blocked | superseded
- Trigger packet: <path>
- Failed target: <lemma, theorem, or final assembly step>
- Failure class: <class>
- Verifier blocker: <short exact blocker>
- What not to retry:
  - <specific failed step, theorem route, definition reading, or estimate>
- Reusable partial work:
  - <usable lemma, reduction, computation, or source>
- Suggested next owner: <agent or human>
- Suggested next file target: <path>
```

### Route History Compression

Route history stores only information useful for later routing, not the full
proof process.

Compression rules:

- `STATUS.md` stores only the active route path and one-line summary.
- Each `route_history.md` entry stays short.
- When more than three failures share a class, Regulator writes a grouped
  summary and marks older entries as summarized.
- Compression must not delete `what not to retry` or `reusable partial work`.
- If a failed route is fully superseded by a verified route, it may be marked
  `superseded`, but the blocker summary remains.

## Result Contract

The system has only two mathematical terminal states:

1. a verified proof of the original statement;
2. a verified counterexample or obstruction to the original statement.

The following are not terminal mathematical answers:

- source theorem unavailable;
- route missing;
- definition missing;
- notation unclear;
- no proof found;
- agent stuck;
- attempt budget exhausted;
- problem statement did not provide an intermediate object.

These states must enter recovery and continue routing to search, definition
lookup, route rewrite, human clarification, or obstruction verification.

## Consequences

### Benefits

- More flexible than a fixed pipeline.
- Failures are classified rather than blindly advanced.
- Regulator reduces the Orchestrator's cognitive load.
- Brainstorming and multi-route exploration become first-class actions.
- Two-layer verification catches structural errors early.
- Route history reduces repeated failure routes.
- Review-packet and completion-gate discipline is preserved.

### Risks

- Rules may conflict.
- Route history may grow too long.
- Regulator output may create noise if unstructured.
- Explorers may produce duplicate routes without diversity constraints.
- Two-layer verification creates more artifacts.
- More agents increase the risk of role overlap.

### Mitigations

- Hard invariants override recommendations.
- Regulator output must be short and structured.
- Route history must stay concise.
- `STATUS.md` stores only the active route summary and path.
- Explorer writes ranked candidates, not canonical plans.
- Synthesizer synthesizes candidates but does not prove or verify.
- Every subagent has explicit write ownership.
- Review-packet lint and completion gates remain hard gates.
- Long tasks must produce checkpoints.

## Experimental Rollout

1. Update Orchestrator rules from pipeline language to rule language.
2. Update the Verifier prompt to support structural and detailed modes.
3. Add a structural mode to `review_packet_lint.py`.
4. Add Regulator custom agent and prompt.
5. Add Explorer custom agent and prompt, including diversity constraints.
6. Add route-history format.
7. Fold Route Historian responsibility into Regulator for now.
8. Add candidate-synthesizer rules.
9. Add Synthesizer custom agent; its output must go through Sketcher and
   Structural Verifier before becoming canonical.
10. Add CE-Hunter, Searcher, Auditor, and
    Code Executor custom agents.
11. Preserve Collector, Refiner, and Refiner, and update their role
    boundaries.
12. Add checkpoint and fail-loud rules.

Out of scope for now:

- UI;
- per-agent model selection;
- token dashboard;
- Python-driven end-to-end pipeline rewrite.
