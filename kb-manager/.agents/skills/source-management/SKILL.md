---
name: source-management
description: "Use when fetching a public URL, registering a local file, or queueing an inaccessible paper/resource for the KBManager knowledge base."
---

# Source Management

Use this skill to get raw sources into KBManager without corrupting the source
store. All paths are relative to `${DATA_DIR:-data}` unless the human supplied
an absolute path.

## Workflows

Read only the reference needed for the task:

- Fetch public URL or arXiv source: `reference-fetch-source.md`
- Register a local file from inbox or explicit path: `reference-register-source.md`
- Add a paywalled/manual resource to the queue: `reference-queue-add.md`

## Invariants

- Never place files directly in `raw_sources/`; every source must live in
  `raw_sources/<sha256_12>/`.
- Derive `<sha256_12>` from the first 12 hexadecimal characters of the SHA-256
  of the final primary file.
- Existing files in `raw_sources/` are immutable.
- Preserve the source's original filename inside its hash directory unless the
  human explicitly provides a target filename.
- Store figures and attachments only in that source's local `assets/`
  directory; create it only when needed.
- Update `sources_manifest.md` for every registered or fetched source.
- Remove matching `download_queue.md` pending entries after successful
  registration.
- Ask before re-registering a duplicate hash.

The content-addressed directory is the primary key tying a source, its
attachments, its manifest entry, and its ingested wiki pages together. The
human-readable original filename remains inside the hash directory.

## Next Step

After a successful fetch or registration, report the saved path, full SHA-256,
size, and ask whether to hand off to the appropriate specialist:

- regular sources: `ingester`
- Lean files: `archivist`
