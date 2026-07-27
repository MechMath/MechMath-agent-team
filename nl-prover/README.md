# NL-Prover

**Natural Language Prover (NL-Prover)** — the natural-language proving agent of
the MechMath Agent Team (MMAT). NL-Prover orchestrates a hub-and-spoke team of
specialist subagents to decompose an open mathematical problem into a lemma DAG,
generate informal proofs, and independently verify them, while a deterministic
command-line tooling layer handles retrieval, extraction, linting, and
cross-model verification.

This repository ships **two harness instantiations** over the same `prompts/`,
`cli_tools/`, and skills:

- **Codex harness** — root instructions `AGENTS.md`; agents `.codex/agents/*.toml`;
  allowlist `.codex/rules/default.rules`; skills under `.agents/skills/`.
- **Claude Code harness** — root instructions `CLAUDE.md`; agents
  `.claude/agents/*.md` (dispatched via the Task tool with the matching
  `subagent_type`); allowlist `.claude/settings.json`; skills under
  `.claude/skills/` (a symlink to the shared `.agents/skills/`).

In both, a centralized Orchestrator dispatches project-scoped specialist agents,
each of which reads its matching specialist prompt (`prompts/*.md`) and
communicates only through files. The normative content of `AGENTS.md` and
`CLAUDE.md` is identical and kept in sync; only the dispatch mechanics differ.
Claude Code additionally supports hooks, which makes the ADR 0020 index-freshness
precondition mechanically enforceable (see `CLAUDE.md ## Hooks`).

## Agent roles (paper Table 1a)

| Layer | Roles (repo agent names) |
|-------|--------------------------|
| Core derivation baseline | `sketcher`, `generator`, `verifier` |
| Grounded infrastructure | `searcher`, `code-executor` |
| Advanced reasoning | `auditor`, `explorer`, `synthesizer`, `regulator`, `ce-hunter` |
| Documentation | `refiner`, `writer` |

`kb-manager` is retained as the Knowledge-Base bridge. `refiner` covers both
plan-simplification (pre-generation) and proof-shortening (post-verification)
modes. The Orchestrator only routes, records, merges verified artifacts, and
follows Verifier verdicts — it never authors mathematics.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url> && cd NL-Prover
uv sync   # installs the dependencies used by the cli_tools
```

### Codex orchestrator startup

Start Codex from the `NL-Prover` directory and grant write access only to the
runtime data locations that agents are allowed to update:

```bash
cd /path/to/NL-Prover
export DATA_DIR="$(cd ../data && pwd)"
codex -C . \
  --add-dir "$DATA_DIR/workspace" \
  --add-dir "$DATA_DIR/inbox"
```

This lets Codex read the surrounding project data, write proof workspaces under
`data/workspace`, and write KB-Manager inbox notes under `data/inbox`. Do not add
the whole `data` directory as writable unless you intentionally want agents to
modify other data subdirectories.

### Environment variables

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `KB_MANAGER_DIR` | No | Path to the KB-Manager knowledge base directory. Overridable per-command with `--kb-manager-dir`. |
| `DATA_DIR` | No | Shared data root (defaults to `../data`). |
| `GEMINI_API_KEY` | For Gemini verification | Google AI API key |
| `OPENAI_API_KEY` | For GPT verification | OpenAI API key |
| `OPENROUTER_API_KEY` | Preferred for discussion and verification | OpenRouter API key that can proxy Gemini/GPT-compatible models |

`settings.py` loads `.env` automatically. If you do not have direct Google/OpenAI
keys, set `OPENROUTER_API_KEY` and the `external.py` checks (`gemini`, `gpt`,
`discuss`) will use OpenRouter-compatible models instead.

## Command-line tooling layer (paper Table 1b)

The deterministic "exoskeleton" lives in `cli_tools/` and is exposed as **five
tool facades**, one per purpose; each is the single entry over an internal
`cli_tools/_<name>/` package (never called directly):

```bash
uv run python cli_tools/<facade>.py <subcommand> ...
```

| Facade | Purpose | Subcommands |
|--------|---------|-------------|
| `memory.py` | remember / recall / KB (three tiers) | `read`, `refresh`, `append`, `render-longterm`, `aggregate-candidates`, `inbox-write`, `card-lint` |
| `search.py` | find external results | `arxiv`, `matlas`, `index`, `frontier`, `citation-graph` |
| `external.py` | independent external-LLM checks | `gemini`, `gpt`, `discuss` |
| `gate.py` | mechanical accept/complete checks | `complete`, `stop`, `proof-attempt`, `proof-review`, `review-packet`, `result-contract`, `citation-audit` |
| `workspace.py` | navigate this problem's files | `references`, `presentation`, `ledger`, `refs-bib` |

Helpers shared by several facades (`DATA_DIR` resolution and CLI logging, the
index-view/scoring/JSONL helpers, the OpenRouter client) live in
`cli_tools/_common/`.

Runtime problem/proof data lives **outside** this repository (under `DATA_DIR`);
NL-Prover ships no `problems/` or `proofs/` directories.

## Project structure

```
AGENTS.md               # Codex Orchestrator instructions (hub-and-spoke rules)
CLAUDE.md               # Claude Code Orchestrator instructions (mirror of AGENTS.md)
.codex/
  agents/*.toml         # Codex custom agent registrations (13 specialists)
  config.toml           # concurrency / depth limits
  rules/default.rules   # allowlisted tool invocations
.codex-plugin/          # Codex plugin manifest
.claude/
  agents/*.md           # Claude Code subagent registrations (13 specialists)
  settings.json         # allowlisted tool invocations (shared)
  skills -> ../.agents/skills   # symlink; shared skill set
.agents/skills/         # orchestration + tooling skills (entry: nl-prover)
prompts/                # specialist prompts (one per agent) + orchestration.md
cli_tools/              # deterministic command-line tooling layer
settings.py             # loads .env; exposes DATA_DIR, KB_MANAGER_DIR, API keys
memory.md               # generated resident long-term constraint memory
tex/                    # article/writeup templates
tests/harness_tools/    # unit tests for the cli_tools
```

## Documentation

- `AGENTS.md` — Orchestrator core invariants, delegation triggers, routing.
- `.agents/skills/nl-prover/SKILL.md` — orchestration cookbook entry point.
- `.agents/skills/memory-routing/SKILL.md` — operational specification of the
  stratified continual-memory system (ADR 0016, paper §2.3.2).
