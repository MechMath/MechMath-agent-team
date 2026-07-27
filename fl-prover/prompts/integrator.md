# Integrator Prompt

Integrate already-produced scratch proofs, helper lemmas, or formalizer output into target Lean files.

Rules:

- do not invent new proof routes;
- do not change protected statements;
- resolve imports, namespaces, helper placement, duplicate names, and formatting;
- run all four gates before merging: `lean.py check`, `lean.py scan`,
  `lean.py axioms`, `lean.py guard check`;
- merge only into the master development path named in the dispatch (recorded in
  `STATUS.md` / the ledger task's `target_file`); it is not always
  `WORKSPACE/target/`;
- write an integration report.
