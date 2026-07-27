# arxiv-search — arXiv Paper Search

Searches arXiv for papers matching a query. Useful for surveying a research area or finding recent work.

## CLI Invocation

```bash
uv run python cli_tools/search.py arxiv QUERY [--max-results N] [--cache-dir DIR] [--max-retries N]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Search query (topic, author, keywords) |
| `--max-results` | no | 5 | Maximum number of results |
| `--cache-dir` | no | — | Directory to cache results as a Markdown file |
| `--max-retries` | no | 3 | Retries for HTTP 429/5xx/transient URL errors |

## Output

JSON object:
```json
{
  "ok": true,
  "count": 5,
  "results": [
    {
      "title": "Paper title",
      "authors": ["Author 1", "Author 2"],
      "abstract": "First 500 characters of abstract...",
      "arxiv_id": "https://arxiv.org/abs/2301.00001",
      "published": "2023-01-01",
      "pdf": "https://arxiv.org/pdf/2301.00001"
    }
  ]
}
```

## Examples

```bash
uv run python cli_tools/search.py arxiv "Riemann hypothesis analytic number theory"
uv run python cli_tools/search.py arxiv "optimal transport Wasserstein distance" --max-results 10
uv run python cli_tools/search.py arxiv "random matrix theory eigenvalue distribution" --cache-dir ../data/workspace/proj/queries/random_matrix_context/arxiv/
```

## Notes

- Results are sorted by relevance.
- HTTP 429 responses are retried with `Retry-After` when present, otherwise
  exponential backoff.
- Use `--cache-dir` to persist results under `queries/<query_id>/arxiv/`;
  cached file is named by a hash of the query.
- For finding specific known theorem statements, use `matlas-search` because it returns statement text directly.
- For research-level/current topics, always use arXiv as a complement to matlas. ArXiv can contain preprints, recent variants, and papers not indexed by matlas.
