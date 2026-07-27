# KBManager Formats

## Source Summary Page

```markdown
---
tags: [source]
date: YYYY-MM-DD
source_file: $DATA_DIR/raw_sources/<hash12>/<filename>
source_count: 1
---

# <Title>

## Summary

## Key Concepts

## Quotes & Evidence

## Connections
```

## Concept Page

```markdown
---
tags: [concept]
date: YYYY-MM-DD
source_count: <n>
---

# Concept: <Name>

## Definition

## Key Results

## Sources

## Connections
```

## Log Entry

```markdown
## [YYYY-MM-DD] ingest | <Source Title>
- Created: $DATA_DIR/wiki/<summary page filename>
- Updated concepts: <comma-separated list>
- New concepts: <comma-separated list or "none">
```

## Ingested Manifest Entry

```markdown
### `<hash12>` — `<filename>`
- **Path**: `$DATA_DIR/raw_sources/<hash12>/<filename>`
- **Title**: <title>
- **Authors**: <authors>
- **Year**: <year>
- **Size**: <size>
- **SHA256**: <full hash>
- **Added**: <date first seen or today>
- **Ingested**: YYYY-MM-DD
- **Wiki page**: [[<summary page name>]]
```
