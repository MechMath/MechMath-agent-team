---
name: query
description: "Use when answering a research question from the KBManager wiki and optionally preserving a non-obvious synthesis, partial progress, or obstruction card."
---

# Query KBManager

Use this skill when the human asks about knowledge already compiled into
`${DATA_DIR:-data}/wiki/`.

## Workflow

1. Read `${DATA_DIR:-data}/wiki/index.md` in full.
2. Identify every plausibly relevant page. Include source, concept, analysis,
   partial-proof, obstruction, and Lean cards when they may affect the
   answer.
3. Deep-read relevant wiki pages.
4. Follow one level of relevant `[[WikiLink]]` expansion.
5. Answer with inline wiki citations like `[[PageName]]`.
6. Clearly distinguish:
   - directly stated facts,
   - your logical inferences,
   - open questions or gaps in the wiki.

## Persisting New Knowledge

Only write files if the query produces something a future reader could not
trivially reconstruct from existing pages.

Qualifies:

- non-trivial comparison or duality
- newly discovered dependency or implication chain
- obstruction or falsified path constraint between pages
- reusable partial proof progress whose remaining gap should be preserved
- structural framework or gap across multiple pages

Does not qualify:

- definition lookup
- summary of one page
- direct answer already stated in existing pages

If it qualifies:

1. Create `${DATA_DIR:-data}/wiki/Analysis_<Topic>.md`,
   `${DATA_DIR:-data}/wiki/PartialProof_<Topic>.md`, or
   `${DATA_DIR:-data}/wiki/Obstruction_<Topic>.md`.
2. Update `${DATA_DIR:-data}/wiki/index.md`.
3. Append `${DATA_DIR:-data}/wiki/log.md`:
   ```markdown
   ## [YYYY-MM-DD] query | <Question summary>
   - Created: $DATA_DIR/wiki/<new page>
   ```
4. Commit changed wiki files unless the human asks not to.

If it does not qualify, answer without writing files.
