# ADR 0001: Multi-Agent Orchestration Architecture

## Status
Accepted

## Context

Producing rigorous informal mathematical proofs requires multiple cognitive modes: research and decomposition (understanding the problem landscape), creative proof generation (finding proof strategies), and skeptical verification (checking each logical step). These modes conflict when housed in a single agent — a generator that also verifies tends to confirm its own reasoning (anchoring bias), and a researcher that also proves tends to lose the big picture in implementation details.

Prior systems (Archon, Prover) demonstrate that multi-agent decomposition with specialized roles significantly improves quality. Archon uses Plan/Prover/Review cycles; Prover uses Coordinator/Sketcher/ProofAgent/BlueprintAgent. Both share a key insight: **orchestration and execution must be separated**.

Additionally, informal proof verification is fundamentally different from formal verification — there is no type checker. The only defense against logical errors is independent, skeptical review by an agent that did not write the proof.

## Decision

We adopt a **hub-and-spoke multi-agent architecture** with four specialized agent roles:

### 1. Orchestrator (Hub)
- **Single persistent agent** that manages the entire proof lifecycle
- Does NOT prove anything itself — purely manages state and spawns agents
- **Sole writer** of the authoritative `proof.tex` and `STATUS.md`
- Makes all strategic decisions (what to prove next, when to re-sketch, when to merge)

### 2. Sketcher (Research & Decomposition)
- **One per problem**, with suspend/resume capability
- Researches the problem space (arxiv, web, knowledge base)
- Decomposes the problem into a lemma DAG with dependency ordering
- Can be re-activated with feedback when a Generator gets stuck
- Writes to `sketch/` and `lemmas/*/statement.md`

### 3. Generator (Proof Creation)
- **One per lemma**, created when the lemma becomes eligible (dependencies satisfied)
- Produces step-by-step informal proofs with explicit justification
- Iterates on verifier feedback (up to max_attempts)
- Can report "stuck" to trigger re-decomposition
- Writes to `lemmas/<id>/generator/`

### 4. Verifier (Proof Checking)
- **Ephemeral** — a fresh instance is spawned for each verification run
- Maximally skeptical: assumes proof is wrong until convinced otherwise
- Produces line-by-line analysis with VALID/QUESTIONABLE/INVALID verdicts
- **Destroyed after each run** to prevent anchoring bias from prior rounds
- Writes to `lemmas/<id>/verifier/`

### Communication Model: File-Based Message Passing

Agents communicate exclusively through the filesystem:
- Each agent reads from shared directories and writes only to its own
- The Orchestrator routes information by including relevant file paths in spawn prompts
- No direct inter-agent messaging — all state is observable in the file tree

### Lifecycle Diagram

```
Problem arrives
  │
  ▼
Orchestrator creates workspace
  │
  ▼
Sketcher spawned ──────────────────────────┐
  │                                         │
  ▼                                         │ (re-activated on stuck/fail)
Decomposition ready                         │
  │                                         │
  ▼                                         │
For each lemma (dependency order):          │
  │                                         │
  ├─► Generator spawned                     │
  │     │                                   │
  │     ▼                                   │
  │   Proof written                         │
  │     │                                   │
  │     ▼                                   │
  │   Verifier spawned (fresh)              │
  │     │                                   │
  │     ├─► PASS ──► Merge to proof.tex     │
  │     │                                   │
  │     └─► FAIL ──► Generator revises      │
  │           │       (up to max_attempts)  │
  │           │                             │
  │           └─► Exhausted ──► Sketcher ───┘
  │
  ▼
All lemmas verified → Final assembly
```

## Consequences

### Pros
- **No self-verification bias** — Generator never checks its own work; Verifier is always fresh
- **Clean state management** — file-based communication makes all state observable and debuggable
- **Flexible re-decomposition** — when a lemma is intractable, the Sketcher can restructure without losing work on other lemmas
- **Parallelizable** — independent lemmas can have Generators running concurrently
- **Auditable** — the full proof history (all attempts, all verifier reports) is preserved in the filesystem

### Cons
- **Higher token cost** — each Verifier spawn re-reads the problem and proof context from scratch
- **Orchestrator complexity** — the hub must track multiple agent lifecycles and make nuanced strategic decisions
- **File I/O overhead** — all communication goes through disk writes and reads
- **No streaming feedback** — Generator cannot get real-time hints from Verifier during proof construction

### Trade-offs vs. Alternatives

| Alternative | Why we didn't choose it |
|-------------|------------------------|
| Single-agent loop (generate → self-check) | Self-verification is unreliable for informal proofs — no type checker to catch errors |
| Two-agent (generate + verify, same instances) | Verifier develops anchoring bias across rounds, lowering verification quality |
| Fully decentralized (no orchestrator) | Without central coordination, dependency ordering and re-decomposition become chaotic |
| Formal proof system (Lean/Coq) | Out of scope — this system targets competition math and research where formalization is too slow |
