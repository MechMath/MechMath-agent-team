# MechMath Agent Team Project Template

This repository provides a reusable research-project template for the
**MechMath Agent Team (MMAT)**, an LLM-based mathematical research agent
developed within the [MechMath](https://mechmath.github.io/) initiative of the
Key Laboratory of Mathematics Mechanization, AMSS, Chinese Academy of Sciences.
The scientific motivation, system overview, and research record of MMAT are
presented on the official
[MechMath Agent Team page](https://mechmath.github.io/agent-team/).

MMAT is designed to support the full mathematical research workflow. Its
general harness coordinates specialized agents and deterministic tools for
literature retrieval, conjectural exploration, proof construction, independent
verification, formalization, symbolic computation, human feedback, and the
preservation of reusable mathematical artifacts. This template integrates the
three principal MMAT agents in a single project:

- **NL-Prover**, the natural-language prover;
- **FL-Prover**, the formal-language prover; and
- **KB-Manager**, the persistent mathematical knowledge manager.

The agents exchange problems, references, proof artifacts, formal
developments, and accumulated research knowledge through a shared `data/`
directory. 

## System Components

| Directory | Research function | Interactive harness |
|---|---|---|
| `nl-prover/` | Decomposes mathematical problems, explores proof routes, generates natural-language arguments, searches for counterexamples, and coordinates independent review. | Codex or Claude Code |
| `fl-prover/` | Formalizes mathematical statements in Lean 4, constructs formal proofs, and applies deterministic compilation, axiom, placeholder, and statement-integrity gates. | Codex or Claude Code |
| `kb-manager/` | Registers and ingests sources, maintains a persistent mathematical wiki, answers knowledge-base queries, and archives formal artifacts. | Codex |
| `data/` | Stores shared runtime data and provides the handoff boundary among the three agents. | Exported as `DATA_DIR` |

NL-Prover and FL-Prover provide two harness implementations over the same
specialist prompts, deterministic command-line tools, and shared skills:

- a **Codex harness**, defined by `AGENTS.md` and `.codex/agents/`; and
- a **Claude Code harness**, defined by `CLAUDE.md` and `.claude/agents/`.

Their scientific workflow is common; only the agent registration and dispatch
mechanism differs. Component-level architecture and operational details are
documented in:

- [`nl-prover/README.md`](nl-prover/README.md);
- [`fl-prover/README.md`](fl-prover/README.md); and
- [`kb-manager/README.md`](kb-manager/README.md).

## Relationship to MechMath

[MechMath](https://mechmath.github.io/) is a research initiative that brings
together mathematicians, computer algebra, formal verification, and artificial
intelligence to construct systems for mathematical research and rigorous new
results. MMAT is its agent-based research environment: a general harness
specialized into coordinated natural-language proving, formal-language proving,
and knowledge-management agents.

This repository is the project-facing layer of that environment. It packages
the three agents with a shared data model and reproducible launch procedure so
that a mathematical investigation can be maintained as an independent,
long-lived project. For a concise account of the MMAT architecture and its
research applications, see the
[official Agent Team overview](https://mechmath.github.io/agent-team/).

## Requirements

The root uv workspace and the current `uv.lock` target Python 3.14. NL-Prover
and FL-Prover are individually compatible with Python 3.12 or later, but
Python 3.14 should be used when installing the integrated workspace from the
repository root.

Required software:

- Git;
- [uv](https://docs.astral.sh/uv/); and
- the Codex CLI.

Optional software and credentials:

- Claude Code, for the Claude harnesses of NL-Prover and FL-Prover;
- `elan`, `lake`, and a compatible Lean 4 toolchain, for FL-Prover;
- `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or
  `OPENAI_API_KEY`, according to the selected external verification backends;
  and
- `LEANDEX_API_KEY`, when the Leandex search backend is used.

API keys may be supplied through the shell environment. Alternatively, copy
and edit the relevant component examples:

```bash
cp nl-prover/.env.example nl-prover/.env
cp fl-prover/.env.example fl-prover/.env
```

Local `.env` files are excluded from version control. The launcher exports the
shared data path automatically, so `DATA_DIR` need not be duplicated in these
files.

## Creating an Independent Research Project

The repository is intended to be copied or cloned as a template. A research
project created from it should acquire its own Git history rather than append
project-specific work to the template history:

```bash
git clone <template-repository-url> my-math-project
cd my-math-project
./init.sh
uv sync --all-packages
```

The initialization script requests the explicit confirmation token `INIT` and
then:

1. optionally renames the project directory;
2. derives the root `pyproject.toml` project name from the directory name;
3. permanently removes the template repository's root Git metadata and history,
   without creating a backup;
4. initializes a new repository on the `main` branch;
5. creates any missing shared-data directories;
6. writes `.mmat-initialized` to prevent accidental repeated detachment; and
7. stages the initial project files without committing, adding a remote, or
   pushing.

The three agent directories are ordinary directories in the new repository;
they are not Git submodules. After initialization, inspect the staged tree and
create the first project commit:

```bash
git status
git commit -m "Initial project"
git remote add origin <your-repository-url>
git push -u origin main
```

> Do not run `init.sh` when maintaining the MMAT template repository itself.
> Its removal of the existing root Git history is deliberate and irreversible.

The same script can initialize a project obtained from a ZIP archive or an
ordinary filesystem copy that does not contain a `.git` directory.

## Dependency Installation

The root `pyproject.toml` defines `kb-manager`, `nl-prover`, and `fl-prover` as
members of one uv workspace:

```bash
uv sync --all-packages
```

The `--all-packages` flag installs the dependencies of every workspace member,
not only those of the dependency-free virtual root project. If `init.sh`
changes the root project name, this command also refreshes the corresponding
workspace metadata in `uv.lock`. Repository tools should be invoked through uv,
for example:

```bash
uv run python nl-prover/cli_tools/gate.py --help
```

FL-Prover additionally requires a functioning Lean installation:

```bash
elan --version
lake --version
```

If elan is installed outside its conventional `~/.elan` location, set
`LEAN_ELAN_HOME` in `fl-prover/.env`.

## Launching an Agent Session

Run the unified launcher from the project root:

```bash
./start.sh
```

It presents the following sessions:

1. KB-Manager via Codex;
2. NL-Prover via Codex;
3. FL-Prover via Codex;
4. NL-Prover via Claude Code;
5. FL-Prover via Claude Code; and
6. contextual help.

When option 4 is selected, the launcher asks for a problem ID and exports the
corresponding `NLPROVER_WORKSPACE`. This is required by NL-Prover's Claude hooks
to attribute dispatch records to the correct problem. If the variable is already
set, it must name an existing directory under `data/workspace/`.

Additional arguments are forwarded unchanged to the selected CLI. For example,
to enable web search in a Codex session:

```bash
./start.sh --search
```

The launcher enforces component-specific write boundaries:

- KB-Manager receives write access to the complete `data/` tree because it owns
  the wiki, source archive, source manifest, download queue, and formal archive.
- NL-Prover and FL-Prover receive additional write access only to
  `data/workspace/` and `data/inbox/`. They may read the remaining shared
  knowledge, but should not modify it without explicit authorization.

Exit the active CLI and run `./start.sh` again to switch agents.

### Manual Codex Launch

The unified launcher is recommended. An equivalent manual NL-Prover launch is:

```bash
export DATA_DIR="$(cd data && pwd)"

codex -C nl-prover \
  --add-dir "$DATA_DIR/workspace" \
  --add-dir "$DATA_DIR/inbox"
```

Replace `nl-prover` with `fl-prover` to launch FL-Prover. KB-Manager requires
access to the complete shared-data tree:

```bash
codex -C kb-manager --add-dir "$DATA_DIR"
```

For a manual NL-Prover Claude Code launch, create and export the active problem
workspace before starting from the component directory:

```bash
problem_id=my-problem
mkdir -p "$DATA_DIR/workspace/$problem_id"
export NLPROVER_WORKSPACE="$DATA_DIR/workspace/$problem_id"
cd nl-prover
claude --add-dir "$DATA_DIR/workspace" --add-dir "$DATA_DIR/inbox"
```

Launching from `nl-prover/` is significant: that is where Claude Code loads the
project allowlist and the dispatch/nesting hooks. FL-Prover's Claude session has
the same launch-directory requirement, but does not require
`NLPROVER_WORKSPACE`.

## Shared Research Data

```text
data/
├── inbox/                 # Human deposits and prover-to-KB-Manager handoffs
├── raw_sources/           # Immutable, content-addressed source materials
├── workspace/             # Per-problem NL/FL master and scratch workspaces
├── lean/                  # Curated Lean 4 proof archive
├── wiki/                  # Persistent Markdown mathematical knowledge base
│   ├── index.md           # Global navigation index
│   └── log.md             # Append-only operation log
├── sources_manifest.md    # Source registration and ingestion status
├── download_queue.md      # Sources awaiting manual acquisition
└── logs/                  # Project-level runtime logs
```

Registered material under `raw_sources/` is treated as immutable. Researchers
may edit pages under `wiki/` directly; KB-Manager treats such human revisions as
authoritative in subsequent operations. Detailed ownership and mutation rules
are specified by each component's `AGENTS.md`.

## Representative Workflows

### Literature and Knowledge Management

Launch KB-Manager to register a public source, a local file deposited in
`data/inbox/`, or a resource requiring manual acquisition:

```text
$source-management https://arxiv.org/abs/2301.12345
$source-management paper.pdf
$source-management queue "Author et al., DOI:10.xxxx/xxxxx"
```

After registration, use the ingestion workflow proposed by the session to
compile the source into reusable mathematical cards under `data/wiki/`.
Knowledge retrieval and maintenance are available through:

```text
$query <research question>
$wiki-maintenance lint
```

### Natural-Language Theorem Proving

Launch NL-Prover and provide the mathematical problem, available references,
and desired form of the result. Each investigation is maintained under
`data/workspace/<problem_id>/`. The Orchestrator routes work among specialist
agents for literature search, lemma decomposition, route exploration, proof
generation, independent verification, counterexample search, human review, and
final exposition.

The workflow is designed as a generation--verification--revision loop. Failed
routes and transferable constraints are retained as research memory rather than
discarded as transient conversation state.

The current harness also separates discovery output from certification: only a
single fresh Verifier packet can give a proof artifact mathematical weight.
Mechanical gates now report dependency-DAG health, dispatch cost, contract drift,
discovery bookkeeping, and the required human-facing progress summary. Every
stop writes memory back and leaves either the verified result or both
`progress_notes.pdf` and the shorter `progress_summary.pdf`.

### Lean 4 Formalization

Launch FL-Prover with a mathematical statement, its source, and the target Lean
project or file. Formal artifacts enter the master development only after the
relevant deterministic gates have passed:

1. the target compiles in Lean;
2. no `sorry` or `admit` remains;
3. the proof introduces no axiom outside the accepted base; and
4. the protected theorem statement is unchanged.

Because compilation establishes correctness only relative to the encoded Lean
statement, a Formal Reviewer evaluates semantic fidelity against the source. A
separate blind `statement-readback` agent receives only the Lean declaration and
its referenced definitions, then spells out its literal quantifiers, bounds,
pointwise/aggregate meaning, and possible vacuity before the node is accepted as
proved. FL-Prover's typed DAG records dependencies, candidates, build verdicts,
`sorry` counts, and these read-backs; `lean.py verdict` distinguishes traceable
build outcomes from missing or incomplete logs.

### Long-Term Knowledge Transfer

Verified arguments, partial proofs, formal declarations, failed approaches, and
identified obstructions may be handed to KB-Manager through `data/inbox/`.
KB-Manager compiles these outputs into an indexed mathematical card graph, so
that later investigations can retrieve both established results and previously
discovered constraints.

## Update Log

### 2026-09-11 — FL-Prover and NL-Prover refresh

- FL-Prover now keeps shared normative rules in `prompts/normative.md`, adds a
  blind statement-readback role, a typed proof-obligation DAG, and auditable
  build verdicts. Its facade tests now check imports, exit-code propagation,
  Lean inspection behavior, suite shape, and the normative single source.
- NL-Prover adds explicit discovery/certification modes, producer-side cold
  verification dispatch, contract/discovery/DAG/speed/summary gates, typed
  workspace status, compute-budget and proof-audit skills, and mandatory compact
  progress summaries at non-proof stops.
- Claude Code dispatch logging and nesting enforcement are now wired through
  component-local hooks. NL-Prover Claude sessions must start from
  `nl-prover/` with `NLPROVER_WORKSPACE` set; the unified launcher handles this
  by asking for the active problem ID.
- Template cleanup removes generated logs, obsolete directory placeholders,
  and prover scratch artifacts from version control. FL-Prover's standalone
  runner scripts again accept caller-supplied targets and options through `uv`.

After pulling this update, run `uv sync --all-packages`. Existing NL-Prover
workspaces should be checked with `workspace.py status` and the new structural
gates before resuming; existing FL-Prover ledgers can be audited with
`dag.py import --from <proof_tasks.json>` (the import command reports issues and
does not migrate or modify the ledger).

## Scientific Context

MMAT is intended as an assistant to, rather than a replacement for, the
mathematician. Human researchers remain responsible for selecting significant
questions, supplying domain insight, evaluating informal arguments, assessing
semantic fidelity, and determining the mathematical value of a result. The
agent architecture provides structured exploration, explicit verification
mechanisms, reproducible artifacts, and continuity across long-running
projects.

For the broader research programme, systems, publications, and case studies,
consult:

- [MechMath](https://mechmath.github.io/);
- [MechMath Agent Team](https://mechmath.github.io/agent-team/); and
- the component documentation linked above.
