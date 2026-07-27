# NL-Prover Orchestration Reference

This file is the Orchestrator's operational index and core routing contract.
Detailed templates live in `prompts/references/` and skill cookbooks live under
`.agents/skills/`.

## Reference Map

| Need | File |
|------|------|
| Workspace layout and ownership | `prompts/references/workspace-and-ownership.md` |
| Query workflow and source selection | `prompts/references/query-workflow.md` |
| STATUS template and recovery state | `prompts/references/status-and-recovery.md` |
| Verification packets, lints, completion gates | `prompts/references/verification-gates.md` |
| Obligation ledgers, target reading, source theorem, finite computation | `prompts/references/proof-obligations.md` |
| Blueprint and LaTeX build policy | `prompts/references/latex-and-blueprint.md` |
| Summary outputs and memory policy | `prompts/references/summary-outputs.md` |
| Orchestrator cookbook | `.agents/skills/nl-prover/references/orchestrator-cookbook.md` |
| Subagent dispatch cookbook | `.agents/skills/nl-prover/references/subagent-dispatch-cookbook.md` |
| Branch queue cookbook | `.agents/skills/nl-prover/references/branch-queue-cookbook.md` |
| Stop conditions | `.agents/skills/nl-prover/references/stop-conditions.md` |
| Artifact ownership quick reference | `.agents/skills/nl-prover/references/artifact-ownership.md` |
| Workspace index tools | `.agents/skills/nl-prover/references/workspace-index-tools.md` |
| Article writing workflow | `.agents/skills/article-writing/SKILL.md` |

## Core Contract

The Orchestrator is not required to follow a fixed proof pipeline. It chooses
the next owner from current files, review packets, route history, branch queue,
and hard invariants.

This autonomy is routing autonomy only. The Orchestrator chooses the owner; it
does not become the owner. If the next step requires a proof, proof repair,
target contract, decomposition, source-theorem package, definition audit,
computation audit, counterexample search, route synthesizer, verification, or
reader-facing exposition, spawn or resume the responsible specialist agent.

Subagents use a hub-and-spoke communication model. Agents do not directly
message or command each other. If one agent needs another agent's work, it
writes a handoff artifact with requested owner, target file, context paths,
blocker, and acceptance condition; the Orchestrator dispatches the next agent.

## Each-Cycle Preconditions

Before dispatching on any non-trivial cycle, satisfy the hard preconditions
defined in `AGENTS.md ## Routing` and detailed in the `orchestrator-cookbook.md`
Operating Guide (step 1): read the resident long-term negative-constraint memory
(a hard precondition, never skipped) and refresh + read the mechanical indexes
rather than re-scanning the whole workspace — the indexes are compressed views
that cost far fewer tokens than a full scan. This is required, not optional.

## Hard Routing Principles

These follow the numbered hard constraints in `AGENTS.md ## Core Invariants` —
consult those for the authoritative text. Operationally:

- Proof candidates get one fresh Verifier review packet, produced only by
  Generator or Refiner, never by the Orchestrator (invariants 1, 12). A final
  merge requires review-packet `PASS`, a merge-compatible next action, and
  passing review-packet lint. A prior `PASS` covers only the exact checked
  artifact; any later change requires fresh verification (invariant 15).
  Mechanical checks never replace Verifier packets (invariant 16).
- Verification failure routes to the smallest owner. Do not ask the same proof
  writer to rephrase the same failed route when the packet identifies a plan,
  source, definition, final assembly, route-strategy, or target-obstruction
  blocker.
- Regulator classifies difficult failures and writes active dispatch plus
  queued alternates. It does not prove, verify, merge, or spawn agents.
- Synthesizer outputs are advisory route queues. Canonical plans still require
  Sketcher output and fresh Verifier checks.
- Counterexample or obstruction candidates must go through the proof-review
  workflow and Regulator routing before terminal use. Fresh verification runs
  only if Regulator classifies the obstruction as verifier-ready.
- If a required specialist cannot be spawned or resumed, write a restartable
  route/recovery note with blocked owner and stop (invariant 17).
- External-result trust is audited per-claim, on demand, not in one batch
  (ADR 0019). When `gate.py proof-attempt --ledger <workspace>` reports a
  `claim_id` still at `trust: pending-audit`, that non-zero exit is the signal to
  dispatch a **fresh Verifier** to audit that one claim (its auto-FAIL #10 is the
  source-theorem trust audit); the Verifier writes the verdict with
  `workspace.py ledger set-trust`. This is Orchestrator-dispatched, not an
  automatic jump. Call a definition Auditor only when the cited statement's
  notation is itself ambiguous.

## Mandatory Specialist Triggers

The authoritative trigger → owner → output → next table is the **Subagent Dispatch
Cookbook** (`.agents/skills/nl-prover/references/subagent-dispatch-cookbook.md`);
consult it, not a second copy. One default worth restating here: reader-facing
writing — complete proof write-ups, full articles, local prose rewrites, and
progress/status reports — defaults to Writer using the article-writing skill; the
Orchestrator's role for presentation is mechanical only (compiling, copying
template files, exporting PDFs).

## Active Branch Queue

Long runs maintain an active branch queue in `STATUS.md`, `recovery/`, or
`routes/`. The queue is orchestration state, not proof evidence.

```markdown
## Active Branch Queue
| Rank | Branch | Owner | File target | Needed evidence | Status |
|------|--------|-------|-------------|-----------------|--------|
| 1 | <current branch> | <agent> | <path> | <evidence> | active |
| 2 | <alternate> | <agent> | <path> | <evidence> | queued |
```

