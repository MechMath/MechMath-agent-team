---
name: llm
description: "Use for external-LLM support around a Lean proof: an informal proof sketch before formalizing, free-form proof-strategy discussion when a route is stuck, a second-model review, or a code-golf suggestion after the deterministic gates pass."
---

# External-LLM Tools

Every tool here is an external API call behind the single facade
`cli_tools/external.py`. The internal modules (`cli_tools/_external/*.py`) are
never called directly, and OpenRouter is used automatically when
`OPENROUTER_API_KEY` is set — there is no separate "…-openrouter" tool.

**Nothing these tools return is evidence.** An LLM's opinion that a proof is
correct means nothing in FL-Prover; only `lean.py check` / `scan` / `axioms`
decide. Treat every output as a draft to be compiled.

## Available Tools

| Command | Purpose | When to use |
|---------|---------|-------------|
| `external.py informal <problem\|->` | Draft an informal solution in a generate-and-verify loop | Before formalizing, when no informal proof was supplied |
| `external.py discuss <question\|->` | Free-form discussion of proof strategy or Lean code | When a route is stuck and you want a high-level alternative |
| `external.py gemini <file>` / `external.py gpt <file>` | Independent second-model read of a written argument | For a cross-check of an informal argument, never of Lean validity |
| `external.py golf <lean_code\|->` | Propose a shorter, cleaner version of a working Lean proof | Golfer only, after the proof already compiles |

Common options: `--backend gemini\|gpt`, `--model M`, `--temperature T`; pass `-`
to read the input from stdin.

For full parameters and examples, read the matching `reference-<tool>.md` in this
directory.
