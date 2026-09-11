# NL-Prover

**Natural Language Prover (NL-Prover)** — the natural-language proving agent of
the MechMath Agent Team (MMAT). NL-Prover orchestrates a hub-and-spoke team of
specialist subagents to decompose an open mathematical problem into a lemma DAG,
generate informal proofs, and independently verify them, while a deterministic
command-line tooling layer handles retrieval, extraction, linting, and
cross-model verification.

This repository ships **two harness instantiations** over the same `prompts/`,
`cli_tools/`, skills, and `docs/`:

- **Codex harness** — root instructions `AGENTS.md`; agents `.codex/agents/*.toml`;
  allowlist `.codex/rules/default.rules`; skills under `.agents/skills/`.
- **Claude Code harness** — root instructions `CLAUDE.md`; agents
  `.claude/agents/*.md` (dispatched via the Task tool with the matching
  `subagent_type`); allowlist `.claude/settings.json`; skills under
  `.claude/skills/` (a symlink to the shared `.agents/skills/`).

In both, a centralized Orchestrator dispatches project-scoped specialist agents,
each of which reads its matching specialist prompt (`prompts/*.md`) and
communicates only through files. What is guaranteed between `AGENTS.md` and
`CLAUDE.md` is narrower than "identical": four sections — Core Invariants,
Routing, Tool Rules, Rules for All Agents — must say the same thing, and
`gate.py contracts` now checks them (`_gate/contracts.py` `SYNCED_SECTIONS`).
It normalises away the dispatch mechanics first, so `.codex/agents` versus
`.claude/agents` is not drift, then splits what is left two ways: the same line
said differently on the two sides is an **error**, because a reader cannot tell
which side is current; a line one side has and the other does not is a
**warning**, because platform-only additions are legitimate and erroring on them
would grow a list of exceptions. The files do diverge outside those four
sections, by design: `CLAUDE.md` carries a `## Hooks` section that has no Codex
counterpart, and inside Tool Rules it carries one extra sentence — the facades
are allowlisted for auto-run in `.claude/settings.json`, which is true of no
Codex file. The gate reports that as a warning today, which is the correct
verdict, not an outstanding bug.

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

### Claude Code orchestrator startup

Launch from the `NL-Prover` directory too — and export `NLPROVER_WORKSPACE`:

```bash
cd /path/to/NL-Prover
export DATA_DIR="$(cd ../data && pwd)"
export NLPROVER_WORKSPACE="$DATA_DIR/workspace/<problem>"
claude --add-dir "$DATA_DIR/workspace" \
       --add-dir "$DATA_DIR/inbox"
```

**Both halves are load-bearing, and getting either wrong is silent.**
`.claude/settings.json` is read from the directory Claude Code is launched in,
and it carries both the tool allowlist and the three `Agent|Task` hooks
(`dispatch_log.py` on Pre and Post, `nesting_guard.py` on Pre). Launch from the
problem workspace instead and that file is never read at all: no allowlist, and
— because `nesting_guard.py` is what enforces the no-spawn half of invariant 1
on this platform, the counterpart to Codex's `max_depth = 1` — no nesting guard
either. Launch from this repo without `NLPROVER_WORKSPACE` and the hooks load
but `dispatch_log.py` finds nowhere to write: its second resolution step looks
for `STATUS.md` at `cwd` or above, and the workspaces live under `DATA_DIR` in a
different repository, so nothing matches. It declines to guess a workspace on
purpose — attributing one run's dispatches to another run's log would make the
completeness check read as healthy — so it writes nothing and says nothing.

That combination has never yet been used. Measured across the whole corpus: 159
rows in 6 workspace `logs/dispatch.jsonl` files, **zero** carrying
`source: "hook"`; every row was written by hand. Until this is the launch
command, treat `platform_mix`, `prompt_shape` and `token_cost` in `gate speed`
as unmeasured — which is what the gate already reports.

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
| `OPENALEX_MAILTO` | For OpenAlex queries | Contact address that puts `search citation-graph` and `workspace refs-bib` in the OpenAlex polite pool. Unset, both still run but are rate-limited harder. |
| `NLPROVER_WORKSPACE` | **Yes, on Claude Code** | The problem workspace the dispatch hook writes into. Unset, `.claude/hooks/dispatch_log.py` resolves nothing and logs nothing, silently. |
| `NLPROVER_VERIFIER_CMD` | For `verify.py dispatch --run` | Cold-start verifier command, fed the dispatch text on stdin (e.g. `claude -p --permission-mode acceptEdits`, `codex exec`). Unset, `--run` refuses rather than no-op. |

