# Wiki Lint

Check:

1. Orphan cards: every page except `index.md` and `log.md` should have inbound
   `[[PageName]]` references.
2. Missing YAML frontmatter: each wiki page should start with `---` and contain
   at least `tags` and `date`.
3. Duplicate concepts: compare page titles and `## Key Concepts` sections.
4. Unresolved obstructions: list pages tagged `obstruction` or
   `open-question`.
5. PartialProof coverage: list `PartialProof_*` pages that are not linked from
   their target concept, remaining-gap concept, or relevant source page.
6. Index completeness: every wiki page except `log.md` should appear in
   `wiki/index.md`.

Report findings grouped by issue type. For each issue, propose a concrete fix.
Wait for confirmation before editing.

After confirmed fixes:

```markdown
## [YYYY-MM-DD] lint | Health check
- Orphans resolved: <n>
- Frontmatter added: <n>
- Duplicates merged: <n>
- Index entries added: <n>
```

Then commit changed wiki files unless the human asks not to.
