---
name: knowledge
description: "KB-Manager knowledge base tools: list what the KB already holds, and write reusable Lean knowledge (proved helper lemmas, Mathlib gaps, definition mismatches, failed proof routes) back to it."
---

# Knowledge Base Tools

Tools for reading and writing the KB-Manager knowledge base — the third memory
tier, a local store of reusable results shared across the agent team. It holds
reusable knowledge, **not** a task log: current run state belongs in the task
ledger (`cli_tools/control.py task`) and the wave summaries.

Every access goes through the single memory entry `cli_tools/memory.py`; the KB
logic itself (`cli_tools/_memory/kb.py`, `inbox.py`) is internal and never called
directly.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `memory.py read --tier kb --view compact` | List the concept / analysis / experience pages the KB holds (local read, zero cost) | **Always first**, before any deep KB query |
| `memory.py read --tier kb --query TEXT` | Filter that index by topic | When looking for a specific concept or source |
| `memory.py inbox-write` | Save a file or note into the KB inbox for indexing | After a helper lemma compiles and is axiom-clean |

## What FL-Prover Writes to the KB

Keep FL-Prover's KB footprint Lean-shaped and small. In practice that is two card
types:

- `Lean_*` — a reusable formal fact: a proved helper lemma with its exact
  statement, the Mathlib lemmas it needed, or a Mathlib gap you had to work
  around.
- `Experience_*` — a negative constraint: a formalization trap that cost a wave
  (a definition that does not mean what its name suggests, a tactic that loops on
  a shape, a statement pattern that silently weakens the theorem).

The richer card taxonomy (`Concept_`, `Source_`, `Analysis_`, `Conjecture_`)
belongs to the informal side of the loop; FL-Prover may read those cards but
rarely produces them.

Use the `memory-routing` skill first if you are unsure whether something belongs
in the KB tier at all rather than in the local index or the long-term
negative-constraint list.

For full parameters and examples, read the matching `reference-<tool>.md` in this
directory.