`settings.py` loads `.env` automatically. If you do not have direct Google/OpenAI
keys, set `OPENROUTER_API_KEY` and the `external.py` checks (`gemini`, `gpt`,
`discuss`) will use OpenRouter-compatible models instead.

`ANTHROPIC_API_KEY` is **not** in the table or in `.env.example`. `settings.py`
still defines it, but no module imports it — the three external checks import
only `GEMINI_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY`. Setting it
configures nothing.

## Command-line tooling layer (paper Table 1b)

The deterministic "exoskeleton" lives in `cli_tools/` and is exposed as **six
tool facades**, one per purpose; each is the single entry over an internal
`cli_tools/_<name>/` package (never called directly). Those six are the whole
model-facing surface; `cli_tools/migrate_memory_md.py` is a seventh file but not
a seventh facade — it is a one-time, human-run ADR 0017 migration, dry-run by
default, deliberately outside the Codex allowlist.

```bash
uv run python cli_tools/<facade>.py <subcommand> ...
```

| Facade | Purpose | Subcommands |
|--------|---------|-------------|
| `memory.py` | remember / recall / KB (three tiers) | `read`, `refresh`, `append`, `budget`, `render-longterm`, `candidate`, `aggregate-candidates`, `inbox-write`, `card-lint` |
| `search.py` | find external results | `arxiv`, `matlas`, `index`, `frontier`, `citation-graph` |
| `external.py` | independent external-LLM checks | `gemini`, `gpt`, `discuss` |
| `gate.py` | mechanical accept/complete checks | `complete`, `stop`, `proof-attempt`, `proof-review`, `review-packet`, `result-contract`, `citation-audit`, `discovery`, `dag`, `speed`, `summary`, `contracts` |
| `verify.py` | assemble a verification dispatch a prior verdict cannot enter | `dispatch` (`--mode certification\|discovery`, `--run`) |
| `workspace.py` | navigate this problem's files | `references`, `presentation`, `ledger`, `refs-bib`, `status` |

Helpers shared by several facades (`DATA_DIR` resolution and CLI logging, the
index-view/scoring/JSONL helpers, the OpenRouter client) live in
`cli_tools/_common/`.

Runtime problem/proof data lives **outside** this repository (under `DATA_DIR`);
NL-Prover ships no `problems/` or `proofs/` directories.

## Project structure

```
AGENTS.md               # Codex Orchestrator instructions (hub-and-spoke rules)
CLAUDE.md               # Claude Code Orchestrator instructions (four sections
                        #   kept in sync with AGENTS.md by `gate contracts`; plus `## Hooks`)
.codex/
  agents/*.toml         # Codex custom agent registrations (13 specialists)
  config.toml           # concurrency / depth limits
  rules/default.rules   # allowlisted tool invocations
.codex-plugin/          # Codex plugin manifest
.claude/
  agents/*.md           # Claude Code subagent registrations (13 specialists)
  settings.json         # allowlist + the three Agent|Task hooks; read only when
                        #   Claude Code is launched from this directory
  skills -> ../.agents/skills   # symlink; shared skill set
.agents/skills/         # orchestration + tooling skills (entry: nl-prover)
prompts/                # specialist prompts (one per agent) + orchestration.md
cli_tools/              # deterministic command-line tooling layer
settings.py             # loads .env; exposes DATA_DIR, KB_MANAGER_DIR, API keys
docs/adrs/              # architecture decision records
tex/                    # article/writeup templates
tests/harness_tools/    # unit tests for the cli_tools
```

## Documentation

- `AGENTS.md` — Orchestrator core invariants, delegation triggers, routing.
- `.agents/skills/nl-prover/SKILL.md` — orchestration cookbook entry point.
- `docs/adrs/` — design decisions, including the stratified continual memory
  system (ADR 0016, paper §2.3.2).
