# Fetch Source

Use when the human provides a URL and asks KBManager to fetch it.

## arXiv First

If the URL matches `arxiv.org/abs/<id>`, `arxiv.org/pdf/<id>`, or
`ar5iv.labs.arxiv.org/html/<id>`, try to download LaTeX source first:

```bash
DATA_DIR="${DATA_DIR:-data}"
ARXIV_ID="<extracted id>"
mkdir -p "$DATA_DIR/tmp"
curl -L "https://arxiv.org/src/${ARXIV_ID}" -o "$DATA_DIR/tmp/arxiv_src_raw"
file "$DATA_DIR/tmp/arxiv_src_raw"
```

If the source is a single gzip file, decompress to a `.tex`. If it is a tar
archive, extract and select the file containing `\begin{document}`.

When a `.tex` file is found:

1. Pick the filename from the human hint or arXiv id.
2. Compute SHA-256 of the final `.tex`.
3. Copy to `raw_sources/<sha256_12>/<filename>.tex`.
4. Add a `## Pending Ingest` entry to `sources_manifest.md`.
5. Report success and offer a handoff to `ingester`.

## Web Fetch

For non-arXiv pages, fetch readable content with available web/MCP tools. Treat
these as fetch failure:

- HTTP 4xx/5xx
- login/paywall/access denied page
- empty or suspiciously short content
- binary PDF/EPUB not decoded by the fetch tool

On success:

1. Save fetched Markdown to `tmp/<filename>.md` with metadata frontmatter:
   ```yaml
   ---
   source_url: <url>
   fetched_date: YYYY-MM-DD
   fetch_status: success
   ---
   ```
2. Localize external images into the source's `assets/` directory when present.
3. Compute hash after final content is known.
4. Copy to `raw_sources/<sha256_12>/<filename>.md`.
5. Add a `## Pending Ingest` manifest entry.

## Queue Fallback

Do not return a bare fetch error. If the URL cannot be fetched:

1. Record URL, failure reason, filename hint, and any visible metadata.
2. Append an entry to `download_queue.md` `## Pending`.
3. Use the next numeric queue id.
4. Tell the human to download manually and run `$source-management` registration.

Queue entry format:

```markdown
### [N] <Title or URL>
- **URL**: <url>
- **DOI**: <doi or "unknown">
- **Authors**: <authors or "unknown">
- **Year**: <year or "unknown">
- **Target filename**: `$DATA_DIR/raw_sources/<hash_tbd>/<filename>.<ext>`
  *(hash directory will be determined after manual download)*
- **Added**: YYYY-MM-DD
- **Failure reason**: <reason>
- **Status**: `pending`
```
