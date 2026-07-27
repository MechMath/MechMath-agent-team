# Reorganize Wiki Connections

Use for semantic enrichment of `## Connections` sections, not for basic lint.

## Scope

- No argument or `all`: read `wiki/index.md` and collect all concept pages.
- Topic/cluster: collect relevant concept and analysis pages.
- Specific analysis page: use it as the source of relationships to backfill.
- Specific partial-proof or obstruction page: use it to backfill progress,
  remaining-gap, ruled-out-path, or warning links.

## Process

1. Read target pages.
2. Record existing `## Connections`.
3. For each concept pair, ask whether a reader of page A benefits from page B.
4. Add only non-trivial links:
   - direct use,
   - theorem dependency,
   - structural analogy,
   - precursor/application,
   - local-global relationship,
   - partial-proof progress,
   - obstruction or gap,
   - formalization link to a `Lean_*` card.
5. Prefer bidirectional links, but only when both directions are informative.
6. Each connection bullet must include a one-sentence reason naming the specific
   theorem, proposition, definition, or structural phenomenon.

Avoid vague links such as "both involve p-adic methods".

## Optional Analysis Page

If the reorganization reveals a genuinely new structural insight, create
`Analysis_<Topic>.md`, update `index.md`, append to `log.md`, and commit.

If it only adds links, append:

```markdown
## [YYYY-MM-DD] reorganize | <scope>
- Pages updated: <pages>
- New links added: <n>
- New analysis page: none
```
