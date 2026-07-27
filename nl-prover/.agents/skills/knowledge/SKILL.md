---
name: knowledge
description: "KB-Manager knowledge base tools: list, query, and write proven results"
---

# Knowledge Base Tools

Tools for interacting with the KB-Manager knowledge base — a local store of proven mathematical results and research notes. All scripts are in `cli_tools/`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **kb-manager-summary** | List concept and analysis pages in the knowledge base (local read, zero cost) | **Always run first** before issuing a deep query |
| **kb-manager subagent** | Deep query the knowledge base by reading local KB-Manager wiki files | When you need detailed information about a specific concept, analysis, source, or Lean page |
| **kb-manager-write** | Save a file or text note to the knowledge base inbox | After a lemma is verified, to persist the result |

In orchestrated proof work, route KB-Manager deep reads through the problem-local
`queries/<query_id>/` workflow from `prompts/orchestration.md`; the KB-Manager
subagent writes `queries/<query_id>/kb-manager.md`.

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
