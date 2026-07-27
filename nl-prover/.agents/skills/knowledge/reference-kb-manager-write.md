# kb-manager-write — Save to Knowledge Base

Writes a file or inline text to the KB-Manager knowledge base inbox for later indexing.

## CLI Invocation

```bash
# Write inline content
uv run python cli_tools/memory.py inbox-write --content "TEXT" [--filename NAME]

# Copy an existing file
uv run python cli_tools/memory.py inbox-write --path FILE [--filename NAME]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--content` | yes* | — | Inline text/Markdown to write. Mutually exclusive with `--path` |
| `--path` | yes* | — | Path to an existing file to copy into the inbox |
| `--filename` | no | auto | Output filename. A date prefix (`YYYYMMDD_`) is always prepended |

*One of `--content` or `--path` is required.

## Output

JSON object:
```json
{
  "ok": true,
  "file": "/path/to/kb-manager/data/inbox/20260420_lemma1.md",
  "filename": "20260420_lemma1.md"
}
```

## Examples

```bash
# Save a verified lemma proof
uv run python cli_tools/memory.py inbox-write --path workspace/proj/lemmas/lem1/generator/proof_v2.md --filename lem1_proof.md

# Save an inline note
uv run python cli_tools/memory.py inbox-write --content "The spectral gap bound follows from Cheeger's inequality applied to..." --filename spectral_gap_note.md
```

## Notes

- Files land in the KB-Manager inbox and are picked up during the next indexing run.
- Use this after a lemma is verified to persist the result for future problems.
