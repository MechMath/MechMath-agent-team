# ADR 0023 — 发现区与验收区的分离

- **状态**：**Accepted**（第五轮人类审阅批准实施）。
  依赖 ADR 0024 的条款暂缓，见 §7.0。
- **取代**：本 ADR 的早期草稿《候选发现阶段（Discovery Triage）与全局重置》。
  该草稿的两条前提被取证证伪（见 §1.3），Discovery Triage 在本版中降级为次要条款。
- **证据**：`docs/harness-cross-workspace-forensics.md`（9 个 workspace，约 600 MB 产物，
  逐字引用与 md5/sha256 核验）；`docs/harness-speed-forensics.md` §10–§13
- **扩展**：ADR 0009、ADR 0010、ADR 0016、ADR 0017、ADR 0020、ADR 0022
- **不改变**：ADR 0002（文件通信）、ADR 0003（无状态 Verifier）、ADR 0005（证明严格性标准）、
  ADR 0008（`proof.tex` 单一真源）。**本 ADR 不降低任何证明标准，一个字都不降。**
- **修订**：前四轮共 84 条批注已按结论融入正文，讨论过程不再保留；
  第五轮新增 4 条批注，以问答形式就地保留，见 §0。

---

## 0. 本轮未决批注索引（第五轮）

以 **「批注 N**xx**」/「回答 N**xx**」** 就地标注，可直接检索。

| # | 位置 | 你的要点 | 处置 |
|---|---|---|---|
| N35 | §3.A.2 | 可以简单过一下疑点，不然可能导致多轮 | **你对，我把限制加错了维度**——贵的是深度不是覆盖 |
| N36 | §3.A.2 | 可以修的话可以回去修发现 | **采纳，补第三条出路**；与 N35 合起来把 N 轮压回一轮 |
| N37 | §3.G.2 | 不要墙钟超时，可能限制能力 | **照办**；并记下这条取舍放弃与保住了什么 |
| N38 | §3.G.3 | 通法 skill 先搁置 | **照办**，从实现清单移除；已查清的三件事留档 |

---

## 1. Context

### 1.1 问题陈述

同一批题目上，一次普通的网页会话反复做出本地 harness 做不出的结果，
而本地 harness 的严谨性明显更高。**目标是两者都要**，不是二选一。

### 1.2 取证的核心事实

**广度不是问题。** 本地探索广度远超网页：3_1 有 88 轮 brainstorm 对网页的 1 轮；
2_5 有 317 条 route、224 条队列行。

**问题是正确路径被杀了，而且是被杀了很多次、用了十种不同的方式。**

四个 workspace 都属于「发现了正确路径又被杀」：

| workspace | 正确路径在哪 | 被杀时的位置 | 之后还跑了 |
|---|---|---|---|
| 2_2_old | Rivoal 精确三元组，与获胜证明完全相同 | rank 79 / 172 | 93 个 rank |
| 2_5 | 初始矩阵的核 `(4,7,13)`；以及人类交出的完整 PSLQ 配方 | 最早几份 brainstorm 之一 | 全程 |
| 3_1 | `brainstorm_26` = 获胜策略本身，含缺口的精确规格 | brainstorm 26 / 89 | 63 轮 |
| 2_7 | ₃F₂ 载体；以及从 p08 迁移来的 ₄F₃（参数完全相同） | 外部投稿到达前 13 小时 | 直至投稿到达 |

（3_2 不属于此类：它把预算花在了自己已证明为平凡的因子上，
而该题网页也未解出，谈不上"正确路径"。）

**正面对照**：2_2 的成功直接来自刻意丢弃上一次运行积累的封闭结论——
`"non-authoritative … only after fresh route formation"`、
`"Deliberately deferred reading mathematical conclusions from 2_2_old"`。
结果：1 轮 brainstorm、1 次计算审计、5 条 lemma 全 PASS、
**`recovery/` 是空目录，Regulator 决策 0 次**。

> **说明**：本 ADR 不使用墙钟时间作为任何指标——workspace 未必由同一人运行。
> 全部量化依据为分支队列名次、产物序号、文件计数、哈希比对。

### 1.3 对早期草稿的两条修正

**修正一：锚定不长在记忆系统。**
早期草稿提议把经验卡片的 `scope` 机械化。但 `memory.md` 受 git 管理，
在 2_5 的整个发现窗口内内容为 7 行的 `_(no long-term negative-constraint cards yet)_`，
SHA-256 与那次唯一 PSLQ 审计报告 Inputs Read 表中记录的哈希**逐字节相同**——
跑那次 PSLQ 的 agent 读到的是空文件。`2_2` 与 `2_2_old` 合计产出经验卡片 0 张。
**该条撤销：修的是没病的器官。**

**修正二：Discovery Triage 不是最高杠杆。**
复盘称「没有尽早检查初始矩阵的秩与核」——事实错误。
`2_5/routes/brainstorm_full_seed_construction_1.md:147-153` 在很早就逐字写出
`A_P × A_Q = −27000(4,7,13)`、`rank A = 2`、`κ_A = (4,7,13)ᵀ`，
且 agent 自标「比单个比值 206/225 严格更强的数据」。
harness 已经做了 triage 的工作并把结果扔掉了。
**一个只会产出被立刻冻结的事实的新阶段，只会更快到达同一个死胡同。**

**由此得到全文的第一条归纳**：K1、K3、K6 的共同形状是
**在一个被随手收紧的宇宙里得到空结果，然后把空结果记成对整个族的否定**。
三次都不是「假设错了」，而是**假设的作用域被丢掉了**——
记录里只剩结论，没剩「这个结论是在什么盒子里成立的」。

### 1.4 一条不能弄丢的资产

3_1 的验证战役证明本地审稿能力极强：三条独立 Verifier 通道跑不相交章节，
两条返回 FAIL，抓出导入证明中 carrier junction 的真实逻辑断裂、(7.1) 无来源、
缺 a-priori 界、三个虚报 PASS token，并从 arXiv LaTeX 源码（`9712224.tex`，附 md5）
查出 Neumann–Yang Def 2.1 关系 (2) 的**原始来源印刷错误**。
Refiner 自述 52 页中约 10 页是「诚实性装置」。

**本 ADR 的任何条款都不得触碰这一部分。**

---

## 2. 击杀机制分类（决议的依据）

十种机制，长在不同的器官上。**逐一对应到下面的决议。**

| # | 机制 | 器官 | 证据 | 决议 |
|---|---|---|---|---|
| K1 | 冻结宇宙里的约定错误 → 弹出且永不重访 | `regulator.md` 的封闭语义 | 2_2_old rank 79 | **B**, C |
| K2 | 结构事实 / 可迁移机制被误路由为出处问题 | `regulator.md` 失败分类表 | 2_5 核；2_7 ₄F₃ | **F** |
| K3 | 一次性契约 + 预先封死补救 | `regulator.md` `Do Not Retry` | 2_5 PSLQ | **C** |
| K4 | `first_missing` 中止 | brainstorm 协议 / Decision 契约 | 3_1 `brainstorm_26` | **D** |
| K5 | 有限歧义升级给人类 | `proof-review` 工作流 | 2_5 系数排列 | **J** |
| K6 | 有限宇宙前置条件失败 → 不得执行 | Code Executor 派单契约 | 2_7 ₃F₂ | **C**, G |
| K7 | 同侪迁移被降级为"先例" | Searcher / 来源审计标准 | 2_7 ₄F₃ from p08 | **H** |
| K8 | 记录只用于排除，不用于回归（**放大器**） | route history 的全部消费者 | 全仓库 | **B**, I |
| K9 | 排序规则没有产出维度，不确定下的不动点是"永远审计" | `prompts/synthesizer.md` 评估维度表 | Q6 六次连续 synthesis | **K** |
| K10 | 危险率塌陷：连续派发全部被下一个决策杀掉，只有机制族的名字在换 | Regulator 的族级失明 | 3_1 决策 16–30 | **E**（+ ADR 0024 D-bis/F） |

**K8 是使 K1–K7 变成永久的那一条。** 单独看，K1–K7 每一种只是一次挫折。

### 2.1 K9 — 排序规则的不动点是"永远审计"

**先记一个负面结果**：Synthesizer 的排序在可解的题上**完全正常**——
IMO 的 Q1–Q5，**5/5 的 rank-1 分支就是最终完成证明的那一条**，
零次机制更换，排队的备选从未被启用。「排序选错路线」这个方向可以排除。

**但 Q6 暴露了规则本身的缺陷。** 八次 synthesis 的 rank-1 owner：

| synthesis | rank-1 owner | 能产出证明吗 |
|---|---|---|
| 1 | Sketcher | ✅ |
| 2–6 | **CounterexampleHunter** ×5 | ❌ |
| 7 | **Regulator**（原文 *"ACTIVE PROCESS HANDOFF. This is not a mathematical branch."*） | ❌ |
| 8 | Sketcher | ✅ ← 完成证明的那一条 |

**连续六次（2–7），从 17:48 到 21:03，整整 195 分钟，排第一的都是一次审计或一次流程交接。**
`synthesis_3` 自陈：

> "Candidate or hybrid: **No theorem-producing candidate is ready for Sketcher
> canonicalization.** … **Canonicalization target: NONE.**
> Exactly zero complete routes have an executable path to `main_theorem`."

根因：`prompts/synthesizer.md` 的八个评估维度
（目标保持、依赖清晰度、源定理风险、定义/记号风险、verifier 可检查性、
与历史重叠、反例风险、最终组装清晰度）**全部是风险规避维度**，
没有任何一个是"这条分支能否产出证明"。

> **当所有候选都带风险时，这套规则下的最优动作就是继续审计——而审计不消除风险，
> 所以它是不动点。**

代价：Q6 的反例车道 **13 次 CE-Hunter 调度、约 99 分钟、占运行 30%**，
产出 6 次杀掉分支、6 次纯保险、**0 次找到 `main_theorem` 的反例**。

**同一车道在别处是高回报的**：Q2/Q5 的 CE 在 t≈0 与 brainstorm **并行**派发
（边际墙钟≈0），且交付了真正的正面数学——Q5 的 Candidate 3 推出
`f(f(y)) = 2f(y) − y`，成为 `lem_orbit_sign`；Candidate 1 的恒等式成为 `lem_reverse`。
Q3 的 CE 在关键路径上但确实改变了路线，11 分钟买到四个事实，ROI 明确为正。

**差别在于审计的目标是否已知**：由具体失败节点触发时，问题有界，
答案无论正负都改变下一步；由「没有别的能排第一」触发时，问题无界，
返回「没找到反例」时**信息量为零**。而按现行规则，
「再审计一次」的风险恒为最低（它不可能引入错误），所以它是稳定解。

### 2.2 K10 — 危险率塌陷

3_1 的决策 16–30 是**连续十五次派发，每一次都被紧接着的下一个决策杀掉**。
这些决策结构完全相同（同一分类、7 条禁令、5 条 reusable work、3 条排队备选、
约 29 处路径引用、8.0±0.3 KB），**只有机制族的名字在换**：
motivic-period/coaction descent → Rademacher–Dedekind modular-cocycle →
Dirichlet-character/Gauss–Bernoulli L-value → Kronecker-limit/automorphic-Green →
probability-simplex/entropy chain-rule，全部是
*"certificate for the fixed eight labelled endpoint generators"*。

**固定目标、固定单次成本、每轮加一条排除、从无穷族里抽名字——刻板的枚举极限环。**
3_1 有约 10 小时在里面。

**从犯错到纠错的时间不增长**（钉在约 40 分钟，全程不变）——
所以复利不在单次成本上，**在于期望需要的次数发散**。
K10 的止血在 ADR 0024 §D-bis（探索预算）与 §F（机制族账本），
但它的**语义**属于本 ADR：一个"未定"的结论不得与"已否决"行为等同（§B）。

**运行机制的补充**：K10 之所以能反复发生，是因为每次换的名字都是 agent
自己发明的、无处定义的标签（`DISPOSITION=INCONCLUSIVE`、`RANK3_EXECUTABLE=NO`、
`NO_OBJECT_CLAIM=NO`……），下游读者无法区分它们，只能一律按"不是 PASS"处理。
**七个不同的标签退化成同一个语义，于是换名字是零成本的。** 见 §T。

---

## 3. Decision

### 核心原则

三条，按重要性排列。

> **1. 严谨性是「你接受什么」的性质，不是「你怎么想」的性质。**
> 生成方只负责想，验证方只负责验证。
>
> **2. 一次失败是一个 test case 的失败，不是一个 theorem 的失败。**
> 「局部的尝试不成功」是关于**一次尝试**的陈述；
> 「这条路线行不通」是关于**一个数学命题**的陈述。二者不得写进同一个字段。
>
> **3. 模板限制角色，不限制方向。**
> prompt 里只保留「你是谁 / 产物写到哪 / 什么不许做（越权、降标准）」。
> **陈述目标，不举例子。** 「你可以选哪些做法」的枚举一律删除。

#### 原则 3 的证据与它的边界

关键在于**例子不是在限制，而是在把输出分布压到例子附近**。
模板从未禁止别的做法，但概率质量已经被例子拿走了——
这解释了为什么一个没有任何禁止性措辞的 `## Escalation` 段能造成十五次单向的升级：
它给了四个例子，**四个全是横向**（并行 Explorer、反例搜索、源定理组合、定义审计），
而 3_1 随后的十五次升级**全部是横向，零次纵向**。

由此得到一条可以一直用下去的分界：

> **描述「做什么」的地方不举例；描述「不许做什么」的地方可以具体。**
> 禁止不会把分布拉向自己。

这条分界在下文多处被引用（§E 的硬约束、§P.1 的 `--help` 设计）。
按它重审本 ADR 自身，已删掉 §C.1 原有的「下一个范围」三种合法来源清单。

现行 harness 把闸门装在想法尚未长大的地方：Explorer schema 要求标
`Verifier checkability`；Synthesizer 按它排序；Regulator 在实验开始前冻死坐标基底；
brainstorm 在 `first_missing` 中止；Code Executor 要求先验有限宇宙；
来源审计要求独立定理；route history 只做排除。

被误用的四条认证纪律：

