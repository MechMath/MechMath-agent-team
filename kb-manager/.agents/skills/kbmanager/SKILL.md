---
name: kbmanager
description: "KBManager skill bundle overview for maintaining a persistent mathematical research wiki with orchestrated source management, ingest, query, maintenance, and Lean archive workflows."
---

# KBManager Skills Index

KBManager is a persistent mathematical research knowledge base maintained by
Codex. Use this index when the user asks generally to work with KBManager or
you need to pick the right workflow.

## Architecture

KBManager uses an incrementally maintained, persistent wiki rather than
reconstructing knowledge through retrieval on every query. It has three layers:

1. `${DATA_DIR:-data}/raw_sources/` is the immutable source of truth.
2. `${DATA_DIR:-data}/wiki/` is the compiled, interlinked Markdown knowledge
   base.
3. `AGENTS.md` and the skills in this directory define the behavioral schema
   that maintains those artifacts.

Cross-referencing and synthesis happen primarily during ingest. Queries begin
with `wiki/index.md` and retrieve only the relevant cards. `wiki/log.md` is an
append-only chronological record using
`## [YYYY-MM-DD] action | Title`.

Human edits to wiki pages are authoritative. Researchers may inspect and edit
the wiki directly, including through Obsidian; later operations must read the
current files before changing them. Create scoped Git checkpoints after major
ingest, archive, repair, or reorganization operations unless the human asks
otherwise.

## Skills

| Skill | Use |
|-------|-----|
| [orchestrator](../orchestrator/SKILL.md) | Route KBManager workflows through specialist subagents |
| [source-management](../source-management/SKILL.md) | Fetch public resources, queue inaccessible resources, register local files into hash-addressed raw sources |
| [ingest](../ingest/SKILL.md) | Dispatch registered files to the right ingest mode |
| [ingest-source](../ingest-source/SKILL.md) | Ingest external references into `Source_*` pages and concept cards |
| [ingest-analysis](../ingest-analysis/SKILL.md) | Ingest problem-solving notes into reusable `Analysis_*`, `PartialProof_*`, or `Obstruction_*` proof memory |
| [query](../query/SKILL.md) | Answer from `$DATA_DIR/wiki/` and persist only non-obvious new insights |
| [wiki-maintenance](../wiki-maintenance/SKILL.md) | Check wiki health and backfill missing semantic links |
| [lean-archive](../lean-archive/SKILL.md) | Organize Lean 4 source files and create wiki proof cards |

## Core Files

- Project rules: `AGENTS.md`
- Architecture and routing rules: `.agents/skills/`
- Runtime data: `${DATA_DIR:-data}`
- Wiki map: `${DATA_DIR:-data}/wiki/index.md`
- Operation log: `${DATA_DIR:-data}/wiki/log.md`
- Source registry: `${DATA_DIR:-data}/sources_manifest.md`
- Download queue: `${DATA_DIR:-data}/download_queue.md`

## Default Selection

- User asks for multi-step KBManager work: use `orchestrator`.
- User provides URL or local file: use `source-management`.
- User asks to process a registered file: use `ingest` to choose source-style,
  analysis-style, or Lean archive handling.
- User asks a research question about accumulated knowledge: use `query`.
- User asks to check/fix wiki health or links: use `wiki-maintenance`.
- User provides `.lean` file: use `lean-archive`.
