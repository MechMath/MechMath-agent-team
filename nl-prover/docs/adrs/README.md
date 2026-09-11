# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for NL-Prover. Each ADR documents a significant design decision, its context, rationale, and consequences.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-multi-agent-orchestration-architecture.md) | Multi-Agent Orchestration Architecture | Accepted |
| [0002](0002-file-based-inter-agent-communication.md) | File-Based Inter-Agent Communication | Accepted |
| [0003](0003-ephemeral-verifiers-against-anchoring-bias.md) | Ephemeral Verifiers to Prevent Anchoring Bias | Accepted |
| [0004](0004-sketcher-suspend-resume-and-re-decomposition.md) | Sketcher Suspend/Resume and Re-Decomposition Protocol | Accepted |
| [0005](0005-proof-rigor-standards-and-verification-criteria.md) | Proof Rigor Standards and Verification Criteria | Accepted |
| [0006](0006-external-llm-cross-verification.md) | External LLM Cross-Verification via Gemini and GPT | Accepted |
| [0007](0007-arxiv-search-and-research-integration.md) | arXiv Search and Research Integration | Accepted |
| [0008](0008-proof-tex-as-single-source-of-truth.md) | proof.tex as Single Source of Truth | Accepted |
| [0009](0009-rule-governed-autonomous-orchestration.md) | Rule-Governed Autonomous Orchestration | Proposed |
| [0010](0010-orchestrator-prompt-skill-cookbook-layering.md) | Orchestrator Prompt, Skill, and Cookbook Layering | Proposed |
| [0011](0011-article-writing-skill.md) | Article-Writing Skill and Writer Agent | Proposed — progress-note parts superseded by 0021/0025 |
| [0012](0012-rethlas-inspired-memory-verification-and-presentation.md) | Rethlas-Inspired Tooling, PDF Pre-Extraction, and AI-Readable Indexes | Proposed |
| [0013](0013-follow-up-upgrade-backlog.md) | 后续升级议题备忘 | Proposed |
| [0014](0014-tighten-source-scout-verification-writer-and-harness.md) | Tighten Source Scout, Verifier, Writer, and Harness | Accepted — §5 `PROGRESS_NOTE` superseded by 0021/0025 |
| [0015](0015-scholar-internalization-and-experience-card-library.md) | Scholar 内化阶段与经验卡片库（已向 0016 对齐，蒸馏部分搁置） | Superseded |
| [0016](0016-stratified-continual-memory-system.md) | Stratified Continual Memory System (paper §2.3.2) | Accepted |
| [0017](0017-unify-continual-memory-into-collector-kb.md) | Long-Term Memory Cards in the Collector KB — Card Family and Schema | Accepted |
| [0018](0018-searcher-internalization-kb-collaboration-and-deep-search.md) | Searcher — Source Internalization, KB-Manager Collaboration, and Deep Search | Accepted |
| [0019](0019-external-result-trust-provenance-citation-and-source-audit.md) | External-Result Trust — Provenance, Citation Integrity, and Source Audit | Accepted |
| [0020](0020-harness-info-architecture-ssot-and-index-adoption.md) | Harness Information-Architecture Governance — SSOT Deduplication and Index Adoption | Accepted |
| [0021](0021-mandatory-progress-notes-and-output-naming.md) | Mandatory Progress Notes at Every Stop, and Plain Output Names | Accepted — amended by 0025 |
| [0022](0022-memory-write-back-at-every-stop.md) | Memory Write-Back at Every Stop | Accepted |
| [0023](0023-discovery-and-certification-separation.md) | 发现区与验收区的分离 | Accepted |
| [0024](0024-dispatch-economics-and-concurrency.md) | 调度经济学：并发、重读预算与重试消除 | Partially Accepted — §4.2 and §3.H3 overtaken by code, see §0bis |
| [0025](0025-progress-summary-the-second-stop-document.md) | A Stop Owes Two Documents: the Progress Summary | Accepted |

## ADR Format

Each ADR follows the standard format:
- **Status**: Proposed / Accepted / Deprecated / Superseded
- **Amendments**: an ADR's body is never rewritten to match later code. A
  correction is a dated blockquote under `## Status` (or under the header
  metadata block) naming what it amends, or a new ADR that the amended one
  points to. The Status column above carries the pointer.
- **Context**: What problem are we solving? What prior art informs the decision?
- **Decision**: What did we decide and how does it work?
- **Consequences**: Pros, cons, trade-offs, and mitigations