| | 认证阶段（正确） | 发现阶段（灾难） |
|---|---|---|
| 反过拟合冻结 | 定义完整的实验不得事后扩基底 | 换基底恰恰就是发现的定义 |
| 不完整即不成立 | 缺一环的证明不是证明 | 缺一环的想法是发现的常态 |
| 来源必须是独立定理 | 引用必须可追溯、非循环 | 类比迁移不需要先有论文 |
| 必须可先验枚举 | 有限检查必须穷尽可复现 | 好想法在提出时通常圈不出有限宇宙 |

**并记一条对本 ADR 自身的约束**：为了修「纪律过强」而写出更多纪律，
本身就是同一个病。初稿新增了 33 个标签/字段/枚举值去修一个「标签太多」的问题；
裁剪标准是**删掉它，是否会导致某一次已发生的击杀无法被阻止**。

### A. 两个区，一个接口（双向）

```
        |──────── Orchestrator ────────|
        │                              │
        ▼                              ▼
   发现区 ──── 候选 + 未证明义务 ────▶ 验收区
      ▲                                │
      └──────── FAIL + 具体断裂点 ──────┘
```

回边携带的**不是**「这条路死了」，而是 Verifier 指出的**具体断裂点**，
它在发现区的语义等同于一条新的 `first_missing` 规格（§D）。
**验收失败是发现区的输入，不是路线的终点。**
唯一不能回流的是「有精确反例」——那才是真的关掉（§B）。

**核心不变量：**

> 发现区的产物只是猜测证据。它不是数学验证，不解除任何证明义务，
> 也不能在没有走通常的 specialist + fresh Verifier 流程的情况下并入 `proof.tex`。
> 两区**共享对象定义，不共享结论等级**。

对现有不变量的影响：

- **invariant 12（单遍验证、无结构性预检门）不受影响。** 它禁止的是*数学*预检；
  发现区不做数学检查也不给结论定级，与 ADR 0020 的索引新鲜度门同类。
- **invariant 16 被沿用并加强**：PSLQ、数值迭代、精确整数恒等式全部落在「检查」一侧。
- **invariant 7/8 被沿用**：每个候选必须同时产出至少一条未证明的全指标义务。
- **invariant 1 不变**：Orchestrator 不做发现，只负责排序与派单。
- **invariant 18 被细化**：「一次失败不算耗尽」保留，但"继续"的合法形式
  从「只能 pop 下一条」扩充为「pop 下一条 **或** 加深当前一条 **或** 回到一条 `open` 的」。

#### A.1 实现方式：拆分「角色」与「分区规则」

现行所有 agent 的 prompt **都是按验收区语气写的**：Explorer 的输出 schema 要求标
`Verifier checkability: high|medium|low`；Searcher 的产物要求 "primary-source theorem"；
Code Executor 的派单契约要求先验有限宇宙。**这三个都是发现侧的 agent，
三个都在用验收侧的标准要求自己。**

因此不做「按产物路径分区」（那只能约束产物能否承载证明重量，
管不到「排序看什么」和「什么算失败」，而 K9 恰恰出在后者），
改为**把每份 prompt 拆成两层**：

| 层 | 内容 | 数量 |
|---|---|---|
| **角色** | 你是谁、产物写到哪、不许做什么（越权、降标准）。**蒸馏，删掉其余一切** | 13 份，每份变短 |
| **分区规则** | 两侧各一份：什么算结论、什么算失败、排序看什么、能否承载证明重量 | **2 份，共享** |
| **绑定** | 派单时给定 mode；每个 agent 声明默认 mode | 一行 |

净效果：**prompt 总字数下降**（13 份各删掉一半，换来 2 份共享文件）。
交接由 Orchestrator 承担，即上图的两条边——hub-and-spoke 不变，ADR 0002 不动。

##### 分区规则放在哪一层

分区规则的要求是**每次派发都必须生效，且只写一份**。四层核对：

| 层 | 载入时机 | 是否满足 |
|---|---|---|
| `prompts/<agent>.md` | 每次派发常驻 | 生效可靠，但**要写 13 遍**——正是要避免的 |
| `.claude/agents/*.md` + `.codex/agents/*.toml` | 注册时 | 生效可靠，但**要写 13×2 遍**，且两套 harness 必然漂移 |
| `.agents/skills/` | **按需触发**（靠 description 匹配） | **不满足**：触发是概率性的，而这是必须生效的规则 |
| **`prompts/references/`** | 由 prompt 一行引用 | **满足**：写一份，13 份 prompt 各引用一行 |

**定案：`prompts/references/discovery-mode.md` 与 `certification-mode.md`。**
角色文件里那一行是「本 agent 的默认 mode 为 X；分区规则见 `references/<mode>-mode.md`」。
这一层有现成先例，仓库里已经这么用了七次（`latex-and-blueprint.md`、
`workspace-and-ownership.md`、`proof-obligations.md`、`verification-gates.md`、
`query-workflow.md`、`status-and-recovery.md`、`summary-outputs.md`），
是既定的 SSOT 惯例（ADR 0020），不引入新概念。

**skill 的判据值得单独记一句**，它对后面所有类似决定都适用：
skill 的载入由 description 匹配触发，是**概率性**的，
且它的触发条件越精确、越可靠。因此判据不是「重要与否」而是
**触发条件是否清晰**：
「每次派发都要遵守的分区规则」没有清晰触发点，不适合 skill；
「即将跑一个程序」有清晰触发点，适合（§G.2）。

#### A.2 mode 与 agent 的关系

**全部 13 个 agent 均可被派往任一 mode**，`mode` 由派单给定。
下表只是省略参数时的默认值，不是限制——Writer 可以写探索笔记，
KB-Manager 可以在发现区查已证结果，Refiner 可以整理一份还没验收的推演。

| agent | 默认 mode |
|---|---|
| Explorer、Searcher | 发现 |
| Verifier、Auditor、Refiner、KB-Manager、Writer | 验收 |
| Sketcher、Generator、Code Executor、CE-Hunter、Synthesizer、Regulator | 按派单给定 |

由此必须补一条约束，它正是两区分离的要害：

> **在发现 mode 下，任何 agent 的输出都不构成状态转移，也不承载证明重量。**

以最危险的一例说明为什么需要它。Verifier 跨区是有价值的——
让它快速看一眼「这个想法有没有明显毛病」比等到分解完再发现便宜得多。
**但如果它在发现区的输出仍然是 `PASS`/`FAIL`，那么按 §B 的定义，
一个 `FAIL` 会立刻把路线变成 `rejected`（硬墙）。**
那就等于把最强的验收判定装进了发现阶段——正是本 ADR 要拆掉的那个病，
而且是最严重的形态。

所以 Verifier 在发现 mode 下的输出格式必须不同：只说「哪里可能有问题」，
**不出 `PASS`/`FAIL`**。`rejected` 仍然只能由**验收 mode 下的 fresh Verifier** 置入。
这条写在 `discovery-mode.md` 里，一句话覆盖全部 13 个 agent，不需要逐个写例外。
ADR 0003（Verifier 恒 fresh）不受影响——它约束的是验收 mode 下的 Verifier。

##### 发现 mode 必须同时约束投入，不只是约束输出

上面那条规则说的是**产物的地位**（不构成状态转移），它没有说**该花多少力气**。
而一个照现行 `prompts/verifier.md` 跑的 Verifier 会做完整审计——
它的 `## Global Proof Refinement` 段要求读进整段运行史。
于是发现 mode 的实际行为会变成：
**付出完整验收的代价，产出一份不能改变任何状态的意见。**
按速度取证，**延迟由读入量驱动，而完整审计正是读入量最大的那一类派发**——
这条设计在最坏情况下会把 harness 变得更慢，而 ADR 0024 正在拼命减派发。

所以 `discovery-mode.md` 必须写死投入的形状，不能只写产物的地位：

| | 验收 mode | 发现 mode |
|---|---|---|
| 读入 | 整条链路 + 运行史 | **只读当前这一份候选** |
| 覆盖 | 穷尽，每一步都要检 | **快速扫一遍全部，不漏点** |
| 每个疑点的深度 | 追到底，给出判定 | **一行说清它是什么，不追证** |
| 产物 | 完整 review packet | **一份疑点清单**，每条一行 |
| 结论 | `PASS` / `FAIL` | 不出结论 |

**受限的是深度，不是覆盖。**

> **批注 N35 —— 你**（针对原稿的「第一个说得通的疑点就停，不枚举」）
> 也可以吧，但我觉得可以简单过一下疑点，不然可能导致多轮。
>
> **回答 N35 —— 你对，我上一版把限制加错了维度，已按你说的改**
>
> 我上一版写的是「找到第一个疑点即返回」，并说
> 「快与慢的差别在于要不要穷尽」。**这句话是错的**，
> 而且它错的方向正好是本 ADR 最在意的那个方向：
>
> - **浅扫一遍全部**：读入量与只看第一个疑点几乎相同（都只读当前候选），
>   成本增量很小；
> - **每个疑点追到底**：这才是完整审计的成本来源。
>
> 所以贵的是**深度**，不是**覆盖**。我把便宜的那一维给限制掉了。
>
> 而代价正是你指出的：第一个疑点停 → 候选回去改 → 再来 → 撞上第二个疑点
> → 再改……**一次能说完的事被拆成 N 轮**。
> 按 ADR 0024 的主定律 `T(N) = N × f(N)`（`f` 递增），
> **轮数是超线性项**，而单轮多扫几行是线性的。
> 拿超线性去换线性，方向反了。
>
> 改法就是上表第二三行：**覆盖要全，深度限死在「一行」**。
> 「一行说清它是什么」是可执行也可检查的，而且天然把深度压住了
> ——追证一个疑点不可能只写一行。

##### 疑点可修就回去修，不必等到验收

> **批注 N36 —— 你**
> 可以修的话可以回去修发现。
>
> **回答 N36 —— 采纳，补一条出路；这也让 N35 的多轮问题再降一层**
>
> 我上一版只写了「疑点写进本轮工作台，下游承接时可见」——
> 那是**存档**，不是**处理**。存档只保证它不丢，
> 但它仍然要等到验收阶段才会被真正应付。
>
> 补上第三条出路，让疑点在发现区就能就地消化：
>
> > 发现 mode 返回的疑点，Orchestrator 可以**直接派回原候选的 owner 修改**，
> > 不必先进验收区。修改后的候选是同一条路线的新版本，
> > **不新开分支、不进 route history、不改变状态**。
>
> 三条出路按成本排：
>
> | 疑点的性质 | 动作 |
> |---|---|
> | 能当场改掉（记号、边界情形、一个漏掉的条件） | **派回原 owner 就地改**（本条新增） |
> | 改不掉但知道缺什么 | 写成 `first_missing` 规格，成为工单（§D） |
> | 说不清是不是真问题 | 记进工作台，留给验收阶段（原有做法） |
>
> 第一行是新增的，也是最常见的一类。**它不违反任何不变量**：
> 修改由原 owner 做（invariant 13 满足），产物仍在 `discovery/`，
> 不承载证明重量，进验收区时照样走完整的 fresh Verifier 流程。
>
> 与 N35 合起来看：浅扫一遍拿到全部疑点，能就地改的一次改完，
> **原来要 N 轮的事情压回一轮**。

### B. 状态词整理：`rejected` 收窄

**这是本 ADR 的主决议。** 它替代了初稿中新增 `parked` 状态、
`parked_reason` 四值、`revisit_when` 六触发器、以及一个新工具的整套设计。

> **`rejected` ⟺ 有精确反例，或验收 mode 下的 fresh Verifier 给出 FAIL。
> 其余一律不是 `rejected`。**

核对它是否真能挡住已发生的击杀：

| 击杀 | 现在被记成什么 | 收窄后 |
|---|---|---|
| K1 冻结约定里算错 | `rejected`，永不重访 | 仍在队列（没有反例） |
| K3 PSLQ 空盒子 | 族级禁令 | 仍在队列 + 必须命名下一个范围 |
| K4 `first_missing` 中止 | 弹队列 | 仍在队列 + 一张工单 |
| K6 推不出有限宇宙 | `RANK3_EXECUTABLE=NO` 终止 | 仍在队列（没有反例） |
| K7 姊妹迁移「precedent only」 | 不可用 | 仍在队列 |
| K10 十五次换族 | 每次一条新禁令 | 前 14 条都不是 `rejected` |

**六种里六种都被这一条挡住**，且不需要新状态、新触发器、新工具、新的每轮必读。

#### B.1 状态词表

| 状态 | 含义 | 谁能置入 | 出路 |
|---|---|---|---|
| `active` | 当前正在做 | Orchestrator | 任意 |
| `queued` | 在主路上排队 | Orchestrator | → `active` |
| `open` | 仍有机会，但不在主路上 | 任意 | → `queued`（Synthesizer 排序时） |
| `blocked` | 等一个**写明的**外部条件 | 任意，**必须写明条件** | 条件满足 → `queued` |
| `rejected` | **有精确反例，或验收 mode 的 Verifier FAIL** | **只有验收 mode 的 Verifier / 精确反例** | 无（硬墙） |
| `done` | 已完成并通过验收 | **只有验收 mode** | 无 |

`queued` 与 `open` 的区分（「在主路上排队」vs「还有机会但不在主路上」）
对 Synthesizer 是两种不同的输入，合并会丢信息；
`blocked`（等一个外部条件）与「没人排它」也是两回事，
合并之后无法机械地找出「外部条件已满足」的那些。
`superseded` 删除——取代关系应记在那另一条上，而不是给被取代者一个新状态。

**默认落点**：一次尝试不成功而没有反例时，默认是 `open`，
**不是** `rejected` 也不是 `blocked`。`blocked` 需要举证（写明在等什么），
这防止它变成 `rejected` 的替身。

##### 六个状态词各自的实现位置

状态词本身只有一个定义点，但**「谁能置入」这条约束散落在四处，必须一起改**，
否则收窄形同虚设：

