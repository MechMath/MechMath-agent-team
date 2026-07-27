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

Lints and completion gates are deterministic shape checks, not mathematical
verifiers. If they fail, route to the smallest owner.
