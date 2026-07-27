# Queue Add

Use when a resource should be tracked for manual download without attempting an
automatic fetch, or when a fetch fallback needs to queue an inaccessible source.

## Parse

Input may be:

- URL
- DOI
- free-text citation
- citation plus target filename

Extract title, authors, year, URL, DOI, and target filename where possible.

## Target Filename

If no filename is supplied, construct:

```text
<FirstAuthorLastName><Year>_<ShortTitle>.pdf
```

Use snake_case, strip special characters, keep the stem short.

## Append

Read `download_queue.md`, find the highest pending id, and append:

```markdown
### [N] <Title>
- **URL**: <url or "not provided">
- **DOI**: <doi or "unknown">
- **Authors**: <authors or "unknown">
- **Year**: <year or "unknown">
- **Target filename**: `$DATA_DIR/raw_sources/<hash_tbd>/<filename>`
  *(hash directory will be determined after manual download)*
- **Added**: YYYY-MM-DD
- **Failure reason**: Manual entry — not attempted
- **Status**: `pending`
```

Remove `*(Queue is empty.)*` if present.