| 要素 | 实现位置 | 现状 |
|---|---|---|
| **状态词定义** | `.agents/skills/nl-prover/references/branch-queue-cookbook.md` | 现有六个词，需替换（删 `superseded`，加 `open`，改 `rejected` 定义） |
| **状态写入** | `STATUS.md` 的分支队列表，由 Orchestrator 维护 | 无格式约束，任何词都写得进去 |
| **状态渲染** | `cli_tools/_memory/local.py`（`memory.py refresh`） | 已经在做，无需改动 |
| **「谁能置入」的约束** | **四处**：`orchestrator-cookbook.md` 的 "pop the next queued branch"、`regulator.md` 的失败分类、`prompts/verifier.md` 的判定输出、`discovery-mode.md` | **只改定义不改这四处，agent 仍会照旧把失败写成 `rejected`** |
| **机械校验** | `cli_tools/_gate/discovery.py`（本 ADR 新增） | 检查每条 `rejected` 带反例或 Verifier FAIL 引用；每条 `blocked` 写明所等条件 |

**一个必须一起做的清理**：`branch-queue-cookbook.md` 现在写的是
*"mark it `blocked`, `rejected`, or `inconclusive`"* ——
**`inconclusive` 出现在这句话里，但不在状态词表里**。
这是 §T 第三类（无处定义的标签）在 cookbook 层的一个实例，同批删除。

**不需要**实现的：不新增 `discovery.py revivable` 之类的工具。
`memory.py read --tier local` 每轮已经把分支队列送到 Orchestrator 面前，
缺的只是那份清单里的状态词有区分度——由上表第一行解决。

#### B.2 消费侧同步

`route_history` 的全部消费位置只有五处，改四处：

| 位置 | 现在 | 改为 |
|---|---|---|
| `prompts/explorer.md:29` | "choose the **nearest non-repeating variant**" | 只避开 `rejected` |
| `prompts/synthesizer.md:24` | 评估维度 "overlap with route history" | 删除（见 §K） |
| `prompts/synthesizer.md:39` | 比较表列名 "Repeats history" | 删除（见 §K） |
| `prompts/regulator.md:50` | "repeated failures … change in search mechanism" | 见 §E |
| `prompts/regulator.md:104` | 唯一的写：append-only | 不变 |

**这四行加上 §B 的定义修改，就是 K8 的全部解药。**
不需要「复活机制」——`open` 的分支从来没死过。

对 `revisit / resurrect / reopen / reconsider / unblock` 的全仓库检索，
在路线语境下**零命中**；仅有的两条 "reopen" 说的是
「排版失败不得重开已验证证明的数学状态」——方向恰好相反。
**三个读者全部把 route history 当排除清单；一个写者，只追加。**

#### B.3 义务清单是缺口清单，不是风险清单

两个方向的错误代价不对称：写少了会被 Verifier 抓住（有纠错机制，代价一轮验证）；
**写多了没有任何机制会发现**——没人会去证明一条不必要的义务不必要。
但「不应该写多」直接写成规则不可执行，所以改变它的**定义**：

> `obligation` 是**缺口清单**，不是风险清单。
> 每一条必须是「若核心断言为真，仍然缺少的一个具体构造/界/桥」，
> 而不是「这里可能有问题」。

这样过宽从判断题变成类型错误。**「可能有风险」的地方本来就该由 Verifier 去发现，
不该由提出者预先自我审查**——那正是核心原则 1 说的，把验收纪律装进了生成侧。
`obligation` 为空的候选不得进入验收区（invariant 7 已有此要求）。

### C. 否定结论必须带作用域，且必须开出后继

**问题定位。** `prompts/regulator.md` 的 `## Do Not Retry` 是必填输出段，schema 仅为
`- <specific route, theorem, estimate, definition reading, or NONE>`：
无作用域字段、无失效条件、无撤销机制、append-only。
2_5 跑 33 次 Regulator，2_7 跑 60 次，3_1 跑 71 次，只加不减。实际写出来的是：

> "Any closed PFQ, adjoint, integral, cone, Delannoy, Riesz, Padé, Mellin,
> factorial–Borel, qd, Askey/Racah, split-margin, sibling-transfer, or
> Raz–Shvets label **under a renamed convention**."

十三个方法族按名字一次关掉，还带防改名条款——**形式上完全合规**。
而赢下 2_2 的相邻指标平移 `w_m → w_{m+1}` **字面上就落在其中一族里**。

#### C.1 统一标签：在声明范围内无结果

**K2、K3、K6 是同一个形状的三个实例**，此前被写成三节，是因为盯着它们的领域
（文献检索 / PSLQ / 有限宇宙）而不是盯着它们的结构：

| 击杀 | 声明的范围 | 空结果被记成了什么 |
|---|---|---|
| K3 | 一个坐标 + 基底 | 十三个方法族的族级禁令 |
| K2 | 一次公开文献检索 | 结构事实所在路线 `resolved` |
| K6 | 推不出有限宇宙 | `NO_OBJECT_CLAIM=NO`，对象类的否定 |

三次都是「在一个范围内没找到」被记成了「不存在」。统一为一个标签：

> **`NO_RESULT_IN_DECLARED_SCOPE`** —— 适用于一切搜索：计算搜索、文献检索、
> 反例搜索、构造尝试。必填两项：**这次的范围是什么**；
> **下一个范围是什么**（必须是一个不同的、被写明的范围）。
> 它**永远不是** `rejected`，路线保持 `open`。

（初稿在此处列过「下一个范围」的三种合法来源，按核心原则 3 删除
——那是一份例子清单，会把后继实验的分布压到那三种附近。）

**这条规则在 2_5 上的具体含义**：实际跑的盒子用的是归一化坐标，没跑的那个是
原始 `w_i` 坐标 + 基底 `[w_i, G, log2, 1]`（G 为 Catalan 常数）。
**那个实验一次 0.455 秒，而且它就是对的。**
harness 整个运行没做它，不是因为算不动，是因为自己写的禁令不让做。

#### C.2 禁令记录

每条禁令必须带 `scope`（关闭的是哪个盒子）与 `evidence`（关闭它的确切产物路径）。
**关闭一个盒子，不关闭这个盒子所属的族。**

族级信息由 `family` 字段承担，**与 ADR 0024 §F1 共用同一字段**，只记一次。
初稿的 `expires_on` 与 `class` 两个字段删除：
前者与 ADR 0024 §F3「同族第 3 次触发回看」重复，且要求 agent 预测未来，最易被敷衍；
后者与族计数重复。

**预算决定不得写成禁令。** 2_7 的
*"Do not scan adjacent orders, kernels, basepoints, or scalar prefactors"*
是预算理由写成的族级禁令。预算耗尽记为路线保持 `open` 并注明预算，不进 `Do Not Retry`。

#### C.3 反过拟合由正确机制承担

现行做法（禁止第二次实验）是用粗暴代理去实现一个本有精确实现的目标。
被封死的那条补救逐字为：

> "Adding π, **logarithms**, other beta/L-values, or source constants after
> inspecting a failed relation."
> "**failure cannot trigger a basis or coordinate expansion.**"

正确机制是**预先声明 + 未触碰的留出深度 + 精确残差**：先声明用前 N 位精度识别关系，
剩下的位数不参与识别，识别出来之后拿剩下的位去检验。
这个机制既精确又便宜，而且**允许换任意多次基底**——每次换基底后留出位仍是独立检验。

### D. `first_missing` 从终止条件改为派单触发器

`3_1/routes/brainstorm_26.md` 是获胜策略本身，正确定位唯一缺口并把缺失定理
写成精确规格 `QLI-T`（"a target-independently specified finite-order subgroup"），
然后按 Decision-8 自杀：

> "Decision-8 **requires abandonment** at this first absent lattice/object-bridge row,
> so this packet performs no enclosure and isolates no coefficient."

**它是被规则叫停的，不是写不动了。** 网页会话补上的恰好就是这份规格。

**能把自己的缺口写成规格，是发现阶段能产出的最高价值信号，不是失败。**
三种「卡住了」的写法价值差别极大：

| 写法 | 例子 | 下一个人能做什么 |
|---|---|---|
| 卡住了 | "no executable path" | 什么都做不了 |
| 缺一个东西 | "需要一个合适的子群" | 不知道什么算合适 |
| **缺口规格** | "a target-independently specified finite-order subgroup" | **可以直接去构造并检验** |

该规格成为一张可派发的任务单；路线保持 `open`，**不得记 `rejected`**。
`prompts/` 与 brainstorm 协议中一切「遇到缺口即放弃」的条款删除。

#### D.1 规格写必要条件，不写充分描述

除了「规格写错」（§D.2），还有一个更隐蔽的失效模式：**规格写得太严**。
规格每多一个条件，可行解集就小一圈，而多写的那些条件往往只是提出者当时
脑子里那个具体实现的痕迹，并非真的必需。极端情况下规格变成
「照我想的那个东西造一个」，解集只剩一个点甚至是空集——
**而没有任何人会去检查这些条件是不是真的必要**。
这与 §B.3 的 `obligation` 过宽是同一类错误的两个位置：
都是把「我当下的设想」写成了「必须满足的要求」，且都没有纠错机制。

措辞上的要求：

| 不要写 | 要写 |
|---|---|
| 「它必须是……」（充分描述） | 「满足以下即可……」（必要条件） |
| 把实现细节写进规格 | 只写**它将被用来做什么**（即 `consumed_at`） |
| 规格是契约 | **规格是参考** |

并写成一条明确规则，使「规格写太严」变成可自愈的
——多余的条件会在第一次被绕过时暴露：

> 承接工单的 agent **不受规格字面约束**。若它造出的对象不满足规格的某一条，
> 但确实填上了 `consumed_at` 指向的那个洞，**视为完成**，
> 并把「那一条其实不必要」作为一条发现记回工作台。

#### D.2 防止错误规格向下游扩散

规格写错的失效模式比一般错误更贵：规格错 → 下游按错规格造出一个东西 →
造出来了、验收也过了（它确实满足那个规格）→ **拼接时才发现它不解决问题**。
错误在最远处才暴露。两个字段把暴露点提前：

| 字段 | 内容 | 它防住什么 |
|---|---|---|
| `acceptance` | 怎么判断造出来的东西满足了规格（一个可判定的检验） | 规格写得含糊 |
| `consumed_at` | 它将被用在**哪一步**、替换掉证明里的哪个洞 | 规格写得跑题 |

有了 `consumed_at`，规格是否跑题在**派单前**就能被 Orchestrator 核对——
它指向的那个洞必须真实存在于当前的分解里。

##### 这两个字段该由谁写

「自己给自己出考题」的风险在两个字段上不对称：

**`consumed_at` 由提出方自己写没问题。** 它是**客观可核对**的——
它指向当前分解里的一个洞，那个洞要么存在要么不存在，
Orchestrator 在派单前一比对就知道。自欺在这里不成立。

**`acceptance` 由提出方自己写有问题。** 同一个 agent 既提出规格又定义
「什么算满足」，最省力的写法是把 acceptance 写成规格本身的复述
（「满足上述规格即为通过」），于是它退化成同义反复，一点约束力都没有；
更糟的是它照着自己心里那个实现去写，于是只有那一个实现能通过
——这正好与 §D.1 的「规格过严」合流。故：

> **`acceptance` 由消费方写**，即由 `consumed_at` 指向的那一步的 owner 写：
> 「我这一步需要一个什么东西，我拿到之后怎么验它够用」。
> 这天然避免同义反复，因为消费方关心的是**够不够用**，不是**像不像我想的那个**。
> 若消费方尚不存在（洞还没有 owner），`acceptance` **允许留空**，
> 由 Orchestrator 在派单时补，或在工单完成时由 Verifier 判定。
> **留空好过写一句同义反复。**

不采用「让另一个 agent 复核 acceptance」——那是多一次派发换一次弱检查，
而按速度取证，多一次派发的成本是超线性的。

§D.1 与本节指向同一件事：**规格的约束力不应该由提出者单方面决定。**
前者从下游解决（承接方可绕过多余条件），后者从上游解决（验收条件由消费方定）。

### E. 升级阶梯：删例子，加一条硬约束

`prompts/regulator.md` 的 `## Escalation` 现在是：

> "recommend **a change in search mechanism** … Examples: **parallel Explorers with
> different diversity constraints**, counterexample search, source theorem portfolio,
> or target-reading/definition audit."

四个例子全是横向，而 3_1 随后十五次升级全部横向。
**解法不是再加三个纵向例子**（那只会把封闭清单从四项变成七项），而是：

1. **删掉例子清单**，只保留目标句：

   > 说明为什么继续按现在的方式做下去不会成功，以及你建议改变**什么**。
   > 改变可以是方向，也可以是投入强度、粒度或 owner。

2. **保留一条硬约束**（这条必须是规则不能是建议，因为它对抗的是极限环）：

   > 同一机制族连续第 3 次失败时，你的建议**不得**是换到第 4 个机制族。

   与 ADR 0024 §F3 是同一条，合并计，不重复实现。
   按核心原则 3 的分界，这里可以写得具体——**它是禁止，不是候选清单。**

##### 这条硬约束在说什么

**「机制族」是「用哪一类数学机器去打这个目标」**，比 route 粗得多。
3_1 里连续出现的五个族是 motivic-period/coaction descent、
Rademacher–Dedekind modular-cocycle、Dirichlet-character/Gauss–Bernoulli L-value、
Kronecker-limit/automorphic-Green、probability-simplex/entropy chain-rule。
**它们是五种完全不同的数学，但打的是同一个固定目标**——
每一次的措辞都是 *"certificate for the fixed eight labelled endpoint generators"*。

它对抗的失败形状是：

```
选一个族 → 派发 → 失败 → Regulator 说「换个搜索机制」→ 选下一个族 → …
```

3_1 的决策 16–30 连续十五次都是这个形状，十五份决策文件的结构统计几乎逐字相同
（同一分类、7 条禁令、5 条 reusable work、3 条排队备选、约 29 处路径引用、
8.0±0.3 KB），**变的只有名字**。目标、粒度、投入强度、owner 全都没变，
约 10 小时在这个循环里。这就是**极限环**：每一步都合规，整体不前进。
而且它自我维持——每换一个族就多一条禁令，可选空间单调收窄，
**而候选族的名字池是无穷的**，所以它永远能找到「下一个还没试过的族」，
永远不会自然停下。

**所以这条约束在说：数到 3 就不许再用「换个族」这个动作了。**
它不指定该做什么（那会犯核心原则 3），只关掉那一个出口；
剩下的合法动作自然是纵向的，不用列举。

