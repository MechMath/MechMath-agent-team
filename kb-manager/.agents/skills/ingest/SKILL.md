---
name: ingest
description: "Use when processing a registered KBManager raw source; dispatches to source-style ingest for external math references or analysis-style ingest for internal problem-solving notes."
---

# Ingest Dispatcher

Use this skill after a file has been registered or fetched into
`${DATA_DIR:-data}/raw_sources/<hash12>/`.

This skill chooses the right ingest mode. Do not default to creating a
`Source_*` page until the file type has been classified.

## Shared Setup

1. Locate the source by filename:
   ```bash
   find "${DATA_DIR:-data}/raw_sources" -maxdepth 2 -name "<filename>" | head -1
   ```
2. Check `sources_manifest.md` `## Ingested` for this hash or filename. If it is
   already ingested, ask before re-ingesting.
3. Read enough of the file to classify it. For `.tex`, preserve commands. For
   PDFs, read rendered pages rather than trusting plain text extraction.
4. Read `${DATA_DIR:-data}/wiki/index.md` before deciding which pages to update.
5. Before writing, summarize 3-5 core takeaways and get human acknowledgement.

## Mode Selection

Use `ingest-source` for external mathematical knowledge:

- books, papers, chapters, lecture notes, expository references
- files whose durable value is definitions, theorems, lemmas, proofs,
  hypotheses, examples, or bibliography
- output normally includes a `Source_*` page and concept cards/updates

Use `ingest-analysis` for internal problem-solving memory:

- proof attempts, verifier reports, correction notes, error summaries, query
  syntheses, solution summaries, TODO/checklist notes
- files whose durable value is next-time behavior: pitfalls, correctness
  checks, proof patterns, hypothesis audits, reusable warnings
- output normally includes an `Analysis_*`, `PartialProof_*`, or
  `Obstruction_*` page and links into existing concepts, not a redundant
  `Source_*` page

For Lean files, return a handoff to the `archivist` agent.

If a file mixes modes, choose the dominant durable use. If genuinely ambiguous,
ask the human which mode to use before writing.

## Shared Completion

Every ingest mode must:

1. Update `sources_manifest.md`: move the entry from `## Pending Ingest` to
   `## Ingested`, or create an ingested entry if missing.
2. Set `Wiki page` to the primary durable page created or updated. For
   analysis-style ingest this may be an `Analysis_*`, `PartialProof_*`, or
   `Obstruction_*` page.
3. Remove a matching `download_queue.md` pending entry for the source itself if
   one exists.
4. Append one entry to `wiki/log.md`.
5. Commit changed wiki/manifest/queue files unless the human asks not to.

## Shared References

- Mathematical transcription: `reference-math-notation.md`
- Manifest and page formats: `reference-manifest-format.md`
