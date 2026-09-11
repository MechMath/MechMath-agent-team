# FL-Prover

**Formal Language Prover** — a multi-agent Lean 4 theorem-proving harness. It
formalizes mathematical statements into Lean 4, searches for proofs, and verifies
them mechanically, so validity is decided *deterministically by the Lean 4
compiler kernel* rather than by an LLM's opinion.

This repository is a harness, not a monolith: a generic orchestration scaffold
(control / execution / augmentation planes) instantiated with Lean specialists and
a Lean toolchain.

## What Enters the Master Development

Nothing reaches the master Lean development until four mechanical gates pass,
plus two complementary statement checks that the compiler cannot perform:

| # | Gate | Command |
|---|------|---------|
| 1 | It compiles | `lean.py check` |
| 2 | No `sorry` / `admit` | `lean.py scan` |
| 3 | No axiom outside the accepted base | `lean.py axioms` |
| 4 | The protected statement is unchanged | `lean.py guard check` |
| 5 | The statement faithfully formalizes the source | F-Reviewer, re-checked by Regulator |
| 6 | The declaration literally says what the team thinks it says | Blind `statement-readback` |

The F-Reviewer sees the source and checks formalization fidelity. The blind
statement reader sees only the Lean declaration and its referenced definitions;
it explicitly audits quantifier order, aggregate versus pointwise claims,
constants, vacuity, and trivial witnesses. Every node receives a read-back before
it is accepted as proved, and again after a statement repair.

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
| Statement Read-back | `statement-readback` | Gives a context-free literal reading of a Lean declaration before acceptance. |

The Orchestrator (root `CLAUDE.md` / `AGENTS.md`) routes; it never proves. There
is **no fixed pipeline** — it dispatches whichever role owns the current blocker,
following the cookbook in `.agents/skills/orchestration/`.

## Tools

Eight model-facing facades provide the supported command-line surface:

| Facade | Purpose |
|--------|---------|
| `lean.py` | Lean toolchain: `check`, `scan`, `axioms`, `guard`, `index`, `search <engine>`, `verdict` |
| `control.py` | Control plane: `task` (ledger), `wave` (wave summary) |
| `dag.py` | Typed proof-obligation graph: `state`, `render`, `leaves`, `put`, `import` audit |
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

The normative rules live once in `prompts/normative.md`; both harness entry
documents point to it and contain only runtime-specific dispatch instructions.
`tests/test_normative_single_source.py` prevents the four normative sections
from being copied back into either entry document. Skills live once under
`.agents/skills/` (`.claude/skills` is a symlink to it).

## Layout

```
FL-Prover/
├── CLAUDE.md / AGENTS.md      # Orchestrator instructions (Claude / Codex)
├── settings.py                # Config (loads .env): DATA_DIR, KB_MANAGER_DIR, keys
├── cli_tools/                 # Deterministic tool exoskeleton
│   ├── lean.py / _lean/           # check, scan, axioms, guard, index, search, verdict
│   ├── control.py / _control/     # task ledger + wave summary
│   ├── dag.py / _dag/             # typed obligation graph + status rendering
│   ├── memory.py / _memory/       # three-tier continual memory
│   ├── search.py / _search/       # arxiv, matlas, frontier, citation-graph
│   ├── external.py / _external/   # Gemini / GPT / discuss / golf / informal
│   ├── gate.py / _gate/           # mechanical accept / stop gates
│   ├── workspace.py / _workspace/ # references, presentation, provenance ledger
│   └── _common/                   # shared internals (paths, indexing, openrouter)
├── scripts/                   # run_claude.py (CLI), runner.py (session loop)
├── prompts/                   # normative SSOT + orchestration/role prompts + references/
├── tests/                     # harness unit tests
├── tex/                       # LaTeX templates
├── .claude/ .codex/ .agents/skills/   # dual-harness registrations, hooks, shared skills
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
the typed `dag.json` obligation graph and rendered `STATUS.md`, the task
ledger under `.claude/state/`, and the local memory tier. The DAG records the
candidate commit, build-verdict log, `sorry` count, dependencies, and blind
read-back used to justify each proved node. Layout and artifact ownership:
`prompts/references/workspace-and-ownership.md`.
