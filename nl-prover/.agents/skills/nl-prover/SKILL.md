---
name: nl-prover
description: "NL-Prover orchestration cookbook for multi-agent informal proof runs. Use when the Orchestrator manages a proof workspace, chooses specialist subagents, diagnoses stalled routes, maintains branch queues, enforces Orchestrator delegation, or avoids fixed proof pipelines. Trigger on no generator-ready DAG, verifier failure, source theorem blocker, definition ambiguity, route-strategy failure, counterexample risk, branch pruning, recovery packet, route history, repeated blocker, early-stop risk, proof workspace handoff, article/progress writing handoff, or artifact ownership conflict."
---

# NL-Prover Orchestration Cookbook

Use this skill to manage proof workspaces without doing specialist work inside
the Orchestrator. It is not a fixed proof pipeline. It tells the Orchestrator
which cookbook to load, how to choose specialist subagents, and when a stalled
route remains restartable.

## Quick Dispatch

| Need | First reference |
|------|-----------------|
| General orchestration loop | [orchestrator-cookbook.md](references/orchestrator-cookbook.md) |
| Choose the next specialist | [subagent-dispatch-cookbook.md](references/subagent-dispatch-cookbook.md) |
| Route is stuck, pruned, or inconclusive | [branch-queue-cookbook.md](references/branch-queue-cookbook.md) |
| Refresh and read the mechanical indexes (required every non-trivial cycle) | [workspace-index-tools.md](references/workspace-index-tools.md) |
| Decide whether stopping is allowed | [stop-conditions.md](references/stop-conditions.md) |
| Artifact ownership is unclear | [artifact-ownership.md](references/artifact-ownership.md) |

## Specialist Summary

Explorer proposes diverse routes; Synthesizer ranks route portfolios;
Regulator classifies failure and dispatch queues; Searcher traces
literature and audits theorem packages; Auditor resolves notation; CE-Hunter
searches for obstruction candidates; Code Executor audits finite or
computed evidence; Sketcher canonicalizes plans; Generator writes proofs;
Verifier checks; Refiner shortens accepted proofs; Writer produces
reader-facing article candidates, local rewrites, and progress notes; KB-Manager
reads local knowledge.

## Skills

| Skill | Description |
|-------|-------------|
| [search](../search/SKILL.md) | Literature search: arxiv-search, matlas-search |
| [knowledge](../knowledge/SKILL.md) | Knowledge base: kb-manager-summary, kb-manager subagent, kb-manager-write |
| [verification](../verification/SKILL.md) | Single-packet verification guidance plus gemini-verify and gpt-verify |
| [llm](../llm/SKILL.md) | LLM tools: discussion-partner |
| [target-reading](../target-reading/SKILL.md) | Target contract, accepted readings, and definition/notation routing |
| [source-theorem](../source-theorem/SKILL.md) | Source theorem packages, precondition audits, and bridge obligations |
| [proof-review](../proof-review/SKILL.md) | Two-sided proof/refutation routing before terminal non-proof results |
| [proof-recovery](../proof-recovery/SKILL.md) | Restartable branch recovery and Regulator-aware owner selection |
| [human-review](../human-review/SKILL.md) | Human-marked proof repair with fresh verification |
| [proof-summarize](../proof-summarize/SKILL.md) | Final proof summary and reusable knowledge notes |
| [article-writing](../article-writing/SKILL.md) | Writer cookbook for article candidates, local rewrites, and progress notes |

## Environment variables
- `OPENROUTER_API_KEY` — preferred for gemini-verify, gpt-verify, discussion-partner
- `GEMINI_API_KEY` — fallback for gemini-verify and discussion-partner (gemini backend)
- `OPENAI_API_KEY` — fallback for gpt-verify and discussion-partner (gpt backend)