**为什么必须是规则不能是建议**：写建议正是现状——
`## Escalation` 现在说的就是「建议改变搜索机制」，一句纯建议，
而模型十五次都选了同一种改变。**对抗一个稳定的循环，
需要一个不依赖当事人判断的外部计数器**，因为判断力本身已经在循环里了。

检查由三个部件完成，其中两个在别处已定义：route 产物带 `family` 字段
（ADR 0024 §F1，与 §C.2 共用）；`gate.py` 数同一 `family` 的连续失败次数；
到 3 时若建议指向一个新 `family` 则拦下。
门控只做计数与比对，**不判断建议好不好**——这是它能机械执行的原因。

**一个边界**：「同一族第 3 次」不是「同一族只能试 3 次」。
族内继续加大投入、换粒度、换 owner 都不受限制，
受限的只有「跳到第 4 个族」这一个动作。

同时放宽
*"Do not collapse recovery into a single owner when materially different next branches exist"*
——当存在一条带精确 `first_missing` 规格的路线时，允许收敛到单一 owner。

### F. 文献检索为负，不关闭任何数学路线

**证据一（2_5）**：问题最强的结构数据 `κ_A = (4,7,13)ᵀ` 在 `STATUS.md:64` 变成了

```
| Full initial-data source fingerprint | Searcher | … | resolved |
  Public search closed negative: the challenge statement is the sole exact fingerprint hit |
```

**一个数学事实被「解决」成了一次失败的文献检索，状态 `resolved`。**

**证据二（2_7）**：从 p08 迁移来的 ₄F₃ 被自判为 "genuinely transferable object" 之后，
下一步是一份给 Searcher 的检索请求——"Locate **a primary-source theorem** …"。

**成因**：`prompts/regulator.md` 的六类失败表中，
「我有一个关于目标对象的精确结构事实，不知道它从哪来」最贴近 `context-source`，
而 `context-source` 的 typical next owner 是 Searcher / Auditor / KB-Manager。
**表里没有一个类别叫"我有一个结构对象，去用它"。**

**决议**（不新增分类，一句话即可，理由见 §T）：

> **文献检索为负，只关闭「找出处」这件事，不关闭任何数学路线。**
> 寻找一个结构事实的出处，与利用这个结构事实，是两件不同的事。
> 出处只在该事实需要**承载证明重量**时才是必要的（invariant 10），在发现阶段不是。

出处的边界，精确到三行，避免误伤 invariant 10：

| 阶段 | 出处的地位 |
|---|---|
| 发现阶段 | **无关**。搜不到照做 |
| 验收阶段，该事实不承载证明重量 | 无关 |
| 验收阶段，该事实承载证明重量 | **必需**——但合法形式有两种：引用文献，**或在本文给出完整证明** |

第三行的第二种形式，invariant 10 现行措辞 "source **or derivation route**" **已经包含**。
问题只是 Searcher 返回负结果时没人走第二条。故在 `prompts/searcher.md` 加一句：

> 检索为负时，产物必须写明「该事实若需承载证明重量，可改由本地推导承担」，
> 并把它作为一条待派工单交回，**而不是关闭路线**。

### G. 发现区允许「任意但已声明」的盒子

**证据（2_7 ₃F₂）**：

```
DISPOSITION=INCONCLUSIVE / FINITE_UNIVERSE_NOT_DERIVED
RANK3_EXECUTABLE=NO      NO_OBJECT_CLAIM=NO      P07_CLAIM=NO
```

> "**Do not execute** Synthesis Rank 3 as a Computation Auditor search.
> The finite-universe and non-arbitrary gauge-cap preconditions **were not derived**."
> "A height box, increment box, denominator template, or gauge-degree cap
> **would be arbitrary**, so there is no restartable finite Computation Auditor packet."

**agent 明确声明这条路没有被证伪，只是不能开始。**
而同一份 brainstorm 的约束标签里写着 `non-computational`——
评估载体是否存在的 agent 被明令禁止计算。

**G.1** 在发现区，一个高度框、增量框、分母模板或规范次数上限**可以是任意选的**，
只要它被**预先声明**并且**留出未参与识别的深度**。
「任意」在认证阶段是缺陷，在发现阶段是必要条件。
若唯一障碍是「任何盒子都会是任意的」，正确动作是**声明一个盒子并试**。

**G.2 计算能力的分工。** 删除 `non-computational` 作为发现阶段的合法约束标签，
并补上真正缺的东西——Explorer 的输入契约
`{problem_file, target_contract, decomposition_file, route_history, diversity_constraint}`
**五个输入没有一个能跑代码**，所以「探索」实际发生在**路线名称的空间**里，
不在数学对象上。这是 K2 与 K6 的共同根源。

| | Explorer | Code Executor |
|---|---|---|
| 目的 | 试一下这个想法像不像对的 | 审计已声明的结果 / 穷尽搜索 |
| 规模 | 秒级、单次、无需可复现包 | 分钟级以上、必须留可复现脚本与数据 |
| 产物地位 | 只是线索 | 可承载证明重量（走完验收后） |
| 例子 | 2_5 那个 0.455 秒的 PSLQ | 3_1 的有限宇宙穷尽扫描 |

注意 2_5 那个决定性实验**恰好是秒级的**。现行架构下它落在 Code Executor 的
重型审计流程里，需要先有有限宇宙、可复现包、审计契约，于是整个运行都没做。
护栏：**Explorer 的计算结果只能被引用为「值得一试的理由」，不得被引用为证据。**

##### 资源护栏

给 Explorer 加 REPL 之后，这从一件小事变成了前置条件：计算能力从
「一个受重型审计契约约束的 agent」扩大到「每个 Explorer 都能随手跑」，
**并发的 REPL 数量会上一个量级**（ADR 0024 还要提高并发度）。

**做成 skill，不做硬限制。** 判据是**触发条件是否清晰**——
「即将执行代码 / 启动长时间计算」是这套 harness 里最清晰的触发条件之一，
正是 skill 机制最擅长的形状；而大部分派发不跑程序，这部分上下文成本直接为零。
（对照 §A.1：分区规则不适合 skill，是因为「每次派发都要遵守」没有触发点，
不是因为它重要。）

skill 的内容是让 agent 在**写实验之前**就把规模想清楚：
预估内存与时间、先跑小规模再放大、输出落盘而不是全打印、循环设上界。

**其中一条必须写进去**：若一次计算被外部终止或自行超时，
**那是资源问题，不是数学结论**——agent 必须把实验切小重试，
**不得据此关闭路线**。没有这一句，被中断的实验会按 K6 的老路被当成
「算不出来」，然后整条路线被判死，那正是本 ADR 要修的病。

> **批注 N37 —— 你**（针对我建议保留的墙钟超时）
> 不要了，因为这有可能限制能力。
>
> **回答 N37 —— 照办，墙钟超时删除；把这个决定的边界记清楚，以便日后回看**
>
> 决定：**不设任何执行层的资源硬限制**，全部交给 skill。
>
> 记录一下这条决定各自放弃和保住了什么，因为它是一个明确的取舍而不是疏漏：
>
> - **放弃的**：一个 agent 写出意外死循环或规模估错三个数量级的扫描时，
>   没有任何机制会终止它。skill 覆盖的是意图，覆盖不了失误。
>   REPL 并发上一个量级之后，这类事件的频率也会跟着上一个量级。
> - **保住的**：你担心的那件事是真实的——一个墙钟上限会变成
>   「多长的计算算合理」的隐含答案，而这个数**不可能事先定对**。
>   2_5 的决定性实验是 0.455 秒，3_1 的有限宇宙扫描是分钟级以上，
>   两者差四个数量级。**任何一个统一的超时值都会在某一端犯错**，
>   而犯错的方向恰好是本 ADR 全篇在修的那个方向：把「资源不够」
>   误当成「这条路不行」。
>
> 也就是说，超时不只是一个操作参数，它同时是一条**未经证据的关于
> 「实验该多大」的先验**——而 §C 整节讲的就是这类未经证据的先验有多贵。
> 按这个理解，你的判断比我的建议更贴合本 ADR 自己的原则。
>
> **保留一条与服务器无关的上限**，因为它不限制计算规模：
> **REPL 输出字节上限**。它不终止任何计算，只截断打印，
> 而一份几十 MB 的输出会进入下游 agent 的读入量——
> 按速度取证，**读入量是延迟的主因**。这条是防拖慢，不是防跑飞。
>
> **定为宽松**（人类判断：可以限制，但无需限制得太狠）。
> 落地取法：上限设在**正常实验绝不会触及**的量级，
> 只拦住失控打印那一类；截断时保留头尾并注明「已截断」，
> 全量输出仍落盘可查——**agent 想要的数据一个都不会少，
> 少的只是把它整份塞进下游上下文这件事**。

**G.3 阶梯式推进是合法路线。**

数学解题通法（先加条件再想办法去掉、先做特例再推一般、先猜后证、找不变量等）
**不写进 prompt，也不写进本 ADR**——写进 prompt 会犯核心原则 3 的错，
而 ADR 记的是「我们为什么这样搭系统」，不是「怎么做数学」。
它们归 `.agents/skills/`：按需触发，不用时零成本，
而 prompt 里的每一行都要被每次派发读一遍。

**本 ADR 只保留架构侧那一半**（它确实是架构问题）：

> 在发现区，允许先证明一个加强了假设的版本，前提是**加强的假设被显式列出**，
> 并作为一条 `obligation`（去掉它）留在工作台上。
> 这类中间结果不得进入 `proof.tex`，但它是完整的路线进展，
> **不得记为失败，也不得触发换方向。**

最后一句是关键：这种中间结果现在**没有地方安放**，
于是它要么被包装成完整结论（危险），要么被当成失败弹掉（浪费）。
这条与 Rules for All Agents §5「不得默默加强假设」不冲突：
那条禁止的是**默默**，本条要求**显式列出**。

##### 通法 skill —— 本轮搁置

