# ADR 0002: File-Based Inter-Agent Communication

## Status
Accepted

## Context

Multi-agent systems need a communication protocol. Common options include:

1. **Direct message passing** — agents send messages to each other in real-time
2. **Shared memory / blackboard** — agents read/write a shared data structure
3. **File-based message passing** — agents communicate through filesystem artifacts

The Archon project uses state files (`PROGRESS.md`, `task_results/`, `PROJECT_STATUS.md`) as the communication backbone between Plan, Prover, and Review agents. The Collector project uses structured Markdown files with indexes. Both demonstrate that file-based communication scales well for LLM agents that inherently work with text.

For NL-Prover specifically, we need:
- **Auditability** — every proof attempt and verification report must be preserved
- **Agent isolation** — each agent must work in a bounded context without polluting others
- **Resumability** — if the orchestrator crashes, the file state is the recovery point
- **Debuggability** — humans must be able to inspect exactly what each agent saw and produced

## Decision

All inter-agent communication happens through the filesystem with strict ownership rules.

### Directory Ownership Model

Each agent type has a designated write-zone:

| Agent | Writes to | Reads from |
|-------|-----------|------------|
| Orchestrator | `proof.tex`, `STATUS.md` | Everything |
| Sketcher | `sketch/*`, `lemmas/*/statement.md` | `problem.md`, `STATUS.md`, verifier reports (for re-sketch context) |
| Generator | `lemmas/<id>/generator/*` | `statement.md`, `verifier/report_*.md` |
| Verifier | `lemmas/<id>/verifier/*` | `statement.md`, `generator/proof_v*.md`, `generator/response_to_verifier.md`, referenced analysis-preflight `queries/*/collector.md` |

### File Naming Conventions

**Versioned proof files**: `proof_v<N>.md` where N starts at 1 and increments with each revision.

**Versioned verification reports**: `report_v<N>.md` corresponding to the proof version being verified.

**Timestamped logs**: `<agent_type>_<YYYYMMDD>_<HHMMSS>.md` in the `logs/` directory.

**Revision files** (Sketcher only): `revision_<N>.md` where N increments with each re-decomposition request.

**Research queries**: `queries/<query_id>/` contains `request.md`,
`status.md`, and source outputs such as `arxiv.md`, `matlas.md`, and
`collector.md`. Tool-specific cache files may live below
`queries/<query_id>/arxiv/` or `queries/<query_id>/matlas/`.

### Information Flow Protocol

1. **Orchestrator → Sketcher**: Problem context injected via spawn prompt. Feedback for re-sketching includes paths to relevant verifier reports and generator status files.

2. **Sketcher → Orchestrator**: Sketcher writes `decomposition.md` and `statement.md` files. Orchestrator reads these to plan Generator spawning.

3. **Orchestrator → Generator**: Spawn prompt includes path to `statement.md` and (if revising) path to previous verifier report.

4. **Generator → Verifier**: Generator writes `proof_v<N>.md`. Verifier reads it directly from the filesystem. If `statement.md` or `decomposition.md` contains a Verifier risk checklist, the Verifier also reads the referenced analysis-preflight Collector output and audits each checklist item.

5. **Verifier → Generator**: Verifier writes `report_v<N>.md` and `verdict.md`. Generator reads the report on the next attempt.

6. **Generator ↔ Verifier discussion**: Generator writes `response_to_verifier.md` to address specific concerns. Verifier reads this but is instructed to remain independent. This file is overwritten each round (not versioned) — it reflects the Generator's latest position.

### Status File (`STATUS.md`)

The Orchestrator maintains `STATUS.md` as the single source of truth for proof progress. This file is:
- The first thing the Orchestrator reads when resuming
- The basis for all scheduling decisions
- Updated immediately after any state change

Format:
```markdown
| Lemma | Dependencies | Status | Generator Attempts | Verifier Verdict |
```

Status values: `blocked`, `ready`, `in_progress`, `stuck`, `verified`, `merged`

## Consequences

### Pros
- **Full audit trail** — every proof version, every verifier report, every generator response is preserved as a file
- **Crash recovery** — the filesystem IS the state; no in-memory state to lose
- **Human-inspectable** — anyone can `ls` the workspace and understand what happened
- **Agent isolation** — strict write-zones prevent accidental corruption
- **Natural versioning** — proof_v1, proof_v2, etc. automatically track iteration history

### Cons
- **No real-time feedback** — Generator cannot get streaming hints from Verifier
- **Potential stale reads** — an agent might read a file that another agent is about to overwrite (mitigated by Orchestrator sequencing)
- **Disk I/O** — every communication requires a file write and read (negligible for LLM-speed operations)
- **Convention enforcement** — ownership rules are conventions, not enforced by the OS. Agents must be correctly prompted to respect boundaries.
