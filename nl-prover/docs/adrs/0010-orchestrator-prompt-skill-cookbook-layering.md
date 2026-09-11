# ADR 0010: Orchestrator Prompt, Skill, and Cookbook Layering

## Status

Proposed, experimental.

This ADR refines ADR 0009. The goal is to make rule-governed orchestration
work in long proof runs without turning the Orchestrator into a hidden proof
writer, a verifier substitute, or a fixed pipeline executor.

## Context

ADR 0009 made subagents callable specialists rather than fixed pipeline stages.
Early experimental runs exposed two remaining failure modes.

First, the Orchestrator still tended to rely on Sketcher, Generator, and
Verifier while underusing Explorer, Synthesizer, Regulator, Searcher, Auditor, CE-Hunter, and Code Executor. This
made the newer agents look like advisory extras instead of useful tools.

Second, after one specialist or recovery cycle, a run could stop with a future
Sketcher or Human handoff instead of continuing through a queued alternate
branch. The common bad state is:

```text
future Sketcher/Human after a new idea
```

That is restart state, not exhaustion.

The root issue is layer confusion. The harness currently mixes four different
kinds of instruction:

```text
AGENTS.md             = high-priority harness constitution
.codex/agents/*.toml  = custom-agent registration cards
prompts/*.md          = specialist execution contracts
.agents/skills/*      = triggerable cookbooks and tool workflows
```

When these layers duplicate each other, the model sees stale pipelines and
unclear ownership. When they are too thin, the Orchestrator has no concrete
reason to call the less common specialists.

The current Codex runtime is also hub-and-spoke rather than a native peer
agent-team runtime. Subagents do not directly message, spawn, or command each
other. Cross-agent communication must be represented as files that the
Orchestrator reads and routes.

## Decision

Adopt a four-layer prompt and skill structure.

### AGENTS.md

`AGENTS.md` is the constitution. It should stay high-salience and contain only:

- Orchestrator role and non-role;
- artifact ownership;
- hard invariants;
- mandatory specialist triggers;
- terminal stop conditions;
- pointers to detailed prompts, skills, and orchestration references.

It must not embed a fixed proof pipeline. It may describe a routing loop, but
that loop must choose the next owner from the current blocker and active branch
queue.

### Custom Agent Registrations

`.codex/agents/*.toml` files are registration cards. They identify the agent,
point it to the matching prompt, and state write boundaries. They must not
duplicate full prompt bodies or global orchestration policy.

### Specialist Prompts

`prompts/*.md` files are execution contracts for specialist agents. They define:

- inputs;
- owned output files;
- forbidden actions;
- output schemas;
- completion markers;
- specialist-specific success and failure criteria.

Specialist prompts should not contain global orchestration policy except where
the specialist must produce routing artifacts. Regulator and Synthesizer are the
main exceptions: they must produce executable branch queues rather than a
single vague next owner.

### Skills and Cookbooks

`.agents/skills/*` are triggerable cookbooks and workflow guides. Their
frontmatter descriptions matter because they determine when Codex loads the
skill. The main skill file should be concise and should link to reference files
for detailed workflow variants.

The `nl-prover` skill is the entry cookbook for orchestration. It should
trigger on proof workspace management, specialist dispatch, stalled routes,
branch queue maintenance, verifier failures, source theorem blockers,
definition ambiguity, counterexample risk, route history, and early-stop risk.

Detailed cookbook material belongs in reference files:

- `orchestrator-cookbook.md`;
- `subagent-dispatch-cookbook.md`;
- `branch-queue-cookbook.md`;
- `stop-conditions.md`;
- `artifact-ownership.md`.

## Specialist Dispatch Policy

The Orchestrator should use the smallest specialist that owns the current
blocker:

- unclear route or repeated strategic failure: Explorer portfolio, then
  Synthesizer, then Sketcher canonicalization;
- multiple candidate routes: Synthesizer branch queue;
- missing named theorem or major estimate: Searcher;
- unstable notation, convention, or definition: Auditor or
  target-reading workflow;
- possible falsehood or boundary obstruction: CE-Hunter, then
  Regulator using the proof-review workflow, then fresh Verifier only if
  obstruction-ready;
