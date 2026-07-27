# FL-Prover

**Formal Language Prover** — a multi-agent Lean 4 theorem-proving harness. It
formalizes mathematical statements into Lean 4, searches for proofs, and verifies
them mechanically, so validity is decided *deterministically by the Lean 4
compiler kernel* rather than by an LLM's opinion.

This repository is a harness, not a monolith: a generic orchestration scaffold
(control / execution / augmentation planes) instantiated with Lean specialists and
a Lean toolchain.

## What Enters the Master Development

Nothing reaches the master Lean development until all four gates pass, plus one
meaning check no compiler can do:

| # | Gate | Command |
|---|------|---------|
| 1 | It compiles | `lean.py check` |
| 2 | No `sorry` / `admit` | `lean.py scan` |
| 3 | No axiom outside the accepted base | `lean.py axioms` |
| 4 | The protected statement is unchanged | `lean.py guard check` |
| 5 | The statement still means what the source says | F-Reviewer, re-checked by Regulator |

Gate 5 is why a compiling proof is not automatically a correct one: the compiler
checks the Lean statement, not its correspondence to the book, paper, or user
statement the target came from.

## Specialist Roles

| Role | subagent_type | Responsibility |
|------|---------------|----------------|
| Formalizer | `formalizer` | Source statements → Lean declarations with `sorry` bodies. |
| F-Reviewer | `f-reviewer` | Statement fidelity gate; approves the statement snapshot. |
| F-Generator | `f-generator` | Proves one assigned declaration in an isolated scratchpad. |
| Integrator | `integrator` | The sole merge path into the master development. |
| Golfer | `golfer` | Post-gate cleanup that must not change proof logic. |
| Regulator | `regulator` | End-of-wave audit; classifies traps; edits nothing. |
| Blueprinter | `blueprinter` | Decomposition plan for a hard or repeatedly failing target. |

The Orchestrator (root `CLAUDE.md` / `AGENTS.md`) routes; it never proves. There
is **no fixed pipeline** — it dispatches whichever role owns the current blocker,
following the cookbook in `.agents/skills/orchestration/`.

## Tools

Seven model-facing facades, each the single entry over an internal
`cli_tools/_<name>/` package:

| Facade | Purpose |
|--------|---------|
| `lean.py` | Lean toolchain: `check`, `scan`, `axioms`, `guard`, `index`, `search <engine>` |
| `control.py` | Control plane: `task` (ledger), `wave` (wave summary) |
| `memory.py` | Three-tier memory: local / long-term negative constraints / knowledge base |
| `search.py` | Literature search: `arxiv`, `matlas`, `index`, `frontier`, `citation-graph` |
| `external.py` | External-LLM calls: `gemini`, `gpt`, `discuss`, `golf`, `informal` |
| `gate.py` | Mechanical accept / stop gates |
| `workspace.py` | Navigation of the current problem's files |

Two different things are called "search": `lean.py search`
(leandex / loogle / leanfinder / leansearch / state / hammer) finds *Mathlib
declarations*; `search.py` finds *papers*.

## Dual Harness

The same `prompts/`, `cli_tools/`, `scripts/`, and skills drive two runtimes:

- **Claude Code** — `CLAUDE.md` + `.claude/agents/*.md` (Task-tool dispatch).
- **Codex** — `AGENTS.md` + `.codex/agents/*.toml` (custom agents; `max_threads = 6`,
  `max_depth = 1`).

`CLAUDE.md` and `AGENTS.md` carry identical normative content and must stay in
sync; only dispatch mechanics differ. Skills live once under `.agents/skills/`
(`.claude/skills` is a symlink to it).

## Layout

```
FL-Prover/
├── CLAUDE.md / AGENTS.md      # Orchestrator instructions (Claude / Codex)
├── settings.py                # Config (loads .env): DATA_DIR, KB_MANAGER_DIR, keys
├── cli_tools/                 # Deterministic tool exoskeleton
│   ├── lean.py / _lean/           # check, scan, axioms, guard, index, search
│   ├── control.py / _control/     # task ledger + wave summary
│   ├── memory.py / _memory/       # three-tier continual memory
│   ├── search.py / _search/       # arxiv, matlas, frontier, citation-graph
│   ├── external.py / _external/   # Gemini / GPT / discuss / golf / informal
│   ├── gate.py / _gate/           # mechanical accept / stop gates
│   ├── workspace.py / _workspace/ # references, presentation, provenance ledger
│   └── _common/                   # shared internals (paths, indexing, openrouter)
├── scripts/                   # run_claude.py (CLI), runner.py (session loop)
├── prompts/                   # orchestration.md + role prompts + references/
├── tests/                     # harness unit tests
├── tex/                       # LaTeX templates
├── .claude/ .codex/ .agents/skills/   # dual-harness registrations + shared skills
└── memory.md                  # resident long-term negative-constraint memory (generated)
```

## Setup

```bash
uv sync
cp .env.example .env    # then fill in DATA_DIR, KB_MANAGER_DIR, and API keys
```

Runtime problem data lives **outside** the repo under `DATA_DIR` (default
`../data`). A working Lean 4 toolchain (`lake`, `elan`) is required for the
compile, scan, axiom, and index tools; set `LEAN_ELAN_HOME` if elan is not in
`~/.elan`.

## Workspace

Each problem gets `DATA_DIR/workspace/<problem_id>/`: the master Lean
development, one scratchpad per dispatched agent (`scratch/<role>/<task_id>/`),
the task ledger under `.claude/state/`, and the local memory tier. Layout and
artifact ownership: `prompts/references/workspace-and-ownership.md`.
