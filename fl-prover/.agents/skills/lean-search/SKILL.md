---
name: lean-search
description: "Lean premise retrieval (not literature search — that is `search.py`). Use for Lean theorem proving or formalization whenever you need Mathlib facts, local declarations, premise candidates, examples, definitions, or proof-state search. Covers leandex, loogle, leanfinder, leansearch, state-search, and hammer-premise."
---

# Search Tools

Tools for finding relevant Lean theorems, lemmas, definitions, examples, and premise candidates. Use this skill before defining a concept or proving a helper that might already exist in Mathlib or local code.

All six backends sit behind one facade:

```bash
uv run python cli_tools/lean.py search {leandex|loogle|leanfinder|leansearch|state|hammer} "QUERY" [-n N]
```

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **leandex** | Semantic search by natural language or Lean terms | First choice for any search; **max 5 parallel queries** |
| **loogle** | Pattern-based search by type shape | When you know the type signature pattern |
| **leanfinder** | Mathlib semantic search | Alternative semantic search |
| **leansearch** | Natural language + Lean term search | Alternative to leandex |
| **state-search** | Search by proof goal/state | When you have a specific proof state to match |
| **hammer-premise** | Premise retrieval for automation | When looking for premises for automated tactics |

## Orchestration Use

F-Generator, Formalizer, Regulator, and Integrator roles may all use this skill. Search is especially important before:

- adding a local definition or helper lemma;
- classifying a blocker as missing Mathlib support;
- choosing canonical Mathlib structures for a formalized statement;
- feeding candidate premises into automation or a proof plan.

Read only the reference file for the tool you are about to call, for example `reference-leandex.md`, `reference-loogle.md`, or `reference-state-search.md`.
