# Register Source

Use when the human has a local file that should become a KBManager raw source.

## Resolve Input

- No argument: list `${DATA_DIR:-data}/inbox/`. If exactly one non-hidden file is
  present, use it. If multiple are present, ask which one to register.
- Bare filename: resolve under `${DATA_DIR:-data}/inbox/`.
- Path with `/`: use the supplied path.
- Optional second argument may specify target filename; preserve extension unless
  the human explicitly asks otherwise.

## Steps

1. Verify the file exists.
2. Compute full SHA-256 and `HASH12`.
3. Read `sources_manifest.md` and check duplicate `HASH12` in Pending or
   Ingested. Stop unless the human confirms duplicate registration.
4. Create `raw_sources/<HASH12>/`.
5. Copy the file into that directory.
6. If the source was from `inbox/`, move the inbox copy to repository-root
   `trashbin/` only after successful copy, preserving enough path/name context
   to identify where it came from. Do not permanently delete it.
7. Update `sources_manifest.md`:
   - If a pending queue/placeholder entry matches the filename, update it.
   - Otherwise add a new `## Pending Ingest` entry.
8. Remove matching `download_queue.md` pending block by target filename.
9. Report source path, SHA-256, and size.

Manifest entry:

```markdown
### `<hash12>` — `<filename>`
- **Path**: `$DATA_DIR/raw_sources/<hash12>/<filename>`
- **Title**: <title or filename>
- **Authors**: <authors or "unknown">
- **Year**: <year or "unknown">
- **Size**: <size>
- **SHA256**: <full hash>
- **Added**: YYYY-MM-DD
- **Ingested**: no
- **Wiki page**: —
```