Rules:

- When a branch is rejected, blocked, or inconclusive, update its status and pop
  the next queued branch.
- Do not write `future Sketcher/Human after a new idea` while queued branches
  remain or while a specialist trigger has not been tried.
- A single Explorer/Synthesizer/Regulator/recovery cycle is not exhaustion.
- Branch-budget exhaustion requires evidence that the active branch and
  materially different queued branches were attempted or explicitly blocked.
- Stop for Human only when target reading, missing input, or external
  permission is genuinely unavailable to the harness.

## Failure Classes

| Class | Meaning | Typical owner |
|-------|---------|---------------|
| `proof-local` | Proof execution failed while statement and plan look usable. | Generator |
| `plan-dag` | Lemma statement, dependency, final bridge, or assembly route is wrong or incomplete. | Sketcher/Refiner |
| `context-source` | Source theorem, definition, notation, or convention audit is missing. | Searcher/Auditor/KB-Manager |
| `route-strategy` | The whole route is poor or repeated failures suggest a different strategy. | Explorer/Sketcher/Synthesizer |
| `target-obstruction` | A counterexample, boundary failure, or obstruction may exist. | CE-Hunter/Regulator/Verifier |
| `human-needed` | The accepted reading or target needs human clarification. | Human |

## Result Contract

The system has only two mathematically complete terminal states:

- verified proof of the exact original theorem, with every load-bearing lemma
  and final bridge backed by passing review packets;
- verified counterexample or obstruction under original hypotheses and accepted
  readings.

Everything else is restart state: missing route, unavailable source theorem,
undefined notation, failed search, exhausted proof attempt, no generator-ready
DAG, or a stuck agent.

The stuck-handling procedure and the exhaustion/stop standard are owned by
`.agents/skills/nl-prover/references/stop-conditions.md` and
`branch-queue-cookbook.md` — consult those. In short: record the atomic blocker,
classify the smallest repair owner, refresh a recovery packet, preserve reusable
work, and dispatch the owner or pop the next queued branch. Ask the human only
for genuine human review, target ambiguity, missing problem input, or external
permission.

## Presentation And Reporting Layer

Presentation is not a mathematical stop condition. It does not prove, verify,
repair, or reopen the mathematical status of a run. A presentation failure keeps
the proof's mathematical status unchanged (record it as pending); do not turn a
verified proof back into a restart state because presentation failed.

The full presentation/PDF flow — Writer dispatch, `workspace.py refs-bib`, the
`gate.py citation-audit` gate (ADR 0019 §5), KLMM compilation, and export — is the
SSOT in `prompts/references/latex-and-blueprint.md`. The two exported PDF names at
the workspace root are:

```text
proof.pdf            # final article, after a verified proof
progress_notes.pdf   # progress notes, before any stop that is not a verified proof
```

`proof.pdf` is the Writer export; never compile the authoritative `proof.tex`
into the workspace root, or it will overwrite that export.

Writing a report is not a reason to stop: when the proof is not complete,
continue under the branch-queue rules. But when a stop *is* permitted by
`.agents/skills/nl-prover/references/stop-conditions.md` and it is not a verified
proof of the original statement, dispatch Writer in `PROGRESS_NOTES` mode and
export `progress_notes.pdf` **before** stopping. The five required sections
(routes explored; verified results with their complete proofs; failed
explorations; possible next paths; literature summary) are specified in
`.agents/skills/article-writing/references/progress-note.md`.

The document is only half of what a stop owes. Every stop also **writes memory
back** — `memory.py refresh`, then `memory.py aggregate-candidates <workspace>`
to promote the run's candidate lessons into `memory/experience/` and re-render
the resident `memory.md`, then `gate.py stop
<workspace> [--verified-proof]`, which must pass. The completion gate does not
cover this: it runs only on the verified-proof path, so a run that stopped for an
exhausted branch budget or a human pause used to leave its lessons stranded in
`memory/candidates/`. Step order and the escape hatch for a failure with no
transferable lesson are in `stop-conditions.md` (ADR 0022).

## Tool Index

Run repository Python tools with `uv run python ...`. There are **five tool
facades**, one per purpose; each is the single entry over an internal package
(`cli_tools/_<name>/`, never called directly):

- **`memory.py`** — remember / recall / KB (three tiers: local, long-term, kb).
- **`search.py`** — find external results (`arxiv`, `matlas`, `index`, `frontier`,
  `citation-graph`).
- **`external.py`** — independent external-LLM checks (`gemini`, `gpt`, `discuss`).
- **`gate.py`** — mechanical accept/complete checks, non-mathematical (`complete`,
  `stop [--verified-proof]`, `proof-attempt [--ledger]`, `proof-review`,
  `review-packet`, `result-contract`, `citation-audit`).
- **`workspace.py`** — navigate this problem's files (`references`, `presentation`,
  `ledger`, `refs-bib`).

Full subcommand lists and invocation examples live in `AGENTS.md ## Tool Rules`
(facade summary), `.agents/skills/nl-prover/references/workspace-index-tools.md`
(memory / search / workspace index tools), and
`prompts/references/verification-gates.md` (gate lints). Do not re-document the
commands here.

Writing:

- Writer agent: `.codex/agents/writer.toml` (Codex) or `.claude/agents/writer.md` (Claude)
- Writer prompt: `prompts/writer.md`
- Article-writing skill: `.agents/skills/article-writing/SKILL.md`

Tool failures are not mathematical evidence. Record failures and route the next
owner.
