---
name: lean-archive
description: "Use when organizing a registered Lean 4 source file into thematic files, creating Lean wiki cards, and cross-indexing formal proofs with KBManager concept pages."
---

# Lean Archive

Use this skill after a `.lean` file has been registered under
`${DATA_DIR:-data}/raw_sources/<hash12>/`.

This workflow has three phases. Each phase needs human confirmation before
proceeding.

## Phase 1: Organize

1. Locate the file:
   ```bash
   find "${DATA_DIR:-data}/raw_sources" -maxdepth 2 -name "<filename.lean>" | head -1
   ```
2. Read the full file.
3. Build a structural map:
   - declarations: `theorem`, `lemma`, `proposition`, `corollary`, `def`,
     `abbrev`, `axiom`, `structure`, `class`, `instance`
   - declaration name and type signature
   - preceding docstring
   - proof status: proved, partial (`sorry`), or axiom
   - namespaces and imports
4. Propose thematic split:
   ```text
   Raw file: <filename> (<n> declarations)

   Proposed units:
     [A] <ThematicName> (<n> declarations)
         - <description>
         Declarations: ...
   ```
5. Wait for confirmation.
6. Write confirmed units to `${DATA_DIR:-data}/lean/<ThematicName>.lean` with
   an archive header preserving source path and date.

## Phase 2: Index

For each organized file, create
`${DATA_DIR:-data}/wiki/Lean_<ThematicName>.md`:

```yaml
---
tags: [lean, formal-proof]
date: YYYY-MM-DD
lean_file: $DATA_DIR/lean/<ThematicName>.lean
proof_status: proved | partial | mixed
source_count: 1
---
```

Include:

- `## Overview`
- `## Declarations` table
- `## Connections`

Update `${DATA_DIR:-data}/wiki/index.md`:

- proved/mixed units under `## Formal Proofs`
- meaningful `sorry` declarations under `## Conjectures`
- relevant unresolved issues under `## Obstruction`

Wait for confirmation before Phase 3.

## Phase 3: Cross-Index

1. Read `${DATA_DIR:-data}/wiki/index.md`.
2. Match Lean cards to existing `Concept_*` pages by declaration names, type
   signatures, and docstrings.
3. Add `## Formal Proofs` links to matched concept pages.
4. Fill `## Connections` in each Lean card.
5. Move the raw source manifest entry to `## Ingested`; `Wiki page` should list
   all created `[[Lean_*]]` cards.
6. Append `${DATA_DIR:-data}/wiki/log.md`:
   ```markdown
   ## [YYYY-MM-DD] ingest-lean | <original filename>
   - Organized into: <files>
   - Created cards: <cards>
   - Updated concepts: <concepts or "none">
   - Proof status: <n proved>, <n partial>, <n axioms>
   ```
7. Commit changed `${DATA_DIR:-data}/lean/`, `${DATA_DIR:-data}/wiki/`, and
   manifest files unless the human asks not to.
