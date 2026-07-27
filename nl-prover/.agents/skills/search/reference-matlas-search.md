# matlas-search — Mathematical Statement Search

Semantic search over 8 million+ mathematical statements extracted from ~435K peer-reviewed papers and ~1.9K textbooks (1826–2025). Finds theorems, lemmas, and definitions using natural language — no exact notation required.

## CLI Invocation

```bash
uv run python cli_tools/search.py matlas QUERY [--num-results N] [--cache-dir DIR]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Natural language search query |
| `--num-results` | no | 10 | Number of results (minimum 10) |
| `--cache-dir` | no | — | Directory to cache results as a Markdown file |

## Output

JSON object:
```json
{
  "ok": true,
  "count": 10,
  "results": [
    {
      "type": "paper" | "book",
      "entity_name": "Theorem 1.2",
      "title": "Full paper/book title",
      "authors": "Author names",
      "year": "2021",
      "doi": "doi.org/...",
      "statement": "Mathematical statement text...",
      "candidate_id": "<id for feedback>"
    }
  ]
}
```

## Examples

```bash
uv run python cli_tools/search.py matlas "Banach fixed point theorem"
uv run python cli_tools/search.py matlas "spectral gap for random matrices" --num-results 20
uv run python cli_tools/search.py matlas "convergence of Fourier series L2" --cache-dir ../data/workspace/proj/queries/fourier_l2/matlas/
```

## Notes

- Use this when looking for a specific known result — the statement text is directly usable.
- Do not stop at matlas for research-level/current topics. Matlas may miss arXiv preprints and recent papers; run `arxiv-search` with related names and keywords to complement the statement-level results.
- This search path is free to use in this workflow and does not require an OpenAI/Google/Anthropic key.
- Use `--cache-dir` to persist results under `queries/<query_id>/matlas/`.
- Results include `candidate_id` for feedback; ignore this field during normal use.
