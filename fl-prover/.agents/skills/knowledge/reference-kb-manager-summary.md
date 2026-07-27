# KB summary — List Knowledge Base Concepts, Analyses, and Experience

Lists concept, analysis/comparison, and experience pages currently indexed in the
KB-Manager knowledge base (KB tier). This is a local file read — zero API cost,
instant. The read goes through the unified memory entry `memory.py` (the KB-tier logic is
the internal module `cli_tools/_memory/kb.py`, not called directly).

> **Always run this first** before issuing a deep KB-Manager query through
> `queries/<query_id>/`, to know what is already available.

## CLI Invocation

```bash
uv run python cli_tools/memory.py read --tier kb --view compact
```

Optional arguments:

| Argument | Required | Description |
|----------|----------|-------------|
| `--data-dir PATH` | no | Override `DATA_DIR`; must contain `wiki/index.md` |
| `--query TEXT` | no | Filter the concept/analysis/experience entries |

## Output

Unified memory envelope (`tier`/`view` header) wrapping the KB index:
```json
{
  "tier": "kb",
  "view": "compact",
  "ok": true,
  "concept_count": 12,
  "analysis_count": 2,
  "experience_count": 3,
  "total_count": 17,
  "concepts": ["[[Concept_SelmerGroup]] — ..."],
  "analyses": ["[[Analysis_IwasawaSelmer_1_3_ErrorKnowledge]] — ..."],
  "experience": ["[[Experience_neg-hidden-hyp]] — ..."]
}
```

Use `analysis_count`, `experience_count`, `total_count`, `analyses`, and
`experience` when deciding whether a previous failure, counterexample,
proof-hygiene note, or long-term negative constraint is relevant.

## Examples

```bash
uv run python cli_tools/memory.py read --tier kb --view compact
uv run python cli_tools/memory.py read --tier kb --data-dir ../data --query "Selmer"
```

## Notes

- If `total_count` is 0 or the index file is missing, the knowledge base is empty.
- Use the concept and analysis names from this output as search terms in the
  KB-Manager query request. Analysis pages are especially relevant for
  `counterexamples`, `proof strategy`, `previous failures`, and `related
  results` requests.