> **批注 N38 —— 你**
> 先搁置吧。
>
> **回答 N38 —— 照办，从实现清单移除。记下搁置时已经查清的三件事，
> 免得日后重来一遍**
>
> **1. 检索结果：不存在「星星多的」数学通法 skill。**
> 直接相关的候选只有两个，星数都极低：
>
> | 仓库 | 星 | 许可 | 形态 |
> |---|---:|---|---|
> | [`googlarz/math-skill`](https://github.com/googlarz/math-skill) | **6** | MIT | 按情境组织的四本 playbook（problem-mapping / method-selection / solver-loop / verification）——形态合用 |
> | [`agtm1199/uber-polya`](https://github.com/agtm1199/uber-polya) | **3** | Apache 2.0 | 代码为主，33+ 问题分类——形态不合用 |
>
> 星数高的（[VoltAgent 约 29.6k](https://github.com/VoltAgent/awesome-agent-skills)、
> Anthropic 官方约 150.6k、若干社区目录 2.2 万–4.4 万）
> **全部是聚合目录，不是内容本身**。
> 旁证：[`cc-thinking-skills`](https://github.com/tjboudreaux/cc-thinking-skills)
> 是「18 个思维模型」——恰好是清单形态，且是通用思维不是数学。
>
> **2. 这推翻了「不自撰」这条指令自身的论据。**
> 不自撰的理由是「现成的被很多人筛过，质量下限更高」，
> 而一份 6 星的 skill **没有被很多人筛过**，那个保证并不存在。
> 所以搁置是合理的：既没有可直接用的现成品，
> 又不该在没有把握的情况下自己编一套方法论。
>
> **3. 日后若要重启，形态标准仍然有效**（它们来自核心原则 3，与检索结果无关）：
> 优先「按情境组织」而非「按技巧枚举」；skill 的 description 写成窄触发。
> 以及一条本轮浮现的可能路径：借用 `math-skill` 的 playbook **结构**，
> 内容用本仓库的取证重写——我们手上有别处没有的东西，
> K1–K10 是十条有据可查的真实失败，而通用 skill 只有正面建议。
>
> **搁置不影响 §G.3 的架构条款**（阶梯式推进是合法路线），
> 那一条不依赖任何 skill 存在。

### H. 同侪迁移是一等公民

**证据（2_7）**：本地已验证的姊妹问题构造被判为不可迁移：

> "It is **a local proof for different literal data, not an independent theorem**
> deriving p07 data. **Transferring its concrete parameters or normalization would be
> unsupported.** | accepted local sibling artifact; **precedent only**"

而外部投稿在 13 小时后到达，用的正是同一机制类。

**H.1** 一个在姊妹问题上已被 fresh Verifier 接受的构造，在本问题上是
**一等的发现证据**，不是"precedent only"。
「它是针对不同字面数据的局部证明」是**验收阶段**的正确异议，
在**发现阶段**不构成不尝试的理由。

**H.2 可迁移的是思想；不可强制的部分不要设 schema。**
2_7 自己已经把这件事说对了：

> "**This is the genuinely transferable object**: `trajectory_matrix` generated a
> target-independent contiguous matrix, while inverse transpose supplied the
> recurrence carrier."

**模型能写出来，只是系统没有地方存它。** 所以切成两半：

| | 内容 | 能否机械化 |
|---|---|---|
| 可强制 | **参数必须在本问题重新导出**，不得从姊妹问题抄 | 能。检查引用来源 |
| 不可强制 | 思想 / 品味的迁移 | **不能。给它一个存放的地方，别的什么都不做** |

**不要给「思想」设计 schema。** 一旦要求按字段填写，
模型会填出可通过 lint 的空话——27 张经验卡片就是这个下场（§L）。

#### H.3 存放位置与它的命名

存长期记忆层，不需要新族。`cli_tools/_memory/experience.py:31` 的
`CARD_KINDS = ("negative-constraint", "heuristic-threshold")` ——
**后者从未被用过（27/27 全是前者），它就是这类知识的位置。**

准入走 §L.2 的统一条件（能否用在别的题上）。卡片只有 `trigger` 必填，
因为**没有 trigger 的卡片永远不会被召回**，只会让 `memory.md` 变长
——现行 `cardlint.py` 已经在做这个检查，保留。
正文（这道题给了我什么可能对别的题有用的想法）是自由文本，不做 lint。

一个已知的取舍：`trigger` 要求把「品味」写成可识别的结构线索，
这本身会损失一部分难以言表的东西。这个损失必须接受——
存不进 `trigger` 的东西，系统也没有办法在下一道题上把它取出来。

**命名修正。** `heuristic-threshold` 这个名字本身是 27/27 全是禁令的成因之一：
它字面指向一个**数值边界**（「迭代超过 N 次就换路」），而不是「一个可能有用的想法」。
一个 agent 想记「M(n) 是 ₄F₃ contiguous relation 的对偶」时，
看这个名字**不会认为它属于这里**，于是只剩 `negative-constraint` 可选。

> **改名为 `transferable-idea`** ——名字直接说出准入条件（可迁移），与 §L.2 一致。

改动面：`_memory/experience.py:31` 一个字符串常量、`cardlint.py` 的报错文案、
`memory-routing/SKILL.md` 的示例。既有 27 张卡全是 `negative-constraint`，
**不受影响，无需迁移**。

（另一个方案是合并成一个 kind 加 `polarity: +/-`，概念更干净，
但要改渲染与去重逻辑且多一个字段，不采用。）

### I. Route history 双向化

见 §B.2 的四行修改。补一条 Explorer 的措辞：
`prompts/explorer.md:29` 的 "choose the nearest non-repeating variant" 收窄为
「避免重复**已被证伪**的路线」；对 `open` 路线，允许并鼓励重新提出。

### J. 小的离散歧义先枚举再问人

2_5 中给定三个系数行与未知顺序，`proof_review_human_log2_vectors_1.md`
只枚举了 **2** 种排列，然后：

> "Selected status: **HUMAN_CLARIFICATION**"
> "Reason: the missing information is **external provenance, not a mathematical
> calculation the harness may infer**."

正确顺序是至多二十几种里的第三种。人类给出顺序后，**0.455 秒**全部对上。

**规则**：当一个离散歧义的合理候选集可枚举时，
**先机械枚举全部候选**，再考虑 `HUMAN_CLARIFICATION`。
**不设候选数上限**——真实成本与候选个数关系很弱（二十几种和几千种都是秒级），
写死上限只会给出一条合法的偷懒路径。只留反向要求：

> 若认为枚举不可行，必须写明**为什么**（候选集无界，或单次检验代价过高并给出估计）。
> 「候选太多」不是理由，除非附上数量级。

**默认动作是试，问人需要举证。**

### K. Synthesizer：排序只看两条

替换现行八个评估维度（目标保持、依赖清晰度、源定理风险、定义/记号风险、
verifier 可检查性、与历史重叠、反例风险、最终组装清晰度）——**八个全是风险侧**，
产出侧字数为零。这不是权重问题，是存在性问题。

> 对每个候选给出两项判断：
> **（1）可行性**——按现有能力，这条路线能被走通的把握；
> **（2）推进贡献**——若它的核心断言成立，目标被关掉多少。
> 两项综合排序。上述之外的一切信息（历史、风险、来源、可检查性）
> **是你可以引用的证据，不是必填的打分项。**

这一条同时修好 K9：加入「推进贡献」之后，**审计的贡献恒为零**，
它就不可能稳定排第一了。并连带解决三件事：

- **`verifier checkability` 自动消失**在发现侧，不需要单独写删除规则；
- **`Repeats history` 不再是减分项**（`rejected` 收窄后本来就不该是）；
- **不需要初稿加的两个新维度**（`coverage-if-true`、`proof-producing`）。

**可检查性的正确归属**是一条职责链，不是一个筛选条件：

| 阶段 | 谁 | 对可检查性做什么 |
|---|---|---|
| 发现 | Synthesizer | **什么都不做**（现状：拿它当筛选条件 ← 错） |
| 分解 | **Sketcher** | **把想法改写成可检查的形式**——这就是分解的定义 |
| 验收 | Verifier | 检查 |
| 呈现 | Writer | 让人类读得懂 |

Q2 的证据：Synthesizer 选了复坐标 Laurent 证书，否决综合几何路线的理由是它
*"presently unexpanded"*——**「现在还没展开」被当成了缺陷，
而那正是发现阶段所有好想法的共同状态。** 结果是六题里唯一一份人类读不了的证明，
而那条 rank-3 路线至今在 `STATUS.md` 里标着 `dormant`，从未被尝试。

**周期性回看由 Synthesizer 承担**，不新增 agent：它已经读 route history、
已经在排序、已经周期性被派发，边际成本接近零。
（Regulator 不合适——它只在失败时才跑，而漏掉的路径恰恰出现在
「没失败、只是没排第一」的时刻，Q6 那六次就是。）

### L. 记忆：一个准入条件，五处措辞与命名修正

现行长期层 100% 是 `neg-do-not-*` 过程禁令，
**没有一张记录数学技巧、来源或可复用的正面结果**。
它只能让未来的运行更慢，没有任何通道让积累的经验让它更强。

#### L.1 根因（实查结果）

写入路径是 `.agents/skills/memory-routing/SKILL.md:63-80`。
五条根因，**全部是牵引问题，没有一条是能力问题**：

| # | 现状 | 牵引效果 |
|---|---|---|
| 1 | **触发条件全是失败**："On a `verifier` FAIL, `regulator` classification, `ce-hunter` obstruction, or a human correction" | 成功从不触发写卡。**结构上不可能产出正面卡片** |
| 2 | 示例卡的 `kind` 写死 `"negative-constraint"`，是文件里唯一的示例 | 照抄示例是最省力的合规方式 |
| 3 | 字段名本身是禁令语义：`statement: <one-line **boundary**>`、`why: <failure it **prevents**>` | 即使想写正面的，字段不接受 |
| 4 | `gate stop` 强制：「有失败而未产卡则不通过」 | 每次运行都被迫产出禁令 |
| 5 | 正面卡片那个 kind 叫 `heuristic-threshold`（§H.3） | 名字指向「数值阈值」，想记一个想法的人不会认为它属于这里 |

**`scope` 字段本来就存在**（第 78 行 `"scope": "general"`），
但示例把它写死成 `"general"`，从来没有区分过 class-level 与 this-problem-only。
这与 `heuristic-threshold` 是同一个模式：**schema 是够的，命名与示例把路堵死了。**

这解释了 27 张卡里 `neg-do-not-extend-a-recorded-label-level-closure-termwise`
这类**条件从句长到只可能在原题复现**的卡片为什么能通过 lint——
lint 只检查字段齐全，不检查可迁移性，而 `scope` 那一列永远是 `general`。

修法五条，全部是改命名、示例与措辞，零新增机制：

1. **触发条件加上成功**：「一条路线走通时，同样写一张卡」；
2. **示例改成两张**，一正一负；
3. **字段改中性**：`statement: <这次学到什么>`、`why: <什么条件下适用>`；
4. **`scope` 取值收为二选一**：`class-level` / `this-problem-only`，
   且 `render-longterm` **默认只渲染 `class-level`**；
5. **`heuristic-threshold` 改名 `transferable-idea`**（§H.3）。

第 4 条使得 this-problem-only 的卡片仍然落盘（随 workspace 存档，可检索）
但不进常驻的 `memory.md`，于是常驻部分停止线性膨胀。
现行的 100 行上限因此从「靠合并维持」变成「自然满足」。

#### L.2 准入条件

> **写入长期层的唯一条件是：它在别的题上可能用得上。**
> 正面（一个想法在一类问题上可能有用）与负面（某处容易搞错）**同等对待**，都要过这一关。

不新增层、不新增卡片族。「负面约束层」这个名字本身是问题的一部分：
`CLAUDE.md` 的 Routing 段写的是 "read the resident **long-term negative-constraint** memory"，
`memory.md` 空时的占位文字是 `_(no long-term **negative-constraint** cards yet)_`。
**agent 每一轮读到的都是「这是一张禁令清单」，于是它写回去的也只会是禁令。**
统一改为 "long-term memory"。

#### L.3 账的数量

现有四本：`memory/experience/`（长期）、工作区 local tier、KB wiki、
以及初稿想加的 conjecture ledger。**初稿的第五本撤销**：
conjecture ledger 不新开文件，它就是工作区 local tier 里多出的几列
（`claim` / `evidence` / `obligation` / `status` 四列必填，`transferable: yes/no` 选填）。

理由有硬数据：延迟由**读入量**驱动，与写出字节数几乎无关——
有一次派发只写了 459 B 却花掉 4.3 分钟，另一次写了 22,820 B 只花 1.6 分钟。
**加一列是廉价的，加一本必读的账是昂贵的。**

初稿的 `kind` 五值枚举删除，换成布尔 `transferable`：
五个取值里只有一个有行为后果（决定这条记录会不会被下一道题读到），
其余四个只是分类学，没有任何代码或 prompt 会因为它们做不同的事。

### M. 续跑与 fresh

**不新增长期存活的数学 agent。** 网页那次「94 分钟连续」包含两件事，价值不同：
（a）上下文不断——后一步能看到前一步的完整推演，不必从产物里重建；
（b）没有外部打断——不必每隔一步就把状态写成文件交给别人。
**(a) 是真价值，(b) 不是。** 而 (a) 在现行架构下已经可以实现：
Claude 侧的 Task、Codex 侧的 custom agent 都支持 resume。
现行做法是每次新起一个，那是使用方式的问题，不是架构限制。

> **规则**：所有 specialist 允许被续跑——同一实例在同一条路线上多次唤醒，
> 保留自己的工作子目录，每次唤醒不要求重新交付完整产物。
> **唯一例外是 Verifier：验收 mode 下它恒为 fresh、stateless（ADR 0003 不变）。**

**是否续跑由 Orchestrator 在派单时决定**，与 mode 一起作为派单参数。
理由与 invariant 1 一致：续跑与否是**路由决策**，不是数学决策。
这一条不能省——不指定谁决定的话，默认落点会是 specialist 自己，
而它会倾向于总是要求续跑（上下文越多越省力），
于是「续跑」从可选项变成事实上的常态，
Verifier 之外的防锚定考虑就没有执行者了。由此明确两条：

- **验收 mode 下的 Verifier，Orchestrator 无权续跑**（ADR 0003 是硬约束，不是默认值）；
- **Auditor 做独立审计时按 fresh 派发**，理由与 Verifier 相同（防锚定）；
  它做非审计工作时可续跑。这一判断由 Orchestrator 按任务性质做，
  不由 Auditor 自己声明。

hub-and-spoke 不变：Orchestrator 仍是唯一派发者，仍通过文件通信，
变的只是「被派发的是不是同一个实例」。ADR 0002 不受影响。
**初稿新增的 Prospector agent 撤销**（`prompts/` 下本就没有这个 agent，
它是初稿的提案）；`brainstorm_26` 不是没能力，是被 Decision-8 叫停的。
缺的三样——遇到缺口必须终止、探索者没有计算能力、输出 schema 限制篇幅——
全部是删规则，不是加 agent（分别见 §D、§G.2、§K）。

### N. 记忆的加载策略

> **`memory.md` 默认加载。唯一的例外是 Explorer——它的输入里默认不加载。**

理由记录如下，以便日后回看这条边界为什么划在 Explorer：

- Explorer 是**唯一**其产物完全不承载证明重量、且完全在生成侧的 agent。
  对它而言长期层 100% 的禁令只有减法作用；
- Synthesizer 虽然也在生成侧，但它做的是**排序**而不是**生成**，
  而排序要判断「可行性」（§K 两条判据之一），
  **这正是跨题经验能起作用的地方**——哪一类路线在同类问题上通常走得通、
  哪一类通常卡住，是长期层该提供的东西。
  （早期草稿在此处写的理由是「排序需要知道哪些已被证伪」，**该理由不成立**：
  `rejected` 在分支队列与 route history 里，不在 `memory.md`——
  后者是跨题层，与本题哪条路被证伪无关。结论不变，理由已更正。）
- 2_2 的成功来自丢弃**上一次运行的封闭结论**，那是运行间的问题，
  与运行内谁读记忆是两件事，不作为本条的依据。

**不制度化「丢弃记忆重跑」。** ADR 0022（每次停止都写回记忆）不变——
本条改的是谁读，不是要不要写。

### O. Discovery Triage（次要条款）

以 Code Executor 的第二个模式 `DISCOVERY_TRIAGE` 实现，输出 `discovery/triage_<N>.md`。

**观测核审计**保留为常驻规则（这次失败里唯一结构性、可复用、且反直觉的发现）：

> 当一个 r×(r+1) 的初始矩阵观测一个射影极限时，**在做常数识别之前**先计算并记录
> 它的核，检验伴随 period 或对数项是否可能完全沿该核方向出现，
> 从而在最终被观测的比值中消失。
>
> 一般原理：**最终标量答案只包含某个常数，并不意味着内部极限方向只能由该常数表示；
> 其他 period 可能完全落在初始观测映射的核中。**

按 §L.2 的准入条件存入长期记忆层，`kind: transferable-idea`、`scope: class-level`。

### P. 机械门控：加豁免通道，减模式匹配

新增 `gate.py discovery <workspace>`，纯 schema 级检查：

| 检查 | 对应 |
|---|---|
| 禁令行含 `scope` 与 `evidence` | §C.2 |
| `NO_RESULT_IN_DECLARED_SCOPE` 带范围定义与下一个范围 | §C.1 |
| 预算耗尽未出现在 `Do Not Retry` | §C.2 |
| 带 `first_missing` 规格的路线未被标记为 `rejected`，且规格带 `consumed_at` | §D、§D.2 |
| `rejected` 条目均带精确反例或验收 mode 的 Verifier FAIL 引用 | §B |
| `blocked` 条目均写明所等条件 | §B.1 |
| 离散歧义升级到 Human 前已枚举，或写明不可枚举的理由 | §J |
| `discovery/` 下任何文件未被 `proof.tex` 引用 | 结论等级不串台 |

执行点两处（沿用 ADR 0022 的教训——**没有门要求它跑，它就不跑**）：
第一条结构性分支调度前；以及 `gate stop` / `gate complete` 各调用一次。

#### P.1 门控本身需要一个出口

实查结果两条：

**（一）零豁免。** `grep -rn "override|--force|allow_|waiver|exempt" cli_tools/_gate/*.py`
**零命中**。所有门控只有「通过」和「不通过」，
**没有任何一条带申诉、豁免或强制通过的通道**。
一旦某条正则误判，agent 唯一的合法动作是改产物去迎合正则——
那张 `kind: heuristic` 的卡片连试三天没改对字面量，就是这个形状。

**（二）模式匹配的规模。** 四个 gate 模块共 **22 张正则/关键词表**
（`review_packet.py` 10、`proof_review.py` 6、`result_contract.py` 4、`completion.py` 2）。
举一例，`result_contract.py:24` 的 `PROCESS_FAILURE_PATTERNS` 会拦下含
`\b(?:cannot|can't|unable to|do not)\s+(?:prove|establish|show|complete)\b` 的文本——
**一份诚实说明「本轮未能证明 X」的进度报告会被判为流程失败。**
这类检查是在用字符串近似一个语义判断，而近似的两侧代价不对称：
漏判只是少拦一次，误判则堵死一条正确路线。

**决议三条：**

1. **每个门控失败必须输出：违反了哪一条、合法取值是什么、最小修复是什么。**
2. **引入 `--waive "<理由>"`**：门控仍然记录违规，但不阻断，
   理由写进产物并在 `gate stop` 汇总。豁免可见、可审计、可事后统计。
3. **扫自由散文的模式匹配降级为警告**，不再阻断。

   > **实施时修正**：初稿写的是「22 张模式匹配表全部降级」。落地时逐张核过，
   > 这个数把两类东西混在一起数了，而且规则按字面执行会降低证明标准
   > （与 §4.3 冲突）。正确的判别不是「它是不是正则」，而是**它扫的是什么**：
   >
   > | 扫什么 | 处置 | 为什么 |
   > |---|---|---|
   > | **自由散文**（`proof.tex` 正文、进度说明） | **降级为警告** | 正则分不出诚实的「本轮未能证明 X」与虚假声称，而两向代价不对称 |
   > | **终局声明字段**（`FINAL_PROOF_READY` 的证明路线、`OBSTRUCTION_VERIFICATION` 的对象） | **保留阻断** | 在声称"证明就绪"的字段里出现「无法证明」是真矛盾，不是误判 |
   > | **结构性**（字段存在、文件存在、引用可解析、完成时义务未决） | **保留阻断** | 不需要理解语义，误判率接近零 |
   >
   > 按此实际降级两处：`completion.PROOF_PENDING_PATTERNS` 与
   > `result_contract.PROCESS_FAILURE_PATTERNS`，两者都扫 `proof.tex` 正文。
   > `proof_review` 的四处扫的是终局字段，保留；
   > `review_packet` 的五张表与 `UNRESOLVED_STATUS_TOKENS` 是结构性的，保留。

##### 门控的自述文档

每个 `gate.py <sub> --help` 输出三段——检查什么、合法取值、失败时怎么修，
**不含任何示范产物**。与决议第 1 条是同一份文案的两个出口
（一个在 `--help`，一个在失败时打印）。

「说明正确用法」与「不给例子」并不冲突，它们作用在不同的东西上：

| 可以给（不引起分布偏移） | 不要给（会引起分布偏移） |
|---|---|
| **字段清单**：这个门检查哪些字段 | 填好的样例产物 |
| **合法取值枚举**：`kind` 只能是这两个之一 | 「比如你可以这样写……」 |
| **失败原因与最小修复**：缺 `trigger` → 补一行 `trigger:` | 一段示范文字 |

判据与核心原则 3 的分界一致：**枚举「合法取值」是在划边界，
示范「怎么写」是在给样本。** 前者不改变边界内的分布，后者会把质量压到样本附近。
这也正是 `CARD_KINDS` 那次失败的教训——当时缺的恰恰是「合法取值枚举」，
而不是缺一个示范。

### Q. 验收区不动

**Q.1 验收区一个字不改。**（§1.4）

**Q.2 记账诚实性。** `2_2/STATUS.md` 声称「先前已验证的 53 页组装保留在
`refinement/original_proof.tex`」，而该文件是 2277 字节的 `\VerbatimInput` 包装。
新增机械检查：STATUS 中声称"保留"的产物必须存在且可重建。

**Q.3 外部来源披露。** 3_1 的 `proof.tex` 中 "imported package/manuscript"
出现约 20 次但从未说明来源；`writer/article_candidate*.tex` 中 "imported"
出现 **0 次**——Writer「剥离 agent 运行历史」的指令把"核心来自外部"一并剥掉了。
规范化：**外部供给的数学内容是来源事实，不是运行历史**，
Writer 必须保留其披露；`gate.py citation-audit` 增加对应检查。

### S. 规则只增不减（观测记录，机制另行处理）

一条观测，留给后续专门负责这件事的部分使用：

> **加规则有明确的触发时刻（出了一次事故），删规则没有。**
> 因此规则单调增长：3_1 的 71 次 Regulator、每次约 7 行禁令、
> 九个运行无一例外，曲线线性向上，没有任何向下的力。

本 ADR 内部对此只做一件事，且它已内置在裁剪标准里：
**每条限制必须写明它对抗的是哪一次具体失败**（33 → 6 就是这么砍的）。
`--waive` 的豁免率（§P.1）会自然积累成一份数据，本 ADR 不定义它的用法。

**一处边界必须现在划清**，因为它约束将来任何精简动作：
以上只适用于**发现侧**的规则。验收侧的严谨性标准
（invariant 3/5/7/8/10/12/15、ADR 0005）**不随模型变强而放松**——
它们对抗的不是模型的能力不足，而是模型的自信，而后者随能力提升只会更强。

### T. 分类清点与删除清单

**先澄清一个成本问题**：写标签**几乎不影响延迟**——延迟由读入量驱动
（一次派发只写 459 B 却花 4.3 分钟，另一次写 22,820 B 只花 1.6 分钟）。
标签的真实成本是**把连续判断压成枚举值**：模型本来能表达
「这条路在这个坐标下没找到，换个坐标可能有」，被压成 `NO_OBJECT_CLAIM=NO`
之后只剩一个布尔，而**下游读到的是那个布尔，不是那句话**。
K10 就是这个机制的极端形态——十五个不同的标签在下游退化成同一个语义，
于是换名字是零成本的。

**第一类：有代码消费的枚举**（保留，两处要改）

| 位置 | 枚举 | 处置 |
|---|---|---|
| `_memory/experience.py:31` | `CARD_KINDS = ("negative-constraint", "heuristic-threshold")` | **保留但改名**：`heuristic-threshold` → `transferable-idea`（§H.3） |
| `_memory/experience.py:32` | `CARD_TYPES = ("experience", "error", "obstruction")` | **删 `obstruction`**——它与 `error` 在渲染与召回上无差别 |
| `_memory/inbox.py:18` | KB 六种卡片前缀 | **保留**，KB 侧不在本 ADR 范围 |
| `_search/frontier.py:35-36` | `STATUSES`、`SOURCES` | **保留**，纯机械记账 |
| `_common/indexing.py:15-16` | `VIEW_CHOICES`、`FORMAT_CHOICES` | **保留**，CLI 参数 |

**第二类：只做引导、无代码消费的分类**（主要删除对象）

| 位置 | 内容 | 处置 |
|---|---|---|
| `regulator.md:25-32` **与** `orchestration.md:122-129` | **六类失败分类表，两处逐字重复** | **删表**。改为两个自由文本问题：「还缺什么」「接下来谁做」。理由：它已经把 K2 路由错了一整条路线，而六个类别没有任何一个被代码读取 |
| `synthesizer.md` | 八个评估维度 | **删**，换 §K 的两条判据 |
| `explorer.md` | 输出 schema 的 `Verifier checkability: high\|medium\|low` | **删**（§K） |
| `regulator.md` `## Escalation` | 四个横向例子 | **删**（§E） |
| `branch-queue-cookbook.md` | *"mark it `blocked`, `rejected`, or `inconclusive`"* 中的 `inconclusive` | **删**——它不在状态词表里（§B.1） |
| `verifier.md:162` | `--independent-warrant <PASS\|FAIL\|UNCLEAR>` | **保留**——验收侧，且有代码消费 |

六类失败分类表**逐字重复出现在两个文件里**，这本身违反 ADR 0020 的 SSOT 约定；
删除时两处一起删。

**第三类：agent 自创、无处定义的标签**（全部废止为状态词）

`DISPOSITION=INCONCLUSIVE`、`FINITE_UNIVERSE_NOT_DERIVED`、`RANK3_EXECUTABLE=NO`、
`NO_OBJECT_CLAIM=NO`、`P07_CLAIM=NO`、`NO_RELATION_IN_DECLARED_BOX`、
`HUMAN_CLARIFICATION`……**全仓库找不到它们的定义。**

> 它们说的话照常写在正文里，但**不构成状态转移**。
> 状态只由 §B.1 的六个词表达；「在某个范围内没找到」只由
> `NO_RESULT_IN_DECLARED_SCOPE` 表达（§C.1）。

**净变化**：可用状态词从「六个 + 不定数量的自创标签」变为六个有定义的状态词
加一个搜索结果标签；prompt 中删掉四张表；代码中删掉一个枚举值、改一个枚举名。
脚本侧的对应改动列在 §7，与 prompt 改动同批执行——**先定分类，再改脚本。**

---

## 4. Consequences

### 4.1 收益

- 系统第一次能持有一个「还不严谨的信念」，包括「这个对象其实是什么」
  和「隔壁那题的机制」这两类在现行架构中无处安放的知识。
- **被搁置的路线第一次有回来的路。** K8 被拆掉之后，K1–K7 从永久损失降级为暂时挫折。
- 空结果从永久封闭变成带作用域的局部结论，且强制开出后继范围。
- `first_missing` 规格从自杀理由变成任务单，且规格本身可被下游修正。
- 结构事实从"找出处"改判为"去利用"。
- 姊妹问题的已验证构造从"precedent only"升为一等发现证据。
- 无法先验圈定有限宇宙的对象类第一次允许尝试。
- 长期记忆层第一次有一个**让系统变强**的通道，而不只是变慢。
- 门控第一次有出口，且 `--help` 与失败输出第一次说明合法取值。
- **prompt 总字数下降**（13 份角色文件各删一半，换来 2 份共享的分区规则）。
- 审稿能力原样保留。

### 4.2 代价与风险

| 风险 | 缓解 |
|---|---|
| 发现区产生大量似是而非的东西 | 只写工作台；单一接口进入验收区；验收区一字未改 |
| PSLQ 类过拟合 | 由预先声明 + 未触碰留出深度 + 精确残差承担（§C.3），比原机制更强也更便宜 |
| `open` 路线堆积成噪声 | Synthesizer 按两条判据排序，噪声自然沉底；不设复活机制就不会有复活风暴 |
| 缺口规格写错或写太严 | `consumed_at` 把跑题暴露在派单前；承接方可绕过多余条件并记回（§D.1/§D.2） |
| `acceptance` 退化成同义反复 | 由消费方写，或留空由 Verifier 判定（§D.2） |
| Explorer 拿到 REPL 后跑飞 | skill 在写实验前约束规模；「被终止 ≠ 数学结论」写进 skill；输出字节上限留在执行层。**明确不设资源硬限制**——理由与代价见 §G.2 |
| 发现 mode 的 Verifier 误伤路线 | 发现 mode 下不出 `PASS`/`FAIL`，输出不构成状态转移（§A.2） |
| 同侪迁移引入未经审计的参数 | §H.2：迁移单元是机制，参数必须在本问题重新导出，且仍走完整验收 |
| `--waive` 被滥用成绕过门控 | 豁免必须写理由、进产物、在 `gate stop` 汇总 |
| 双 mode 使 prompt 变长 | 分区规则共享两份 `prompts/references/` 文件；角色文件同时被蒸馏 |
| 发现 mode 的疑点被拆成多轮 | 覆盖要全、深度限一行；能就地改的派回原 owner 一次改完（§A.2） |
| 两个 harness 规范漂移 | 分区规则只有一份，两套 harness 共用；新增文本逐字相同 |

### 4.3 明确不做的事

- 不放宽 Orchestrator 的数学权限（invariant 1 不变）。
- 不降低任何证明标准；验收区一字不改。
- 不让数值符合、整数关系检验、有限检查或同侪迁移提升为证明。
- 不改验收 mode 下 Verifier 的 fresh/stateless 性质。
- **不新增 agent 种类**（Prospector 提案已撤销）。
- **不新增 facade**（`discovery.py` 提案已撤销，facade 保持五个，ADR 0020 不需修订）。
- **不新增每轮必跑的命令**——它会进入每次派发的读入量，而读入量是延迟主因。
- 不制度化「丢弃记忆重跑」。
- 不删除任何现有禁令的**内容**，只改变它的**作用域与生命周期**。
- 不把数学解题通法写进 prompt；该 skill 本轮**搁置**（§G.3）。
- **不设任何 REPL 资源硬限制**（§G.2）。
- **不在本 ADR 设计规则退休 / 自演化机制**（§S，另行处理）。

---

## 5. 验收

### 5.1 回归用例（可机械核对）

| 用例 | 来源 | 要求 |
|---|---|---|
| **A** 禁令作用域 | 2_5 / K3 | 给定一个已冻结 PSLQ 盒子及其空结果，必须 (a) 记录 `scope`；(b) 开出后继范围；(c) 不产生族级禁令；(d) 人类补充 `log 2` 时不被旧冻结阻挡 |
| **B** first_missing 派单 | 3_1 / K4 | 自报 `first_missing` 的路线必须生成任务单（含 `consumed_at`），状态保持 `open`，**不得** `rejected` |
| **C** 离散枚举 | 2_5 / K5 | 排列歧义升级 Human 前必须枚举全部，或写明不可枚举的理由 |
| **D** 结构事实路由 | 2_5+2_7 / K2 | 含精确核/秩/对偶的产物，其后续 owner 不得为 Searcher；检索为负不得改变路线状态 |
| **E** 声明范围内无结果 | 2_7 / K6 | `FINITE_UNIVERSE_NOT_DERIVED` 必须落 `NO_RESULT_IN_DECLARED_SCOPE` + 一个已声明的任意盒子提案，路线保持 `open` |
| **F** 同侪迁移 | 2_7 / K7 | 姊妹问题的 fresh-PASS 构造必须可作为一等发现证据；迁移单元为机制而非参数 |
| **G** 回归读取 | 全部 / K8 | `open` 的历史分支必须与新候选同等参与 Synthesizer 排序，不因出现过而减分 |
| **H** 状态收窄 | 全部 / K1 | 无反例、无验收 mode Verifier FAIL 的失败不得置为 `rejected`；`blocked` 必须写明所等条件 |
| **I** 排序产出维度 | Q6 / K9 | 连续两次 rank-1 为非产出分支时必须触发 ADR 0024 §D-bis 的探索预算判定 |
| **J** 发现 mode 不越权 | §A.2 | 发现 mode 下任何 agent 的输出都不得引起状态转移；Verifier 在发现 mode 不得输出 `PASS`/`FAIL` |
| **K** 规格可被绕过 | §D.1 | 承接方交付的对象若不满足规格某一条但填上了 `consumed_at` 的洞，必须判为完成 |
| **L** 记账诚实 | 2_2 / Q.2 | STATUS 中声称"保留"的产物必须存在且可重建 |
| **M** 外部披露 | 3_1 / Q.3 | 外部供给的数学内容必须出现在 Writer 产物中 |
| **N** 门控出口 | §P.1 | 每个门控失败必须输出合法取值与最小修复；`--waive` 必须记录理由并进汇总；`--help` 不含示范产物 |

### 5.2 范围声明

用例 A–N 可由 `gate.py discovery` 的 schema 检查加字段级断言机械核对。
**「harness 能否自主做出 2_5 / 3_2」不在本 ADR 的验收范围内**——
那需要运行级回归题集，见 §6 R1。

---

## 6. 待决问题

前两轮的八条待决问题已全部关闭：Prospector 预算与对接（撤销该 agent）、
`revisit_when` 默认值（撤销该机制）、FL-Prover 平移（暂不）、
丢弃记忆重跑（不做）、`structural-datum-unused` 滥用风险（该分类已撤销）、
facade 数量（不需要第六个）。剩余两条：

**R1 — 运行级回归题集。** 不急（人类判断）。记一句到期条件：
**一旦开始让系统自己改 harness，冻结回归题集从「可选」变成「前置条件」**——
没有它，无法区分「变强了」和「在新题上变强、在旧题上变弱了」，
文献（`../MechMath-agent-team/docs/research/2026-08-self-evolving-harness-survey.md` §7.3）
对此有实测。§5.1 的十四个用例可作为它的前十四条。
它与 §S 属于同一个后续部分。

**R2 — FL-Prover 与 NL-Prover 的合并。** 暂不平移，将来可能合并。
Lean 是一个更强、也更难实现的验证。两点供合并时用，本 ADR 不处理：

1. **本 ADR 的核心定义在两边答案不同。** NL 侧「Verifier FAIL 即 `rejected`」；
   但 FL 侧**「Lean 编译不过」绝不能是 `rejected`**——它多数时候只是写法问题，
   而不是数学错误。若照搬本 ADR，FL 侧会把绝大多数正确路线判成硬墙。
   FL 侧的 `rejected` 应当只对应「Lean 证明了否定命题」或「找到反例」，
   编译失败落 `open`。
2. **合并的收益主要在发现侧。** Lean 的失败信息是**极精确的 `first_missing` 规格来源**
   ——精确到哪一个洞、需要什么类型的项，比 NL 侧自报的规格质量高一个量级，
   正好喂给 §D 的任务单机制。如果要做，这是最值得先做的接口。

---

## 7. 实现清单

### 7.0 可实施范围（ADR 0024 暂缓）

人类决定：**先实施 0023 中可独立完成的部分，0024 暂不处理。**
按此切分，31 步里 **29 步可立即实施，2 步被 0024 阻塞**：

| 阻塞项 | 依赖 | 后果 |
|---|---|---|
| §C.2 的 `family` 字段 | ADR 0024 §F1 | 「关闭一个盒子，不关闭它所属的族」只剩 `scope` 一半——盒子级可查，族级不可查 |
| §E 的「同族第 3 次不得换族」硬约束 | ADR 0024 §F3（同一条，合并计） | **K10 在可实施范围内没有解药**，见下 |

**必须说清的一个后果**：K10（危险率塌陷）的止血**全部**落在这两条上。
§B 的 `rejected` 收窄能让那十五次派发不再各留一条永久禁令，
但**它不会让循环停下来**——循环的动力是「换个族再来一次」，
而关掉这个出口的正是被阻塞的那条硬约束。

所以在 0024 处理之前，**3_1 那种连续十五次换族、约 10 小时的极限环仍然会发生**。
其余九种击杀机制（K1–K9）的决议不受影响，可完整实施。

（其余条款间无跨 ADR 依赖，均可独立完成。）

### 7.1 步骤（尚未执行）

**第一批：prompt 拆分与蒸馏**（§A.1，最大的一块）

1. 新增 `prompts/references/discovery-mode.md` 与 `certification-mode.md`
   （两份共享分区规则；含「发现 mode 输出不构成状态转移」一条，§A.2）
2. 13 份 `prompts/<agent>.md` 蒸馏为纯角色定义；每份声明默认 mode 并引用分区规则
3. `subagent-dispatch-cookbook.md` 增 mode 与「是否续跑」两个派单参数（§A.2、§M）

**第二批：删分类**（§T，先定分类再改脚本）

4. 删 `regulator.md:25-32` 与 `orchestration.md:122-129` 的六类失败表（两处同批，SSOT）
5. 删 `synthesizer.md` 八维度，换 §K 两条判据；删 `Repeats history`
6. 删 `explorer.md` 输出 schema 的 `Verifier checkability`
7. 删 `regulator.md` `## Escalation` 的四个例子，改目标句（§E）
   —— 其中「同族第 3 次」硬约束**暂缓**（阻塞于 ADR 0024 §F3，见 §7.0）
8. `_memory/experience.py:32` 删 `CARD_TYPES` 的 `"obstruction"`

**第三批：状态机与记忆**

9. `branch-queue-cookbook.md`：六状态表（§B.1）；`rejected` 收窄；
   删 `superseded` 与游离的 `inconclusive`
10. `explorer.md:29`、`synthesizer.md:24/39` 四行消费侧同步（§B.2）
11. `orchestrator-cookbook.md`、`regulator.md`、`verifier.md` 三处「谁能置入状态」
    的约束同步（§B.1）
12. `_memory/experience.py:31`：`heuristic-threshold` → `transferable-idea`；
    同步 `cardlint.py` 报错文案（既有 27 张卡不受影响，§H.3）
13. `.agents/skills/memory-routing/SKILL.md`：触发条件加成功；两张示例卡；
    字段改中性；`scope` 收为 `class-level`/`this-problem-only`（§L.1）
14. `_memory/experience.py`：`render-longterm` 默认只渲染 `class-level`
15. `memory.md` / `CLAUDE.md` / `AGENTS.md`：删 "negative-constraint" 措辞，逐字同步
16. `AGENTS.md` / `CLAUDE.md`：Explorer 输入默认不加载 `memory.md`（§N）

**第四批：门控**

17. 新增 `cli_tools/_gate/discovery.py`，`gate.py` 注册 `discovery` 子命令（§P）
18. 所有 gate 报错增加「合法取值 + 最小修复」输出（§P.1 第 1 条）
19. 所有 gate 子命令的 `--help` 输出三段：检查什么、合法取值、失败怎么修，
    **不含示范产物**（§P.1）
20. 所有 gate 增加 `--waive "<理由>"`；`gate stop` 汇总豁免（§P.1 第 2 条）
21. 扫自由散文的两处模式匹配降级为警告；终局字段与结构性检查保留阻断（§P.1 第 3 条）
22. `_gate/citation_audit.py`：增外部来源披露检查（§Q.3）
23. `_gate/completion.py`：增 STATUS "保留"声明的存在性检查（§Q.2）

**第五批：其他**

24. `prompts/searcher.md`：检索为负不得关闭数学路线（§F）
25. `prompts/code_executor.md`：增 `DISCOVERY_TRIAGE` 模式（§O）；空结果必须命名下一个范围
26. `prompts/explorer.md`：增廉价 REPL 能力（§G.2）
27. 新增资源 skill：触发条件「即将执行代码」；含「被外部终止是资源问题、
    不是数学结论，不得据此关闭路线」一条（§G.2）
28. ~~**执行环境**：REPL 输出字节上限~~ —— **本仓库无此层，无需改动**。
    宿主 CLI 的执行工具本身就截断输出；可实施的部分是 `compute-budget` skill
    里的「大块落盘、只打印摘要」。不为一个不存在的层发明机制
29. 「遇到缺口即放弃」条款 —— **仓库内不存在此类条款**（`Decision-8` 是某次运行
    自定的约定，不是仓库文件）。改为补上正面规则：`stop-conditions.md` 增
    「缺口是工单不是出口」，`discovery-mode.md` §7 已含同一条
30. `tests/harness_tools/test_discovery_gate.py` 覆盖 §5.1 用例 A–N
31. `docs/adrs/README.md` 索引更新（已完成）

**已搁置**：数学通法 skill（§G.3）。

**不做**：新增 agent、新增 facade、新增每轮必跑命令、新增记忆层、
在本 ADR 设计规则退休机制。

---

## 8. 修订记录

### 8.1 第二轮取证

**新增**：K9（排序规则无产出维度，不动点是「永远审计」）、
K10（危险率塌陷，十五次派发只换名字）。

**被证据修正的：**

- **「Regulator 的禁令棘轮是主要的复利项」——错。** 禁令是**线性**增长
  （每决策约 7 行 / 700 字符，九个运行无一例外）。它是恒定速率项；
  **它的效果（可行动空间单调收窄）才是致命的，成本不是。**
  超线性的是 `STATUS.md`（n^1.5–2）。
- **「从犯错到纠错的时间随运行增长」——证伪。** 钉在约 40 分钟，全程不变。
  这把复利的位置从"单次成本"移到了"期望次数"。
- **「证据引用完整性随运行衰变」——证伪。** 悬空率 0–4%，不随运行位置增长。

### 8.2 第一轮人类审阅（50 条批注）

**被推翻的初稿主要设计（四项）：**

1. 新增 `parked` 状态 + `parked_reason` + `revisit_when` 六触发器 + 新工具
   → 替换为一句定义修改（`rejected` 收窄）。四整节压成一条。
2. 新增 33 个标签/字段/枚举值 → 砍到 6 项。
3. `## Escalation` 再加三个纵向例子 → 改为删掉例子清单。
4. 新增 Prospector agent + 第六个 facade → 全部撤销。

**被修正的事实陈述（两处）：**「系统结构上存不下一个信念」（夸大，收回）；
§A 的接口图只有单向箭头（已补回边）。

### 8.3 第二轮人类审阅（18 条批注）

**被推翻的第一轮结论（三项）：**

1. 「按产物路径分区，12 个 agent 一个字不用改」——错。所有 agent 的 prompt
   都是按验收区语气写的。改为拆分角色与分区规则。
2. 「obligation 写多了不算错」——风险方向写反了。改为重新定义为缺口清单。
3. 「三个状态词就够」——丢信息。定为六个。

**被推广的：** `NO_CANDIDATE_IN_DECLARED_BOX` → `NO_RESULT_IN_DECLARED_SCOPE`，
适用于一切搜索——K2、K3、K6 本是同一形状，三节合并为一条。

**新增：** §P.1 门控出口（实查确认零豁免机制、22 张正则表）、
§T 分类清点、§D.2 规格防扩散。

**查明根因：** 长期层 100% 是禁令的根因全在
`.agents/skills/memory-routing/SKILL.md:63-80`，全部是牵引问题。

**定案：** 记忆默认加载仅 Explorer 关闭；所有 specialist 可续跑仅 Verifier 保持 fresh。

### 8.4 第三轮人类审阅（12 条批注）

**被推翻的第二轮结论（两项）：**

1. **「每个 agent 有固定的跨区/不跨区属性」——错**。
   全部 13 个 agent 均可被派往任一 mode；上一版那张表把「典型用法」写成
   「唯一用法」，本身就犯了核心原则 3。补一条约束替代它：
   **发现 mode 下任何 agent 的输出都不构成状态转移**，
   Verifier 在发现 mode 不出 `PASS`/`FAIL`——否则等于把最强的验收判定装进发现阶段，
   是本 ADR 要拆掉的那个病的最严重形态。
2. **「规格由提出方写全」——有问题**。`consumed_at` 自己写没问题（客观可核对），
   但 `acceptance` 自己写会退化成同义反复。改为由消费方写，或留空。

**升为原则正文的（一项）：** 「给例子会 bias 分布」写进核心原则 3。
据此审查本 ADR 自身，删掉了 §C.1 的三种后继范围来源清单。
确立一条可反复使用的分界：
**描述「做什么」的地方不举例；描述「不许做什么」的地方可以具体。**

**新增的（四项）：**

- **§D.1 规格写必要条件不写充分描述**：规格过严是一个漏掉的失效模式，
  与 `obligation` 过宽同类——都是把「我当下的设想」写成「必须满足的要求」，
  且都没有纠错机制。解法是承接方不受规格字面约束，能填上洞即视为完成。
- **§G.2 资源护栏**：给 Explorer 加 REPL 后从题外话变成前置条件。
  做成执行环境硬限制而非 skill，且**必须告知 agent 限制存在**——
  否则它会把「被杀掉」当成「计算失败」并按 K6 判死路线。
- **§P.1 门控 `--help`**：可以给字段清单与合法取值，不给示范产物。
- **§H.3 卡片改名**：`heuristic-threshold` → `transferable-idea`。
  这是 §L.1 的第五条根因——名字指向「数值阈值」，想记一个想法的人不会用它。

**定案的（三项）：** 分区规则放 `prompts/references/`（
判据：skill 是概率性触发，**必须生效的东西不能放 skill**）；
是否续跑由 Orchestrator 在派单时决定；
数学通法 skill 引入第三方而非自撰（附两条选型标准以防它收窄分布）。

**大幅缩减的（一项）：** §S 从约 40 行的机制设计砍到只保留观测事实，
规则退休与自演化机制由后续专门部分负责。

**贯穿三轮的一个模式**：`heuristic-threshold` 名字误导、
`scope` 示例写死为 `general`、`CARD_KINDS` 报错不列合法值——
**三次都是 schema 本身够用，而命名、示例或报错把路堵死了。**
修 harness 时这一类性价比最高：改几个字符串，不动任何机制。

**未受影响：** K1–K10 的全部证据。2_2 vs 2_2_old、3_1 的 `brainstorm_26`、
2_5 的核与 PSLQ 冻结、2_7 的 ₃F₂/₄F₃ 双杀，均经三轮独立复核后成立。

### 8.5 第四轮人类审阅（4 条批注）

**被推翻的第三轮结论（一项）：**

**「资源上限必须做成执行环境硬限制，不能放 skill」——判据用错了地方**。
我把「skill 能否胜任」的判据当成了「这件事重不重要」，而它其实是
**触发条件是否清晰**。分区规则不适合 skill 是因为「每次派发都要遵守」
没有触发点，不是因为它重要；而「即将跑一个程序」是这套 harness 里
最清晰的触发条件之一。§A.1 的判据已按此改写。
改为 skill 为主。（墙钟超时问题已在第五轮定案：不设，见 §8.6。）

**被补上的漏洞（一项）：**

**发现 mode 只约束了输出的地位，没约束投入的规模**。
一个照现行 `verifier.md` 跑的发现 mode Verifier 会做完整审计
（`## Global Proof Refinement` 要求读进整段运行史），
于是**付出完整验收的代价，产出一份不能改变任何状态的意见**——
而按速度取证，完整审计正是读入量最大的那一类派发。
补上四行投入约束，其中关键的一条是**「找到第一个疑点即返回」**：
快与慢的差别不在产物长度，在于要不要穷尽。
另补一句防丢失：发现 mode 的疑点写进本轮工作台，不改变状态但也不消失。

**检索结果与预期相反（一项）：**

**不存在「星星多的」数学通法 skill**。直接相关的两个候选是
`googlarz/math-skill`（6 星，MIT，按情境组织的四本 playbook）与
`agtm1199/uber-polya`（3 星，Apache 2.0，代码为主）。
星数高的（2.9 万–15 万）**全部是聚合目录，不是内容本身**。
这推翻了「不自撰」的论据——一份 6 星的 skill 没有被很多人筛过，
「质量下限更高」的保证并不存在。
（该 skill 已在第五轮定案：搁置，见 §8.6。）

**详解（一项）：** §E 的「同族第 3 次不得换族」硬约束——
机制族的含义、它对抗的极限环形状（3_1 决策 16–30，十五份决策
8.0±0.3 KB、结构逐字相同、只有名字在换，约 10 小时）、
为什么必须是规则不能是建议（现状就是建议，而模型十五次都选了同一种改变）、
以及三个部件的机械检查方式。补一条边界：
「同族第 3 次」限制的只有「跳到第 4 个族」这一个动作，族内加大投入不受限。

### 8.6 第五轮人类审阅（4 条批注）

**被推翻的第四轮结论（一项）：**

**「发现 mode 找到第一个疑点即返回」——限制加错了维度**。
我当时说「快与慢的差别在于要不要穷尽」，这句话是错的：
浅扫一遍全部与只看第一个疑点，读入量几乎相同（都只读当前候选）；
**贵的是每个疑点追到底的深度，不是覆盖。**
我把便宜的那一维限制掉了，代价是把一次能说完的事拆成 N 轮，
而按 ADR 0024 的 `T(N) = N × f(N)`，**轮数是超线性项，单轮多扫几行是线性的**
——拿超线性换线性，方向反了。
改为：**覆盖要全，深度限死在「一行说清它是什么」**。

**新增出路（一项）：**

**疑点可修就派回原 owner 就地改**，不必先进验收区。
上一版只写了「写进工作台，下游可见」，那是存档不是处理。
三条出路按成本排：能当场改掉的就地改；改不掉但知道缺什么的写成
`first_missing` 工单；说不清是不是真问题的留给验收。
第一行是最常见的一类，且不违反任何不变量。与 N35 合起来，
**原来要 N 轮的事情压回一轮**。

**人类定案（两项）：**

- **不设任何 REPL 资源硬限制**，墙钟超时删除。
  记下这条取舍：放弃的是对「失误」（意外死循环、规模估错三个数量级）的兜底；
  保住的是——**任何统一的超时值都不可能事先定对**
  （2_5 的决定性实验 0.455 秒，3_1 的有限宇宙扫描分钟级以上，差四个数量级），
  而它犯错的方向恰好是本 ADR 全篇在修的那个：把「资源不够」误当成「这条路不行」。
  超时不只是操作参数，它同时是一条**未经证据的、关于「实验该多大」的先验**。
  仅保留 REPL 输出字节上限（防拖慢，不终止计算）。
- **数学通法 skill 搁置**。搁置时已查清：**不存在「星星多的」数学通法 skill**
  ——直接候选只有 `googlarz/math-skill`（6 星）与 `agtm1199/uber-polya`（3 星），
  星数高的全是聚合目录。这同时推翻了「不自撰」的论据本身
  （6 星等于没被很多人筛过，「质量下限更高」不成立）。
  形态标准与一条可能路径已留档，日后重启不必重来。

### 8.7 第五轮定案与批准（本轮）

**批准实施。** 状态由 Proposed 改为 Accepted，
但**先实施 0023 中可独立完成的部分，ADR 0024 暂不处理**（§7.0）。
被阻塞的只有两步，且它们共同承担 K10 的止血——
**在 0024 处理之前，极限环仍会发生**，这一点已写进 §7.0，不作为遗漏处理。

**修正一处理由（结论不变）：** §N 原写「Synthesizer 需要读 `memory.md`，
因为排序需要知道哪些已被证伪」——**该理由不成立**，
`rejected` 在分支队列与 route history 里，不在 `memory.md`。
更正为：排序要判断「可行性」，而**哪一类路线在同类问题上通常走得通，
正是跨题经验该提供的东西**。

**收紧一处措辞：** REPL 输出字节上限保留，但明确**定为宽松**——
上限设在正常实验绝不会触及的量级，截断时保留头尾并注明，全量输出仍落盘可查。
它限制的只是「把整份输出塞进下游上下文」，不是计算本身。

**人类确认保留的三处机制**（此前标为「方向与总体倾向相反、待确认」）：
§E 的同族硬约束、`gate.py discovery` 与 `--waive`、§S 保留的那条边界。
三处均按原样保留，不再列为待议。

### 8.8 实施记录（本轮执行）

五批全部落地，182 项测试通过（新增 17 项）。提交按批次切分，每批一次。

**与清单的三处出入，均已在正文对应处改正：**

1. **§P.1 第 3 条「22 张模式匹配表全部降级」——按字面执行会降低证明标准。**
   正确的判别不是「它是不是正则」，而是**它扫的是什么**：扫自由散文的降级
   （2 处），扫终局声明字段的保留阻断（`FINAL_PROOF_READY` 的证明路线里出现
   「无法证明」是真矛盾，不是误判），结构性检查保留阻断。详见 §P.1 的实施修正框。
2. **第 28 步（REPL 输出上限）——本仓库没有执行环境层。**
   宿主工具自身截断输出，可实施的只有 skill 里的落盘约定。
3. **第 29 步（删除「遇到缺口即放弃」）——仓库里没有这类条款可删。**
   `Decision-8` 是运行期自定约定。改为补正面规则。

**实施中发现的、ADR 未预见的两处：**

- **`scope: general` 是既有卡片的合法值。** §L.1 第 4 条要求 `scope` 收为
  `class-level` / `this-problem-only` 并只渲染前者——直接执行会**静默丢掉 27 张
  常驻卡里的 10 张**。已把 `general` 与空值作为 `class-level` 的 legacy 别名接受。
  这正是 §T 那个模式的又一例：schema 够用，是既有取值与新枚举没对齐。
- **27 张常驻卡里有 21 张过不了仓库自己的 `card-lint`**（`statement` 超长，
  改动前后一致，与本次无关）。这是 §L 那条判断的旁证——
  卡片长到只可能在原题复现，而 lint 只检查字段齐全，不检查可迁移性。

**两步因 ADR 0024 暂缓**（§7.0）：`family` 字段、「同族第 3 次不得换族」硬约束。
K10 在当前可实施范围内仍无解药。

## 8.9 首次真实运行后的修复（2026-08-06）

在 `ESConjecture/0806/{newtesta, es-attempt}` 两个 workspace 上验证实现。
分区规则被真读（`certification-mode.md` 引用 40 次，`discovery-mode.md` 14 次），
`rejected` 收窄按设计生效（全 run 无一分支被标 `rejected`，且多处显式说明
"stays `open`, not `rejected`"），`compute-budget` 触发且「资源事实不是数学事实」
原话传播，记忆层出现 9 张 `transferable-idea` 卡。以下四处不符合预期，已修复：

1. **`gate.py discovery` 从未被调用。** §P 本节自己写着「没有门要求它跑，它就不
   跑」，而实现只把子命令注册进 `gate.py`，没有接进任何 agent 可见的文档。实际
   运行调用 citation-audit 29 次、proof-attempt 19 次、discovery **0** 次。
   已写入 `AGENTS.md`/`CLAUDE.md` 的强制 stop 前序列与门控清单。

2. **扫描路径与真实布局不符。** 门只扫 `workspace/discovery/*.md`，而没有任何
   一次运行创建过该目录；发现区产物写在 `routes/ logs/ sketch/ search/
   knowledge/ recovery/ ce/ audit/`。检查文件数 1 → 57 / 20。

3. **三处检查粒度错误，修对路径后会误报正确产物。**
   - 状态行解析要求整个单元格恰等于状态词，真实写法是
     `**done** — superseded and exceeded by ...`，解析结果为空。改为只读最后一
     格的首词（描述列里的 "open question about ..." 因此不会误命中）。
   - `blocked` 要求 until/waiting/requires 之类连接词，真实写法是
     `**blocked**: cannot run on this machine`。冒号/破折号形式同样算写明条件。
   - `Closed Off` 按行判「有 `scope:` 无 `evidence:`」，而两个字段写在同一条
     bullet 的不同行；改为按 bullet 分组。
   - `NO_RESULT_IN_DECLARED_SCOPE` 用文件级子串判断，16 个命中里 9 个是**提及**
     而非发出（"No `NO_RESULT_IN_DECLARED_SCOPE` condition arose"）。改为只认独
     占一行或以冒号收尾的发出行，字段窗口放宽到 40 行（真实 `searched:` 会写十
     几行枚举，那正是要鼓励的写法）。
   - `first_missing` 这个触发键在真实运行中出现 **0** 次——agent 写 gap spec 用
     的是 `consumed_at`/`acceptance`。改为按「gap specification」小节内逐条检查。

4. **`mode` 从未被真正派发。** 20 余份产物记录「the dispatch named no mode;
   default applies」，计数为 certification 110 : discovery 24。根因是
   `prompts/orchestration.md` **完全没有提到这个派发参数**——只有 cookbook 提到，
   而 skill 是概率加载的。已在 orchestration.md 增设专节，并写明 fallback 是给
   畸形派发用的、不是省略决策的通道。

另修 `proof_attempt.py` 的正则 `\bno (?:self-contained )?proof\b`：它与不变量 16
**强制要求写**的免责声明 "carries no proof weight" 撞车，运行记录「several agents
hit it」。这是 §8.8 第 1 条批量降级时判为「终局声明字段，保持阻断」的一条，判断
本身没错，错在没检查它撞的是一句套话。加负向前瞻排除名词短语。

`bounded negative`（61 次）、`restartable-incomplete`、`dropped` 作为第七个及以后
的状态词出现，**未处理**，由人决定是否收编。测试 182 → 204。

## 8.10 第二次真实运行（`newtesta_1`，2026-08-06）

修复后重跑。四项里三项到位：

- **门能看见运行了。** STATUS.md 解析出 7 条状态行（修复前为 0），标签发出 1 次 /
  提及 3 次被正确区分，5 处 `consumed_at` 全部合规。0 error 0 warning，且非空转。
- **`mode` 方向翻转。** discovery 10 : certification 2（上次是 24 : 110）。
- **`rejected` 依旧无一例**，且 D5「`K0 = 15` 被证伪」是**带 5 份反例证书**的，
  正是 §B 允许的那一种；D7 找不到反例就明说 "no counterexample was found，
  the 85-form family stands unrefuted"，没有把找不到写成不存在。

两处新问题，已修：

1. **`code/` 与 `writer/` 不在扫描目录里**，而本次运行三份最大的发现区产物
   （`code/q{1,2,3}_findings.md`，全部自带 `DISCOVERY — no proof weight` 抬头）
   都写在 `code/`。已加入。

2. **`discovery-mode.md` §1「Write to `discovery/`」与实际派发冲突**，运行方自己
   记了这条并要求「To be settled once, not per-artifact」。现按后者settle：
   **分区是产物的属性，不是目录的属性**。写在哪由派发/`artifact-ownership.md`
   决定，产物在开头声明 `**Mode: DISCOVERY.**`；`gate discovery` 的区隔检查改为
   解析 `proof.tex` 引用的路径、读被引文件的 mode 抬头，不再只匹配 `discovery/`
   前缀。cookbook 与 `code_executor.md` 里的同一说法一并改掉。

**未处理，留给人判断：**

- **fallback 方向。** 本次仍有 3 次派发没写 `mode`，而 CE-Hunter 两次「按
  `ce-hunter.md` 声明 certification，然后说明理由背离它」——因为派发正文自己写着
  "your output is evidence and heuristic, never proof"。角色默认值与派发意图系统性
  相反。ADR 定的是「派发指定、缺省 certification」，改默认方向需要人拍板。
- **`UNBOUNDED_LIKELY`。** D5/D7 的裁决词，`prompts/ce-hunter.md` 里没有定义，
  出现在 3 个文件含 STATUS 行。本次没造成危害（D7 明确写了"未被证伪"），但它是
  §P 那张「自造状态词」表的同类。`INVENTED_TOKENS` 没覆盖它；要覆盖需要维护一张
  合法全大写词表，成本高于收益，暂不做。
