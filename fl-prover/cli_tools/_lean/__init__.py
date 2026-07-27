"""Lean toolchain internals behind the `lean.py` facade.

Not model-facing. The paper's five formal tool categories (Table 2b) map onto
this package:

- check.py        Checking  — compile via `lake env lean`
- scan.py         Scanning  — real `sorry`/`admit` outside comments and strings
- axioms.py       Scanning  — `#print axioms` audit of the final axiom set
- guard.py        Guarding  — snapshot/verify protected statements
- fileinfo.py     Indexing  — declarations, imports, outline (over sourcetools.py)
- leansearch.py, leanfinder.py, leandex.py, loogle.py, state_search.py,
  hammer_premise.py   Searching — premise retrieval backends
"""
