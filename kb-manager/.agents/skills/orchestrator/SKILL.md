---
name: orchestrator
description: "Route KBManager workflows through specialist subagents while keeping the main Codex context small. Use when a user asks to register sources, ingest files, query the wiki, maintain/reorganize the wiki, archive Lean files, or coordinate multi-step KBManager operations."
---

# KBManager Orchestrator

Use this skill to route KBManager work. The Orchestrator owns dispatch,
review, user communication, and checkpoints. Specialist agents own heavy reads
and writes.

## Routing

| User intent | Agent | Agent skill(s) |
|-------------|-------|----------------|
| Fetch URL, queue inaccessible resource, register local/inbox file | `registrar` | `source-management` |
| Process a registered raw source | `ingester` | `ingest`, then `ingest-source`, `ingest-analysis`, or `lean-archive` as needed |
| Answer from the compiled wiki | `researcher` | `query` |
| Lint, repair, or semantically reorganize wiki pages | `maintainer` | `wiki-maintenance` |
| Organize registered Lean 4 files and create Lean wiki cards | `archivist` | `lean-archive` |

Specialists follow a hub-and-spoke model: they never command one another. When
another role is needed, the current specialist returns a handoff request naming
the requested owner, relevant paths, blocker, and acceptance condition.

## Task Packet

Every dispatch must provide a bounded packet:

```markdown
Task:
User request:
DATA_DIR:
Input paths:
Required skill(s):
Allowed reads:
Allowed writes:
Forbidden writes:
Required confirmations:
Acceptance criteria:
Return:
```

Use `${DATA_DIR:-data}` unless the environment or human supplies another data
root.

## Orchestrator Duties

- Classify the user request and select the smallest responsible agent.
- Prepare a task packet with inputs, `DATA_DIR`, allowed reads, allowed writes,
  forbidden writes, confirmation points, and acceptance criteria.
- Spawn or resume the selected specialist.
- Review the specialist's returned paths and relevant diffs before reporting.
- Create scoped git checkpoints after ingest, Lean archive, lint repair, or
  reorganization operations that change the wiki, unless the human asks not to.

## Confirmation Gates

- `registrar` asks before duplicate registration.
- `ingester` summarizes 3-5 core takeaways before writing.
- `archivist` stops before each phase transition.
- `maintainer` reports lint findings and proposed fixes before lint-style
  repairs.

At a gate, the specialist returns the question to the Orchestrator. The
Orchestrator asks the human and never infers approval.

## Review and Failure Handling

After a specialist returns:

1. Inspect `git status` and the relevant diffs.
2. Confirm that every changed path is within the allowed write set.
3. Check the packet's acceptance criteria.
4. Create any required scoped checkpoint.
5. Report the result, changed paths, remaining blockers, and next handoff.

If work is blocked, record the smallest blocker and route the next responsible
owner. Ask the human only for genuine missing input, a confirmation gate,
external permission, or ambiguous mathematical interpretation.

## Boundaries

Do not deep-read long sources, perform source/analysis ingest, run deep wiki
queries, or reorganize large wiki areas inside the Orchestrator when a
specialist can own the work. Do small mechanical checks locally when they are
needed to verify the returned result.

Use direct local work only for tiny tasks, status inspection, or when subagent
spawning is unavailable.
