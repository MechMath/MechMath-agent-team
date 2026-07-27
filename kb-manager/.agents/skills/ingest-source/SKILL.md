---
name: ingest-source
description: "Use when ingesting external mathematical references such as books, papers, chapters, or lecture notes into KBManager source pages and concept cards."
---

# Source-Style Ingest

Use this mode for external mathematical knowledge whose durable value is
definitions, statements, proofs, examples, hypotheses, and bibliography.

## Inputs

Start from a registered file under `${DATA_DIR:-data}/raw_sources/<hash12>/`.
The dispatcher skill `ingest` handles locating, duplicate checks, and human
acknowledgement before this workflow writes.

## Workflow

1. Read the full source:
   - `.md`, `.txt`, `.tex`: read directly. For `.tex`, preserve commands.
   - `.pdf`: read rendered pages in chunks; do not rely on plain text
     extraction.
2. Create `${DATA_DIR:-data}/wiki/Source_<ShortTitle>.md` with frontmatter,
   summary, key concepts, quotes/evidence, and connections.
3. Read current concept pages before editing. Human edits are ground truth.
4. Update existing `Concept_*` pages touched by the source.
5. Create new `Concept_*` pages only for durable concepts central to the source.
6. Create or update `Obstruction_*` pages when the source exposes a durable
   ruled-out assumption, incompatible convention, counterexample signal, or
   dependency gap that future queries should not rediscover from scratch.
7. Update `${DATA_DIR:-data}/wiki/index.md`:
   - add the new source page under `## Sources`
   - add every new concept under `## Concepts`
   - add every new obstruction under `## Obstruction`
   - keep one-line descriptions concise and navigational
8. Append one `ingest` entry to `${DATA_DIR:-data}/wiki/log.md`.
9. Queue important bibliography references that are foundational, directly used,
   not already ingested, and not already queued.
10. Update `${DATA_DIR:-data}/sources_manifest.md` as ingested with `Wiki page:
   [[Source_<ShortTitle>]]`.
11. Commit changed wiki/manifest/queue files unless the human asks not to.

## Quality Bar

Do not dump summaries. Compile durable knowledge:

- definitions, theorems, lemmas, propositions, corollaries, remarks, proofs
- exact hypotheses and conclusions
- relationships to existing concepts
- obstructions or dependency gaps, preferably linked to `Obstruction_*` cards
  when durable
- references that should be fetched later

## Formats

Use the templates in `../ingest/reference-manifest-format.md`. Use notation
rules from `../ingest/reference-math-notation.md`.
