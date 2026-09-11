# Verification Gates

Every Verifier check must produce a compact review packet in addition to full
report and verdict. The packet is the Orchestrator's merge or retry artifact.

Before using a passing packet for merge, plan adoption, refined-proof adoption,
or obstruction acceptance, run:

```bash
uv run python cli_tools/gate.py review-packet <review_packet.md> --mode auto
```

Verifier checks write:

```text
report_v<N>.md
review_packet_v<N>.md
verdict.md
```

There is no structural pre-check packet or `PROCEED_TO_DETAILED` action.

Completion gate:

```bash
uv run python cli_tools/gate.py complete <problem_workspace>
```

For refined proof or obstruction packets:

```bash
uv run python cli_tools/gate.py complete <problem_workspace> --packet <review_packet.md>
```

Narrow result-contract check:

```bash
uv run python cli_tools/gate.py result-contract <problem_workspace> --packet <review_packet.md>
```

## The Rest of `gate.py`

`prompts/orchestration.md` names this file as the place the gate commands live
and says "Do not re-document the commands here", so a subcommand missing from
this page has a runnable form nowhere: a model that needs one has to invent it
from a bare backticked token. That is how `gate contracts` — which `AGENTS.md`,
`CLAUDE.md` and `orchestration.md` all tell you to run after any change that adds
a tool, a gate, or a skill — went the whole of its life without an invocation
anywhere in the repo. So this section completes the index rather than scoping the
page down to the packet gates: the SSOT claim is the one that was already made,
and honouring it costs less than contradicting it.

```bash
# a run may stop: memory written back, export present
uv run python cli_tools/gate.py stop <problem_workspace>
uv run python cli_tools/gate.py stop <problem_workspace> --verified-proof
# a Generator proof attempt is shaped for review
uv run python cli_tools/gate.py proof-attempt <proof_v1.md> --status <generator/status.md>
uv run python cli_tools/gate.py proof-attempt <proof_v1.md> --ledger <problem_workspace>
# a proof-review routing artifact carries one valid decision
uv run python cli_tools/gate.py proof-review <proof_review.md>
# final-article citation audit (ADR 0019 §5)
uv run python cli_tools/gate.py citation-audit <problem_workspace> --tex <article.tex>
# discovery-region schema lint (ADR 0023)
uv run python cli_tools/gate.py discovery <problem_workspace>
# the lemma dependency graph, read back
uv run python cli_tools/gate.py dag <problem_workspace>
# what the round cost
uv run python cli_tools/gate.py speed <problem_workspace>
# the stop document a person reads
uv run python cli_tools/gate.py summary <problem_workspace>
# what this repo says about itself, against the code that implements it
uv run python cli_tools/gate.py contracts
```

`dag` and `speed` are advisory and exit 0 unless you pass `--strict`; run `dag`
whenever the branch queue changes and `speed` at least once a run. They are worth
nothing unless somebody reads them. Every subcommand takes `--json` and
`--waive REASON`; the waiver records the violations and lets the run continue,
and the waiver log is what tells us which checks to delete. Use it when a check
has misfired, never by editing the artifact until the check stops firing.

### `contracts`

```bash
uv run python cli_tools/gate.py contracts
uv run python cli_tools/gate.py contracts --repo <harness-root> --json
```

The workspace argument is accepted and ignored, so this gate is invoked like the
others; the thing it audits is the repository, not a run. It reads ground truth
out of the code and checks the prose against it — never one prose file against
another, because a drift report that names only the wrong copy sends someone to
fix the file that was already right half the time, so every finding names both
ends.

What it reads as ground truth: the facade list (`cli_tools/*.py`), the gate
subcommand list (`gate.py DISPATCH` — this section), the skill roster
(`.agents/skills/*/`), the concurrency ceiling (`_gate/speed.py
DECLARED_CONCURRENCY`, against `.codex/config.toml` and the cookbook), and the
long-term-read form (`memory.py` stamps its trace only when a workspace is
passed, so a documented invocation without one is an error). It also checks that
`memory.md` renders the cards actually in `memory/experience/`, that the four
sections `AGENTS.md` and `CLAUDE.md` promise to keep identical still say the same
thing, that what `CLAUDE.md` claims about its hooks matches `.claude/settings.json`,
and that invariant 2 still has its enforcement point on each platform.

Three duplicated facts are deliberately **not** in it — the pre-stop step
sequence, who may set `blocked`, the Codex allowlist. Nothing executable defines
them, and a lint that guesses a machine-readable shape is worse than a document
that rots.

Run it after any change that adds a tool, a gate, or a skill — including a change
to this file, which is one of the prose files it reads.

Lints and completion gates are deterministic shape checks, not mathematical
verifiers. If they fail, route to the smallest owner.
