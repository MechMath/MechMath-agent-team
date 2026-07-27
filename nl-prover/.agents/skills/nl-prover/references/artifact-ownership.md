# Artifact Ownership

The Orchestrator owns routing state and verified merge assembly. Mathematical
content belongs to specialist agents.

**The full artifact-ownership table is the SSOT in
[`prompts/references/workspace-and-ownership.md`](../../../../prompts/references/workspace-and-ownership.md)**
(complete directory + owner, including the ADR 0018 `knowledge/*` and ADR 0019
`references/ledger.jsonl` / `references/refs.bib` rows). Do not maintain a second
copy here — consult that file for any per-artifact owner. The principle below is
the only content this file owns.

## Rule

If an artifact changes mathematical content, theorem support, definition
reading, computation evidence, route logic, proof text, or verification
judgment, it needs a specialist owner and later verification when adopted.

The Orchestrator may run mechanical tools and update routing files, but it must
not create surrogate proof, verifier, theorem, definition, computation, or
reader-facing writing artifacts.
