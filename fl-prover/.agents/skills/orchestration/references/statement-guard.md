# Statement Guard

The guard freezes an approved statement's text and re-checks it later, so a proof
that only compiles because the statement moved is caught instead of celebrated.

```bash
uv run python cli_tools/lean.py guard snapshot --workspace WORKSPACE --task TASK_ID
uv run python cli_tools/lean.py guard check    --workspace WORKSPACE --task TASK_ID
uv run python cli_tools/lean.py guard diff     --workspace WORKSPACE --task TASK_ID
```

`snapshot` writes `.claude/state/statements/<task>.v<N>.statement.lean`; `check`
compares the current text's hash against it (exit 1 on mismatch); `diff` shows
what moved. The task's `target_file` + `declaration` fields decide what is
guarded — a namespace-qualified declaration name is accepted.

## When

- **Snapshot** right after the F-Reviewer returns `VERDICT: APPROVE`, before any
  F-Generator is dispatched.
- **Check** as one of the four merge gates, and again before declaring the target
  done.

## Changing a Protected Statement

Proof work must never change a protected statement. The only legal route:

1. **F-Reviewer** files a rejection in `reviews/statement_<task>.md` naming what
   is unfaithful to the source (book, paper, or user statement).
2. **Formalizer** revises the declaration in its own scratchpad.
3. **F-Reviewer** approves the revision.
4. **Orchestrator** re-snapshots, citing that review:

   ```bash
   uv run python cli_tools/lean.py guard approve-change \
     --workspace WORKSPACE --task TASK_ID --review reviews/statement_<task>.md
   ```

No step may be skipped, and no other role may start the sequence. An
F-Generator that finds the statement unprovable reports that as a blocker with
the reason; it does not edit the statement and it does not ask the guard to be
reset.
