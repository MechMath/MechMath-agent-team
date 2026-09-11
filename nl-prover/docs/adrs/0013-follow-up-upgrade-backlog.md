# ADR 0013: 后续升级议题备忘

## 状态

Proposed，备忘稿。

## 背景

ADR 0012 只讨论 Rethlas 启发的工具层、PDF 预提取和 AI 可读索引。下面这些议题
相关但不应该塞进同一个 ADR，先单独记录，防止后续讨论时遗漏。

## 待开 ADR

1. Search 升级：比较 Rethlas、QED 和现有 `queries/` 体系，重新设计 arXiv /
   Matlas / Collector 的请求、缓存、重试、摘要和索引写入。
2. 去掉 structural verifier：重新设计 verification gate，判断是否保留两层
   verification，或改成单层 Verifier 加更强 review packet。
3. AhhProver 设计调研：阅读 `/data/caosip/github/EonMath/AhhProver` 或远程仓库，
   看它的 agent、工具、状态管理和 proof workflow 有哪些可借鉴点。
4. Writer 升级：继续改进 well-written proof / progress note 的文章质量、模板、
   export 规则和与 presentation index 的关系。
5. Subagent 工具集成规范：在 search / memory / branch state 工具落地时，同步更新
   skill、prompt 和 agent cookbook，明确哪个 subagent 在什么时机使用哪些工具。

## 当前处理

本 ADR 只作为 backlog，不直接决定实现。每个议题进入设计时再拆成独立 ADR。
