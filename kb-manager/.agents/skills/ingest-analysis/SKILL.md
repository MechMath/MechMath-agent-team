---
name: ingest-analysis
description: "Use when ingesting internal problem-solving notes, verifier reports, partial proof progress, obstructions, error summaries, or query syntheses into reusable Analysis, PartialProof, or Obstruction cards."
---

# Analysis-Style Ingest

Use this mode for internal problem-solving memory. The goal is not to summarize
the file as a source; the goal is to preserve reusable next-time behavior.

## Inputs

Start from a registered file under `${DATA_DIR:-data}/raw_sources/<hash12>/`.
The dispatcher skill `ingest` handles locating, duplicate checks, and human
acknowledgement before this workflow writes.

## Workflow

1. Read the full note and identify its reusable payload:
   - correctness conditions
   - proof pitfalls and fixes
   - missing hypotheses or precondition audits
   - recurring errors
   - reliable proof patterns or checklists
   - links to prior queries, verifier reports, or proof files when relevant
2. Choose the most reusable card type:
   - `Analysis_<Topic>.md` for proof patterns, verifier lessons, missing
     hypotheses, reusable checklists, or false shortcuts.
   - `PartialProof_<Topic>.md` for reusable partial progress: intermediate
     statements, reductions, partial routes, dependencies used, and repair
     directions that should be available to future problem-solving agents.
   - `Obstruction_<Topic>.md` for falsified path constraints: ruled-out
     assumptions, invalid shortcuts, incompatible definitions, counterexample
     signals, circular dependencies, or impossible precondition audits.
   Do not create a `Source_*` page unless the human asks or the note is also a
   substantial external reference.
3. Link the analysis-derived page from existing `Concept_*` pages where the
   warning, checklist, partial progress, or obstruction should surface during
   future queries.
4. Create new concept pages only if the note introduces a reusable mathematical
   concept, not merely a local proof tactic.
5. Update `${DATA_DIR:-data}/wiki/index.md` under the matching section, such as
   `## Analysis`, `## PartialProof`, or `## Obstruction`, depending on where the wiki already
   classifies similar pages.
6. Append one `ingest` entry to `${DATA_DIR:-data}/wiki/log.md`.
7. Update `${DATA_DIR:-data}/sources_manifest.md` as ingested with `Wiki page:
   [[Analysis_<Topic>]]`, `[[PartialProof_<Topic>]]`, or
   `[[Obstruction_<Topic>]]`.
8. Commit changed wiki/manifest/queue files unless the human asks not to.

## Page Content

An analysis page should be concise and operational:

- Purpose: what problem or failure mode this note preserves
- Reusable rule/checklist: what to do next time
- Mathematical reason: why the rule is true
- Failure mode: what false shortcut to avoid
- Connections: affected concepts, sources, and proof artifacts

A partial-proof page should preserve reusable progress:

- Target statement
- Partial result, reduction, or intermediate statement
- Strategy segment that still appears reusable
- Dependencies and concepts used
- Remaining gap, missing lemma, missing hypothesis, or blocked computation
- Possible repair direction

An obstruction page should preserve falsified path constraints:

- Ruled-out assumption, shortcut, definition, or route
- Minimal reason it is invalid
- Counterexample signal or impossible precondition audit, if any
- Consequences for related concepts or partial proofs
- Verification status and open questions

## Quality Bar

Extract behavior, not prose. The page should help a future agent avoid the same
mistake, reuse partial progress, or recognize a previously ruled-out path
without rereading the raw note.

Use Obsidian links to the concept pages that should surface the warning during
future KBManager queries.
