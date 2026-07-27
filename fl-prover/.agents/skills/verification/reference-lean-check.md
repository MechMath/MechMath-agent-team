# lean-check — Local Compile Check

Check if Lean code compiles without errors using `lake env lean`. Runs locally — no API key needed.

## CLI Invocation

```bash
python cli_tools/lean.py check FILE [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `FILE` | yes | — | Lean file path to check |
| `--timeout-seconds` | no | 120 | Max execution time (default: 120) |
| `--summary` | no | off | Return counts plus shortened diagnostics |
| `--compact` | no | off | Return counts and diagnostic locations only |
| `--severity` | no | all | Filter diagnostics; may be repeated (`error`, `warning`, `info`) |
| `--line-start` / `--line-end` | no | all | Filter diagnostics to a line range |
| `--include-sorries` | no | off | Include compact `sorry` / `admit` scan output |

## Output

Returns JSON:
- `okay` (bool) — whether the file compiled without errors
- `lean_messages` — list of errors, warnings, and infos with line numbers (`file_name`, `line`, `column`, `severity`, `data`)
- `failed_declarations` — list of theorem/definition names that failed

## Examples

```bash
python cli_tools/lean.py check proof.lean
python cli_tools/lean.py check proof.lean --timeout-seconds 300
python cli_tools/lean.py check proof.lean --compact
python cli_tools/lean.py check proof.lean --summary --severity error
python cli_tools/lean.py check proof.lean --summary --severity warning
python cli_tools/lean.py check proof.lean --summary --line-start 120 --line-end 180
python cli_tools/lean.py check proof.lean --compact --include-sorries
```

Use `--compact` first when you only need status, counts, and error/warning locations. Use `--summary` when you need shortened diagnostic text. Use full default output when the truncated diagnostic is not enough.

For completion checks, prefer:

```bash
python cli_tools/lean.py scan proof.lean --plain
python cli_tools/lean.py scan proof.lean --context-lines 2
```

For local statement or declaration inspection:

```bash
python cli_tools/lean.py index declarations proof.lean --kind theorem
python cli_tools/lean.py index statement proof.lean theorem_name
python cli_tools/lean.py index outline proof.lean
```

## Notes

- No `--environment` flag needed — automatically detects the Lean project root by finding `lean-toolchain`.
- Runs `lake env lean` locally, so the project must have been built at least once (`lake build` or `lake exe cache get`).
- No API key required.
- Multiple checks can run in parallel (each is an independent process).
