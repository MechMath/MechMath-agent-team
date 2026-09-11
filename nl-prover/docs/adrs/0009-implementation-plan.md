# ADR 0009 Implementation Plan

Status: first experimental pass implemented on branch `experimental`.

## Scope

Implement the first experimental pass of rule-governed autonomous orchestration.
This pass changes prompts, custom-agent declarations, and structural lint
support. It does not rewrite the legacy Python orchestrator into an end-to-end
runtime.

## Ordered Work

1. [x] Add custom agent declarations for:
   - `regulator`
   - `explorer`
   - `synthesizer`
   - `ce-hunter`
   - `searcher`
   - `auditor`
   - `code-executor`
2. [x] Add matching prompt files under `prompts/`.
3. [x] Update `prompts/verifier.md` to support structural and detailed modes and
   structural packet outputs.
4. [x] Update `cli_tools/review_packet_lint.py` with `structural`
   mode and `PROCEED_TO_DETAILED` routing.
5. [x] Update `prompts/orchestration.md` with rule-governed routing, route history,
   structural/detailed verification files, and new file ownership.
6. [x] Update existing agent prompts/configs only where needed to preserve role
   boundaries.
7. [x] Review diffs for consistency and avoid unrelated code changes.

## Non-Goals

- No UI work.
- No per-agent model configuration.
- No token dashboard.
- No Python-driven full orchestration rewrite.
- No test run unless explicitly requested.

## Acceptance Checks

- New agent configs point to existing prompt files.
- Every new prompt has input, output, ownership, and forbidden-action sections.
- Structural verification packet format reuses review-packet section names.
- `review_packet_lint.py --mode structural` accepts structural next actions and
  does not require merge-only external cross-verification.
- `prompts/orchestration.md` no longer treats the fixed pipeline as the only
  route.