- finite enumeration or computation evidence: Code Executor, then
  Verifier;
- mixed failure class or unclear owner: Regulator active dispatch plus queued
  alternates;
- stalled route without verified proof or obstruction: proof-recovery branch
  portfolio;
- complete proof after detailed verification: Refiner attempts shortening,
  with the original verified proof retained as fallback until a fresh Verifier
  accepts the refinement.

Calling these subagents is useful even when they share the same base model
because their prompts give them different inputs, allowed writes, forbidden
actions, output schemas, completion markers, and success criteria. The
advantage is not "more people looking at the same thing"; it is isolating
cognitive modes so the Orchestrator does not overfit one route or verify its
own work.

## Branch Queue Policy

Long proof runs maintain an active branch queue in `STATUS.md`, `recovery/`, or
`routes/`. The queue is orchestration state, not proof evidence.

The queue records:

- active branch;
- queued alternate branches;
- owner;
- file target;
- needed evidence;
- status.

When the active branch fails, the Orchestrator updates the evidence and pops the
next queued branch. A single Explorer, Synthesizer, Regulator, or recovery
cycle is not exhaustion.

Branch-budget exhaustion requires evidence that materially different branches
were attempted or explicitly blocked. A run may stop for Human only when the
target reading, missing input, or external permission is genuinely unavailable
to the harness.

## Communication Model

The current harness assumes file-based hub-and-spoke communication:

- subagents write assigned artifacts;
- a subagent that needs another subagent writes a handoff artifact naming the
  requested owner, file target, context paths, blocker, and acceptance
  condition;
- the Orchestrator reads that artifact and dispatches the next owner.

Do not rely on native peer-to-peer agent-team communication unless a future
runtime explicitly supports it.

## Implementation Plan

1. Convert `AGENTS.md` from a fixed workflow into a routing constitution.
   Preserve the existing strict rule that the Orchestrator must not author,
   rewrite, simplify, repair, or extend mathematical proof text.
2. Keep `prompts/orchestration.md` as a compact operational index plus core
   routing contract. Move verbose templates into `prompts/references/`.
3. Update `prompts/regulator.md` so Regulator outputs one active dispatch plus
   queued alternates.
4. Update `prompts/synthesizer.md` so Synthesizer outputs a ranked branch queue,
   not only `Sketcher | Regulator | Human`.
5. Update proof-recovery so a stuck route becomes a restartable branch
   portfolio with an active queue.
6. Redesign `.agents/skills/nl-prover/SKILL.md` as a cookbook entry point
   and add detailed reference cookbooks.
7. Update `.codex/agents/*.toml` descriptions only where they affect tool
   selection.
8. Keep unrelated local files such as `memory.md`, `queries/`, and stray
   untracked files out of the change unless explicitly requested.

## Acceptance Checks

The change is accepted when:

- `AGENTS.md` no longer contains a numbered fixed proof pipeline;
- `prompts/orchestration.md` is short enough to load as an operational index,
  with detailed templates delegated to `prompts/references/`;
- `nl-prover` skill description can trigger on orchestration, dispatch,
  stalled routes, branch queues, and early-stop risk;
- the cookbook references contain executable dispatch and queue procedures, not
  just an index;
- Regulator, Synthesizer, and proof-recovery all produce or preserve queued
  alternates;
- stop conditions reject `future Sketcher/Human after a new idea` while queued
  specialist routes remain;
- all ADR text is English.

## Consequences

Positive:

- less pressure on the Orchestrator to privately diagnose proof strategy;
- clearer reasons to call non-default specialists;
- fewer early stops after one failed route;
- better context hygiene through skill progressive disclosure;
- easier auditing because route decisions become files.

Trade-offs:

- more routing artifacts are written during hard problems;
- the Orchestrator must maintain branch queue state carefully;
- prompts and skills must be kept aligned when a new specialist is added.

Mitigations:

- keep `AGENTS.md` high-salience and short enough to read;
- keep specialist prompts authoritative for their own outputs;
- keep cookbooks concise and load detailed references only when needed;
- require Regulator, Synthesizer, and proof-recovery outputs to include active
  dispatch plus queued alternates.
