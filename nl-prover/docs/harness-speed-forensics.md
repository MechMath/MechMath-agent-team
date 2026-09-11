# 速度与 token 取证：IMO 2026 受控对照 + Ramanujan 运行内分析

## 文档状态

- 状态：取证报告，不构成决议。ADR 0024 的证据基础
- 日期：2026-08-03
- 姊妹文档：`harness-cross-workspace-forensics.md`（管"为什么想法被杀"）；
  本文管"为什么慢、为什么贵"
- **未修改任何文件**

## 0. 方法与其边界

| 数据源 | 提供什么 | 可信度 |
|---|---|---|
| 10 份 `RUN_TIMES.md`（IMO Q1/Q2/Q3/Q6 informal + 全部 6 个 formal） | UTC 起止、分段边界 | **实测**，权威 |
| `find -printf '%T@ %s %p'`（747 个文件） | 逐产物写入时刻与大小 | **实测**；与 `RUN_TIMES` 包络在 10 例中均吻合到 0.5–5 分钟内，故在缺 `RUN_TIMES` 处（Q4/Q5 informal）可作代理 |
| `Prover/cli.log` | 每次 `lean_check` 的调用/返回，毫秒时间戳 | **实测**；两个 harness 中唯一真正的计时仪表 |
| `.claude/state/proof_tasks.json` | 形式化任务 DAG、依赖、波次计数 | **实测** |
| 114 份产物的小节级字节归属 | 仪式 vs 内容 | **实测**（小节级，非句级） |

**两条边界必须记住：**

1. **跨 workspace 的绝对时长不可比。** Ramanujan 各 workspace 未必由同一人运行。
   本文只在**运行内**用 mtime 做时序与并发分析，跨运行只比较*形状*。
   **IMO 六题是例外**——同一 harness、同一操作者、同一周，绝对时长可比。
2. **mtime 是完成事件，不是开始事件。** 因此并发是推断出来的。
   判别器见 §3.1。

**污染源与处理：**

| 问题 | 位置 | 处理 |
|---|---|---|
| 批量拷贝抹掉 mtime | 2_7：669 个文件（49%）全部盖着 `2026-07-19 00:44:02` | 排除；2_7 在 07-19 之前的时间线**不可恢复** |
| 机械索引重写 | 3_1：28 个 `queries/*/index.*` 同一秒 | 从车道归属中排除（工具，非 agent） |
| 模板文件 | 2_2、2_7 的 `KLMM/*.sty` 等 | 排除；否则 2_2 的"运行"会从 2.9h 膨胀到 860h |

**衍生量：**
- **调度簇** = 相邻写入间隔 < 90 秒的极大文件组。经验上等于一次 subagent 轮次
  （一个 agent 写它的产物 + 它的 `logs/` 条目 + 一个状态文件）。
- **归属分钟** = 每个文件占有"距上一次写入"的区间。求和恰好等于运行跨度。

---

## 1. 成本定律（**本节已按后续测量重写，见 §1.0 的订正说明**）

### 1.0 订正说明

本文初稿写的是「墙钟 ≈ 串行调度轮次数 × **5.0 ± 0.9 分钟**，r = 0.995」。
**该表述错误，必须废弃。**那个"常数"不是常数：按每次运行重新测量单次调度间隔，

| 题 | 调度数 | **平均间隔** |
|---|---:|---:|
| Q4 | 12 | **2.74 min** |
| Q1 | 14 | **2.75 min** |
| Q2 | 22 | 3.86 min |
| Q5 | 27 | 3.97 min |
| Q3 | 28 | 4.69 min |
| Q6 | 66 | 4.77 min |

**单次调度成本随累计调度数单调上升。**r = 0.995 之所以成立，只是因为在这个样本里
调度数与单次成本恰好同向变化——**5 分钟是结果，不是 harness 参数。**
任何按"每次调度 5 分钟"做的容量估算都会两头出错。

### 1.1 修正后的成本定律

> **T(N) = N × f(N)，f 递增。总时间在调度数上是超线性的。**

在 IMO 这个量级上，f 从 2.74 涨到 4.77（**1.74 倍**）。

**f 增长的机制不是写出多少，是读进多少。**证据：

- **产物字节数不预测调度延迟。**Q1 的 22,820 字节 Verifier 报告耗时 1.6 分钟；
  459 字节的 `refinement/status.md` 耗时 4.3 分钟。
  Q4 的 590 字节耗 4.7 分钟，18,583 字节耗 3.9 分钟。
  Q5 的 3,924 字节耗 **13.9 分钟**，15,110 字节耗 2.2 分钟。
- **预测延迟的是 prompt 强制的上游产物扇入。**
  `prompts/verifier.md` 的 Global Proof Refinement 模式要求读
  *"the original problem.md, research_notes, original_proof.tex, proof_refinement.md,
  proof_refined.tex, the selected decomposition and lemma statements, …
  **accepted generator proofs and prior verifier reports**"*——即把整段运行史
  塞进一个冷上下文 agent。计划级验证同样要求读**全部** `lemmas/*/statement.md`。
  Q5 的计划验证读九份 12 小节 statement → 13.9 分钟；Q4 读一份短计划 → 3.75 分钟。

**重要范围声明**：IMO 这批跑在 2026-07-17/18，早于 07-23（ADR 0020 索引采用）
与 07-26（ADR 0022）引入的**每轮必读硬前置条件**。实测证实：
六题的 `memory/` 与 `presentation/` 文件**各自只在一个时刻被写入，且在运行结束之后**
（Q1 运行 14:51–15:35，文件写于 **15:35:05**；Q6 运行至 22:12:30，文件写于 22:12:20/22:12:51），
六题**全部没有** `memory/.longterm_read.json`。

因此：**§5 的每轮必读集成本在 IMO 上是零；f(N) 的增长完全来自 prompt 的扇入规则。**
今天的 harness 会在 f(N) 之上**再叠加**每轮记账（Ramanujan 侧实测 Orchestrator
记账屏障中位 15.5 分钟、占每轮 28%），所以 **IMO 的 42–328 分钟是今天 harness 的下界，不是基准。**

### 1.2 原始调度簇统计（保留，供对照）

| 题 | NL 分钟 | 调度簇 | 分钟/簇 |
|---|---:|---:|---:|
| Q1 | 45.83 | 13 | 3.53 |
| Q4 | 41.73 | 10 | 4.17 |
| Q5 | 117.18 | 23 | 5.09 |
| Q2 | 97.33 | 18 | 5.41 |
| Q6 | 327.62 | 56 | 5.85 |
| Q3 | 145.47 | 24 | 6.06 |

各候选驱动量与 NL 时长的相关系数（n=6，只作排序证据，不作推断）：

| 驱动量 | r（全六题） | r（仅 Q1–Q5） |
|---|---:|---:|
| **调度簇数** | **0.995** | **0.975** |
| 文本总字节 | 0.986 | 0.969 |
| `logs/` 文件数 | 0.972 | 0.792 |
| recovery 决策数 | 0.949 | 0.693 |
| `routes/` 文件数 | 0.931 | 0.645 |
| brainstorm 文件数 | 0.924 | 0.083 |
| **lemma 目录数** | **0.595** | **−0.862** |
| **每 lemma 的 Gen/Ver 轮次** | −0.107 | **0.887** |

**lemma 数不预测时长**（Q1 十六条用 45.8 分钟，Q3 九条用 145.5 分钟）；
预测时长的是 lemma 被拆成了多少次独立调度。

那 5 分钟是一次 subagent 轮次的原子延迟，跨角色稳定：
Explorer 平均产物 13.7 KB、Verifier 12.9 KB、Generator 12.4 KB、
Synthesizer 11.7 KB、Regulator 10.5 KB。

**推论：任何不减少*串行*调度轮次的优化都不会移动墙钟。**

### 1.3 两个成本区制，同样的数学，7 倍差价

| 区制 | 题 | 每 lemma Gen/Ver 轮 | 分钟/lemma | 字节/lemma |
|---|---|---:|---:|---:|
| **批量** | Q1, Q4, Q6 | 1 | 2.9–3.2 | 4.0–4.8 KB |
| **逐条** | Q2, Q3, Q5 | 8–9 | 10.8–16.2 | 31–33 KB |

**订正**：初稿称「批量区制是靠降低验证深度换来的」。按内容逐份核对后，
**该判断需要收窄**（完整证据见 §11）：

| | Q1 | Q4 | Q6 | Q2 | Q3 | Q5 |
|---|---|---|---|---|---|---|
| 区制 | 批量 | 批量 | 批量 | 逐条 | 逐条 | 逐条 |
| **报告字节 / 证明字节** | **1.14** | **0.77** | **0.97** | **1.07** | **0.99** | **1.07** |
| 每节点评级步数 | 0.93 | 1.15 | 1.06 | 13.8 | 9.9 | 18.9 |
| 每节点验证字节 | 2.4 KB | — | 2.6 KB | 12.2 KB | 14.6 KB | 14.7 KB |

- **覆盖率完整。** 批量 Verifier 是**逐节点**填模板的，不是只查组装：
  Q1 的 Risk Audit 有 14 项，其中 8 项分别溯源到具体的
  `lemmas/<name>/statement.md`；Q6 有逐边依赖表带行号区间。
- **`报告/证明` 比值在两个区制上一致（0.77–1.14）**——批量 Verifier 花在
  单位证明上的笔墨与逐条相同，它没有略读。
- **每节点评级步数塌了 10–18 倍，但证明本身也塌了同样倍数**
  （批量约 1.1 KB 数学散文/节点，逐条约 7 KB）。两个区制的 Verifier 粒度
  都是"每个证明小节约 1 个评级步"。

> **准确表述：这是真实的 6–7 倍 token 节省，覆盖率完整保留；
> 损失的是每节点深度——一段而不是一页。这个深度差是否代价真实，本语料无法定论。**

两条相反方向的事实：

- **不利于批量**：全语料**唯一一次 INVALID 评级**来自逐条 Verifier
  （Q5 `lem_positive_drift` Step 6，端点 `<`/`≤` 写反，给出反例 `q_n=1/2`，
  三字节修复传播进最终 PDF）。**但基率是 27 次逐条中 1 次、3 次批量中 0 次，
  n=3 对 n=27，统计上不可区分。**
- **有利于批量**：逐条区制有一个批量不可能有的结构性风险。
  Q5 `lem_dichotomy` 发出的是**条件式 PASS**——
  *"The separate v2 proof of `lem_positive_drift` must receive a fresh PASS
  before this downstream result is adopted."*——**下游 lemma 是对着一个
  同时正在修订的依赖被验证的。**此外 Q5 那半条死掉的 `lem_defect_trap`
  通过了 lemma 级验证，直到 refinement 才被发现从未被使用；
  **一个通读整个论证的批量 Verifier 会看出那个不等式没被用到。**

---

## 2. Q6 解剖：86% 是机器

归属分钟（Q6 informal，325.1 分钟跨度）：

| 相位 | 文件 | 分钟 | % |
|---|---:|---:|---:|
| 日志（镜像 route/recovery 轮次） | 54 | 170.8 | 52.5% |
| 路线生成——审计与反例 | 14 | 54.4 | 16.7% |
| 路线生成——Explorer | 20 | 46.3 | 14.2% |
| 恢复/Regulator | 8 | 15.5 | 4.8% |
| 分解/sketch | 6 | 10.2 | 3.1% |
| lemma 生成 | 24 | 8.6 | 2.6% |
| 写作/LaTeX | 17 | 6.4 | 2.0% |
| 精化 | 5 | 6.0 | 1.9% |
| **验证** | 3 | **5.6** | **1.7%** |
| 目标读取/记忆/编排 | 8 | 0.5 | 0.2% |

**282 / 327 分钟（86%）是路线搜索与分支恢复机器。有产出的尾段是 43 分钟**——
`synthesis_8` → sketch → 16 条 lemma 陈述 → 一次 Generator → 一次 Verifier PASS →
Refiner → Writer → PDF。

**最贵的一个事实**：获胜路线 `brainstorm_20`（固定有限素数宇宙）
是一个在**第 25 分钟**就已在桌面上的想法的复活。
`synthesis_8.md` 逐字：*"it supplies the fixed finite prime universe missing from the earlier routes."*

### 2.1 机制族重复（实测）

| 机制族 | 尝试次数 | 产物 |
|---|---:|---|
| 秩/下降界 | **7** | `minimal_support_audit_1`、`barrier_audit_1`、`kernel_bound_audit_1`、`med_audit_1`、`fse_audit_1`、`hi_audit_1`、`adaptive_exchange_audit_1` — 全部被拒 |
| 有限素数宇宙/有限阻断 | **4** | `scp_audit_1`、`blocker_audit_1`、`brainstorm_8`、**`brainstorm_20`（成功）** |
| 三角/自对偶障碍 | **3** | `counterexample_1`、`counterexample_2`、`weighted_completion_audit_1` |
| 建了又废的完整 lemma DAG | **2** | 17:10 的 6 条陈述（**从未派发过 Generator**）vs 21:37 的 16 条 |

42 份 route 产物中 **14 份**属于已被尝试 3 次以上的族，
按每轮 9.3 分钟计 ≈ **130 分钟可证的重复探索**。
**第 2 段（145.6 分钟）除压力测试数据外没有任何产物进入最终证明。**

### 2.2 三段运行：中断源于 Regulator 误判，被人类三次正确推翻

| 段 | 起止 | 分钟 | 终止产物 | 原因 |
|---|---|---:|---|---|
| 1 | 16:44:53–18:39:33 | 114.7 | `regulator_decision_3.md` | **停止条件**：`RESTART_OBLIGATION`，尾标 `active_owner=NONE queued=0 target=NONE` |
| — | 缺口 | 2.2 | — | 人类重开：`route_history.md` `## 2026-07-17 — Human continuation 1` |
| 2 | 18:41:47–21:07:22 | 145.6 | `regulator_decision_7.md` | **同一停止条件**，文件自陈"no fresh Verifier packet exists"——不是 FAIL |
| 3 | 21:07:22–22:12:30 | 65.1 | `proof.pdf` | 已验证的证明 |

第三次同样的判决（`regulator_decision_4.md`，`queued=0`）在会话内被推翻，代价 12.6 分钟。
**两次中断都不是上下文耗尽，也不是 Verifier FAIL。最后一次判决之后 66 分钟就出了证明。**

**与 §2.1 同源**：Regulator 把 7 次秩/下降尝试算作 7 条不同分支。按族计数它会看到 3 个族。

---

## 3. 并发实测

### 3.1 判别器

真并发的产物落盘时间会挤在一起；串行的连续间隔近似相等。
**对照验证**：`2_2/routes/history.md` 明写两个 Generator 并行——
产物相差 **23 秒**，verdict 相差 25 秒。这就是这套 harness 里并行的样子。

### 3.2 Ramanujan：三元批全是串行

3_1 的 89 份 brainstorm 按消费它们的 Synthesis 分成 31 批：

| 指标 | 值 |
|---|---|
| 批内中位间隔 | **8.0 分钟** |
| 间隔 > 5 分钟 | 73.7% |
| 间隔 < 60 秒 | 5.3% |
| **3 元批中存在任意一对 < 60 秒的** | **0 / 22** |
| 批内两间隔之比的中位数 | 1.25（59% 的批 < 1.5） |

代表样本：`54,55,56` → 4.8, 4.8 分钟；`57,58,59` → 5.1, 4.7；`81,82,83` → 8.5, 8.4。

STATUS 自陈：*"A materially new **sequential portfolio** is open"*、
*"**Rank 34 is the sole active owner/file**"*。

5 分钟分箱统计：

| workspace | 活跃箱中"恰好 1 个角色车道" | "恰好 1 个 agent 实例" | 峰值实例 |
|---|---:|---:|---:|
| 3_1（97.0h） | **81.8%** | 71.9% | 5（1164 箱中仅一箱） |
| 2_7（62.2h 可用窗口） | **79.9%** | 65.1% | 7（747 箱中仅一箱） |
| 2_2（2.86h） | 57.7% | **30.8%** | 3 |

**有效持续并发 ≈ 1。`CLAUDE.md` 的 6 从未成为约束。**

### 3.3 IMO：波次宽度 3，波次间有硬屏障

| 题 | lemma 阶段跨度 | Σ 单条窗口 | 并行因子 | 最大并发 | 波次 |
|---|---:|---:|---:|---:|---|
| Q1 | 5.1 min | 5.1 | 1.00 | 1 | 批量 |
| Q2 | 38.8 | 53.2 | 1.37 | **3** | 3 |
| Q3 | 43.7 | 70.2 | 1.61 | **3** | 3 |
| Q4 | 4.0 | 4.0 | 1.00 | 1 | 批量 |
| Q5 | 48.5 | 81.9 | 1.69 | **3** | 4 |
| Q6 | 5.6 | 5.6 | 1.00 | 1 | 批量 |

波次间死时间（上一波最后产物 → 下一波第一产物）：
Q2 4.4+4.1+4.4+4.5 = **17.4 分钟**；Q3 = **20.2**；Q5 = **20.2**。

Q6 的 20 份 brainstorm 用了 **12 轮**（可见 2–3 的并行批与乱序编号），
但最大宽度仍是 3，**6 轮宽度为 1**。

Q6 的 5 分钟分箱形状是一长串 `2`：
**连续四小时每 5 分钟两个产物**——一个 agent 写一份 route 加它的日志。
Q1/Q4 持续 4–23 个产物每箱。

### 3.4 恢复循环的解剖（3_1）

| 阶段 | 中位 | n | 占 54.5 分钟循环 |
|---|---:|---:|---:|
| Regulator 决策 → 第 1 个 Explorer 产物 | 8.1 min | 29 | 15% |
| Explorer → Explorer ×2（**纯串行**） | **15.8** | 55 | **29%** |
| 最后一个 Explorer → Synthesis（join 屏障） | 7.8 | 30 | 14% |
| Synthesis → recovery packet（**Orchestrator 记账屏障**） | **15.5** | 29 | **28%** |
| recovery packet → Regulator 决策 | **0.0** | 31 | 0% |

**Regulator 不是瓶颈**——31/31 次 packet 与决策写在同一秒。
瓶颈是 Orchestrator 的每轮前言记账：29 次 × 15.5 分钟 ≈ **8.0 小时**。

**可拆屏障合计 = 15.8 + 15.5 = 31.3 / 54.5 = 57%。**

循环周期实测中位 **55.1 分钟**（n=31），存在下降趋势（早期 70–195，13–30 轮多为 24–55）。
**35.8 小时的发现阶段产出：99.8% DISCOVER、0% VERIFY、0% GENERATE——零次证明尝试。**

---

## 4. 形式化侧：编译不是瓶颈

来自 `cli.log`：

| 题 | 墙钟 | leancheck | 编译总计 | **占墙钟** | 失败率 | Lean 报错数 | 单次最长 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q1 | 28.3 | 15 | 3.2 min | 11% | 20% | 7 | 118 s |
| **Q2** | **147.25** | 70 | 19.1 | **13%** | **50%** | 112 | 103 s |
| **Q3** | **160.33** | 128 | 22.4 | **14%** | **48%** | 233 | 248 s |
| Q4 | 18.85 | 27 | 2.5 | 13% | 37% | 17 | 16 s |
| Q5 | 24.47 | 25 | 8.2 | 34% | 24% | 19 | 51 s |
| Q6 | 24.07 | 19 | 1.4 | 6% | 21% | 7 | 5 s |

**Q2 的 128 分钟、Q3 的 138 分钟是 agent 时间。**
`cli_tools/lean_check.py` 没有并发锁（直接 shell `lake env lean -j N`），
所以"≤3 并发"是 prompt 约定而非排队——Q2/Q3 不是在等编译。

**根因：Q4/Q5/Q6 用了 `sorry` 骨架 + 并行波次，Q2/Q3 没用。**

- Q4 `RUN_TIMES.md` 自陈：*"Locked a compiling skeleton (all defs + 13 helper lemma
  statements as `sorry`), which fixed every interface up front. Fanned out 4 parallel
  `lean-proof` subagents."* Q5：*"two waves of ≤3 concurrent Lean builds."*
  Q6：*"24 lemmas as `sorry` … 8 lean-proof subagents ran in parallel."*
- **Q2 的 `RUN_TIMES.md` 完全没有 Method 段**（461 字节，只有结果）。
- `proof_tasks.json`：**Q2 的 11 个任务全部 `dependencies: []`、`blocked_by: []`，
  却逐个串行执行**；`current_wave` 在**全部六题中都是 0**。
- mtime 佐证：Q4 的 `job_a`/`job_b` 相差 19 秒、`job_c`/`job_d` 相差 7 秒；
  Q6 的 `gA`/`gC` 相差 8 秒。
  **Q3 在 160 分钟、30 份产物里从未出现两个文件相差 < 60 秒。**
  Q2 只有一次并行爆发（73 秒内 3 个文件），随后完全串行，
  包括**一段 81 分钟只写了一个文件**——一个 agent 在零编译器反馈下写 762 行的
  `certificate_geom.lean`。
- 试探性 probe：Q3 的 `probe_c3.lean` ×14 + `c3dev.lean` ×11 + `C3.lean` ×1
  = **26 次检查落地一条 lemma**；Q2 的 `akl_noncollinear`（18 行）×10、
  `certificate_geom` ×11。Q4 最大重复 7、Q5 最大 6、Q6 最大 5（12 个文件中 8 个首检通过）。
- 空闲缺口（相邻 leancheck ≥ 6 分钟）：Q2 4 段共 **90 分钟 = 61% 墙钟**；
  Q3 6 段共 68 分钟 = 41%；**Q4、Q5 为零；Q6 一段 7 分钟。**

**Q2 超支的约 73%、Q3 的约 68% 可追溯到这一条根因。**

---

## 5. Token：重读远大于写作

### 5.1 磁盘 ≠ 上下文

| 运行 | 可入上下文（`.md`/`.tex`/`.txt`） | 二进制/数据 |
|---|---:|---:|
| 2_5 | 692 文件，**7.5 MB** | 175 文件，**63.9 MB**（占 81%） |
| 2_7 | 1040 文件，**8.8 MB** | 167 文件，**31.4 MB**（65%） |

**扫描不是 token 问题。** 26.36 MB / 124 万行的 Hermite–Padé 转储
（`2_5/routes/computation_audit_hermite_pade_1_data.json`），
消费它的审计报告只有 **7,544 字节 / 213 行**，且**报告中根本没提这个 JSON 的文件名**。
54 个 `*_data.json` 共 36.1 MB → 733 KB markdown，**50:1 压缩**。
grep 全部 `routes/*.md` 未发现任何多 MB 产物被读回上下文的证据。
**那 62 MB 是磁盘卫生问题，省不出 token。**

顺带发现的磁盘浪费：`native_wire_composition_vectors_v2/v3/v4.json` 三代并存（**18.7 MB**）；
`lemmas/.../raw_pycache_v4b/` 里 705 KB 的**已提交 `__pycache__`**；
`routes/` 下**签入的第三方库** `ore_algebra` 源码树；
一个 2.95 MB 的 manifest **在任何 markdown 中都没有被引用**。

### 5.2 每轮必读集的增长

`AGENTS.md` 的 `## Routing` 把这些定为**硬的、永不跳过**的每轮前置条件。
期末实测：

| 文件 | 2_5 | 2_7 |
|---|---:|---:|
| `memory.md` | （根目录缺失） | 9,259 |
| `memory/index.md` | 7,574 | 8,401 |
| `memory/index.json` | 18,057 | 19,974 |
| `STATUS.md` | 238,338 | 274,735 |
| `recovery/route_history.md` | — | **114,276** |
| `sketch/target_contract.md` | 8,367 | 10,395 |
| `queries/index.*` | 3,891 | 2,439 |
| `references/index.md` | 4,411 | 4,771 |
| `presentation/index.json` | **86,541** | **171,050** |
| **合计** | **367,179 B ≈ 91.8K token** | **615,300 B ≈ 153.8K token** |

首轮估计 6–10 KB ≈ 2K token。**增长 40 倍（2_5）到 70 倍（2_7）。**
期末单轮必读量已超过一个小模型的整个上下文窗口。

**全程重读总量（估计，按轮次 ≈ History 条目数、线性增长取均值 = 期末/2）：**
2_5 ≈ **1010 万 input token**；2_7 ≈ **2080 万**。
**而两个运行写出的全部文本只有 7.5 MB 和 8.8 MB——重读是写作的 5–10 倍。**

### 5.3 `STATUS.md` 的构成

| | 2_5 | 2_7 |
|---|---:|---:|
| 总计 | 238 KB / 530 行 | 275 KB / 1981 行 |
| 平均行长 | **448 字符** | 138 字符 |
| `## History`（只追加） | **134.6 KB（56.5%）**，219 条 | 125.3 KB（45.6%），270 条 |
| `## Active Branch Queue` | 85.7 KB（35.9%），224 行 | **147.3 KB（53.6%）**，353 行 |
| 队列中已关闭的行 | 80 行 / 27.3 KB（占队列 31.9%） | **303 行 / 130.4 KB（占队列 88.6%）** |
| **真正的活状态** | 18.1 KB | **2.2 KB** |

**2_7 的 `STATUS.md` 约 93% 是死重量。**

### 5.4 仪式占比

IMO 侧（小节级字节归属，114 份产物）：

| 产物类型 | n | 总字节 | **仪式** |
|---|---:|---:|---:|
| **Verifier report** | 30 | 385 KB | **62%** |
| **Verifier review packet** | 30 | 134 KB | **59%** |
| Generator proof | 22 | 272 KB | 22% |
| Explorer brainstorm | 32 | 430 KB | **3%** |

Ramanujan 侧（行级，含小节继承分类）：

| 类别 | 文件 | 行 | **仪式** |
|---|---:|---:|---:|
| `computation_audit_*.md` | 87 | 26,022 | 35.8% |
| `regulator_decision_*.md` | 58 | 15,985 | **81.9%** |
| `routes/`+`recovery/` 全体 | — | 150,135 | 38.5% |

**极端样本一** `2_7/recovery/regulator_decision_3.md`：173 行中 **143 行仪式、11 行数学**。
前 55 行是九条绝对路径的 `Inputs Read`、一段 `Classification`、
一段 `Active Dispatch`——后者的 `Context to pass:` 又把上面列过的八条路径重列一遍。

**极端样本二** `Q5/informal_proof/lemmas/lem_dichotomy/verifier/report_v1.md`
（10,464 B / 239 行）：第 1–96 行是真正的数学检查（从排中律与实序完全性证二分法的十步审计）；
第 97–239 行是 schema——`External Cross-Verification: Not run`；
五项 Preflight Risk Audit 中**三项是 `NOT APPLICABLE`**；
一段为**排中律**开具的 `Theorem Preconditions`
（"Source or derivation route: elementary classical logic"）；
`Added or Strengthened Hypotheses: NONE`；`Undischarged Assumptions: NONE`；
一个把那十步重述一遍的六行义务账本；
一段 `Finite Case and Computation Audit`，第一个字段是 `Applies: NO`，后面跟着 **8 个 `N/A`**。

**注意**：该样本的 `Dependency Preconditions` 块在做真实工作
（`lem_positive_drift` v2 的条件式 PASS 依赖它）。**浪费在于 schema 不论适用与否都全长输出。**

### 5.5 路径重复

`routes/*.md` + `recovery/*.md` 中反引号路径的出现次数：

| 2_5 | 次 | 2_7 | 次 |
|---|---:|---|---:|
| `sketch/target_contract.md` | **226** | `sketch/target_contract.md` | **177** |
| `STATUS.md` | 134 | `STATUS.md` | 148 |
| `routes/computation_audit_direct_1.md` | 75 | `memory/index.md` | 141 |

58 份 regulator 决策的非空行：13,799 → 去重后 12,062，**12.6% 逐字节重复**。

### 5.6 字节吞吐反向

| 题 | NL 分钟 | 文本总量 | **KB/分钟** |
|---|---:|---:|---:|
| Q1 | 45.8 | 359 KB | **7.83** |
| Q4 | 41.7 | **261 KB** | 6.26 |
| Q2 | 97.3 | 498 KB | 5.12 |
| Q5 | 117.2 | 511 KB | 4.36 |
| Q3 | 145.5 | 616 KB | 4.23 |
| Q6 | 327.6 | 979 KB | **2.99** |

快的运行确实也是小的运行（r=0.986），**但吞吐是反的**。
**冗长是调度次数的症状，不是独立成因**——每次调度都吐一份约 12 KB 的产物，
不论它是否推进了证明。Q6 的 `routes/` 单目录 534 KB，超过 Q4 的整次运行。

---

## 6. 失败调度与存活事故

**产物产出率很高**（从分支队列表提取声明的目标文件并在磁盘上验证）：

| 运行 | 声明目标 | 磁盘缺失 | 比率 |
|---|---:|---:|---:|
| 2_5 | 231 | **1** | 0.4% |
| 2_7 | 377 | 11（其中 8 个是 glob 模式，实缺约 3） | 0.8–2.9% |

**但 3_1 是另一回事。** `3_1/STATUS.md`（696 行）记录 **56 次**有日期的
agent 存活/调度事故——07-27 有 39 次、07-28 六次、07-29 八次、07-30 三次——
合计 **≥70 个失败的 agent 轮次**，波及 Regulator、Brainstormer、Synthesis、
SourceTheoremScout、DefinitionAuditor、Generator、Verifier、Writer。

反复出现的升级阶梯——*"bounded polling, a focused checkpoint, and a hard completion
request"*，有时再加 *"a final allowance"*——**在替换 owner 被派出之前就要花 5–17 分钟**。

**07-29 的 Synthesis 链（逐字压缩）：**
> **13:46Z** 第一个 rank-172 Synthesis owner "produced neither `routes/synthesis_33.md`
> nor its assigned log after bounded polling, two focused completion requests, and a final allowance."
> **13:52Z** "The replacement rank-172 Synthesis owner **likewise** produced neither…"
> **13:56Z** 第一个 owner 被恢复，"**again produced no assigned artifact**… interrupted
> **before another fresh owner was dispatched, preventing concurrent ownership**"
> **13:59Z** "A **third fresh** … produced neither … **execution is paused under invariant 17**."
> **14:19Z** "**The human** explicitly directed the workflow to continue."
> **14:28Z** 恢复的 owner "wrote … **only as explicit `DRAFT_SKELETON` artifacts**"——再次中断
> **14:34Z** 第六轮完成

**一份产物 48 分钟。**

其他事故类：07-28 01:10Z *"A replacement rank-171 Brainstormer **was rejected by service
capacity before acting**"*（这开启了 36 小时的缺口）；
07-30 09:55Z *"**Seven consecutive subagent launches terminated on transient
`HTTP 529 Overloaded` across six distinct fresh agents**"*（约 1 小时阻塞，靠人类指令解除）。

**两条路线被永久丢失**：`routes/brainstorm_61.md` 与 `routes/synthesis_21.md`
在磁盘上不存在（1–89 与 1–33 中仅有的两个编号缺口），
STATUS 标注 *"procedurally undecided, not mathematically rejected"*。

**28 个日志文件带重派后缀**（`_39b`、`_16c`、`_33e`、`_33f` …）。

**空档：**

| 运行 | > 15 分钟的缺口 | 合计 | 占窗口 |
|---|---:|---:|---:|
| 3_1（97.0h） | 49 | **68.9h** | **71.1%** |
| 2_7（62.2h 可用） | 49 | 41.7h | 67.0% |
| **2_2（2.86h）** | **0** | **0** | **0%** |

3_1 的三大缺口：36h17m（等人类把 workspace 贴进网页会话）、
14h23m（等外部完成包）、88.5 分钟。**扣掉两段等人，仍有 18.2h 缺口在 46.3h 的"活"运行里 = 39%。**

**注意**：2_5 与 2_7 的 agent-liveness 失败为 **0 次**；3_1 为 56 次。
这是运行间差异，不是全局常态。

**确认的硬损失**：`2_5/STATUS.md:510` —
*"Two platform-Generator attempts terminated on a harness limit (single response over
the 64000-output-token cap while emitting the artifact monolithically)"* ——
两次调度全额付费、零产物。

---

## 7. 验证与写作的真实占比

**写作不是杠杆。** 验证后尾段（Refiner + Writer + LaTeX + PDF + 记忆 + gate）
是近似常数 **13–32 分钟**，与运行长度无关：

| 题 | NL 分钟 | 尾段 | % | 其中 Refiner | 其中 Writer |
|---|---:|---:|---:|---:|---:|
| Q1 | 45.8 | 15.5 | 34% | 5.1 | 0.6 |
| Q2 | 97.3 | 27.7 | 28% | 0.0 | 1.4 |
| Q3 | 145.5 | 32.0 | 22% | 8.3 | 6.6 |
| Q4 | 41.7 | 13.4 | 32% | 4.0 | 1.8 |
| Q5 | 117.2 | 21.0 | 18% | 13.3 | 4.4 |
| Q6 | 327.6 | 17.7 | **5%** | 5.3 | 1.3 |

LaTeX/PDF 编译每次都 **< 30 秒**。**即使把写作整个删掉也只省约 15 分钟。**
尾段中较大的一块是 **Refiner 及其强制的新鲜再验证**。

**验证本身不慢。** 两种归属口径的表面冲突有统一解释：

| 口径 | 结果 |
|---|---|
| 产物归属其自身相位（IMO） | Q1 1.6 min（3.7%）、Q4 4.0（10.8%）、Q6 5.6（1.7%） |
| 时间归属其后继事件的车道（Ramanujan） | 2_2 36.2%、3_1 导入后 30.7% |

**两者都对，且都是主定律的推论**：一次 Verifier 轮次的思考+写作只要几分钟，
但要付一次完整的 5 分钟调度延迟。Q2/Q3/Q5 发了 8–9 次 Verifier 调度，
**同样的检查工作量，6–10 倍的墙钟**。

> **验证在一次成功运行中占 30–50% 是正确的稳态。该优化的是它被拆成了多少次串行调度。**

一次成功运行的完整相位分布（两个来源独立收敛）：

| 类别 | 2_2（全程成功） | 3_1（导入后） |
|---|---:|---:|
| 验证 | 36.2% | 30.7% |
| 写作/排版 | 14.8% | 11.8% |
| **合计** | **51.0%** | **51.5%** |
| 生成证明 | 25.9% | 13.7% |
| 发现/路由 | 23.1% | 18.0% |

**而 3_1 的失败发现阶段这个比例反转成 99.8% 发现 / 0% 验证，持续 35.8 小时。**
病理不是验证贵，是它一天半都没走到验证。

---

## 8. 2_2 的真实制胜法：消除重试，不是并行

**2 小时 53 分，`recovery/` 空目录，0 个 > 15 分钟的缺口，5/5 lemma 一次 PASS 得分 1。**

它全程真并发只有两处：研究扇出（2–3 个 Brainstormer + SourceTheoremScout），
以及 DAG 上唯一一对独立 lemma（Generator 相差 23 秒，Verifier 相差 25 秒）。
**并行大约只贡献 10 分钟。**

三个**上游**使能因素：

1. **第 22 分钟找到源定理。** 三个指定候选都不匹配后，
   *"**Following their Rivoal citations reached the exact published source**"*
   ——引用图遍历，而不是返回"未找到"。这在任何证明开始前就压缩了搜索空间。
2. **证明前先机械认证代数。** 15:45 的 ComputationAuditor `PASS_AUDIT`，
   于是 Generator 写的是已数值确认恒等式的证明。
   STATUS 明确记着这 *"is not a mathematical Verifier verdict"*——
   它是一道便宜的机械过滤，**作用是把重试轮数压到零，不是替代验证**。
3. **对抗性 Brainstormer 与建设性的同批跑**，
   在**计划验证**阶段就抓住了归一化陷阱（`m=3` 重标、Prop 16 的 `n^{-2}` vs Thm 1），
   而不是等到证明阶段。

---

## 9. 数据缺口（应当补上）

1. **NL 侧没有工具调用日志。** 形式化侧有 `cli.log`（毫秒级 `lean_check`），
   NL 侧没有任何等价物——本文全部 NL 计时都是 mtime 反推。
2. **Q4、Q5 的 informal 运行没有 `RUN_TIMES.md`**，而 `gate.py stop` 不检查它。
3. **2_7 在 07-19 之前的时间线因批量拷贝而永久不可恢复**（669 个文件同一时间戳）。
4. **`current_wave` 在全部六个形式化任务账本中都是 0**——波次计数器从未被使用，
   因此无法从状态文件区分"一波三个"与"三次单发"。

---

## 10. 六次 IMO 运行相互重叠（对 §1 的必要限定）

| 运行 | 窗口（UTC，mtime） | 同时在跑 |
|---|---|---|
| Q1 informal | 07-17 14:51–15:35 | **独占** |
| Q2 informal | 15:48–17:21 | 16:47 起有三个同伴 |
| Q3 informal | 16:46–19:08 | Q2/Q5/Q6 |
| Q5 informal | 16:47–18:42 | Q2/Q3/Q6 |
| Q6 informal | 16:47–22:12 | 19:08 之后独占 184 分钟 |
| Q4 informal | 07-18 00:47–01:24 | **Q2 formal + Q3 formal** |

**曾有一个假设：并发争抢解释了速度差异（估计约 112 分钟）。该假设不成立，两条反证：**

1. **Q6 自己的分箱非单调。**按当时并发数给 Q6 的调度间隔分箱：
   并发 1 → 4.48 min（n=40）、并发 2 → 5.65（n=5）、并发 3 → 6.61（n=12）、
   **并发 4 → 3.13 min（n=9，最快）**。
   若争抢是成因，四路并发应当最慢。它最快。原因是**并发度与运行阶段共线**——
   Q6 的四路窗口是它开跑的头 34 分钟，独占窗口是它后期空转的三小时。
2. **Q4 是决定性反例。**它与 Q2 formal（其中 128 分钟是 agent 时间）和
   Q3 formal（138 分钟 agent 时间）同时运行，却拿到全数据集最快的单次调度速率
   **2.74 min，与独占运行的 Q1（2.75）打平**。

**结论：运行确实重叠，但争抢不是速度差异的成因。**跨运行的绝对时长比较
仍应谨慎，但 §1 的 f(N) 关系在**运行内**成立，不受此影响。

---

## 11. 分解利用率：按内容核对（推翻 grep 结论）

初稿据 grep 得出「批量运行的 lemma DAG 被整个绕过、约 46 分钟浪费」。
**按内容逐份阅读后，该结论被推翻。**

| 题 | 节点 | 按内容确认被使用 | 真正未用 |
|---|---:|---:|---|
| Q1 | 15（+13 alt） | **15/15** | 0 |
| Q2 | 9 | 9/9 | 0 |
| Q3 | 9 | 8/9 | 1（`universal_response_epsilon`，条件回退，触发从未满足） |
| Q4 | 13 | **13/13** | 0 |
| Q5 | 9 | 8.5/9 | 0（半条 lemma 在 refinement 被删） |
| Q6 | 22（16+6 废弃） | **21/22** | 1（`finite_blocker`，**被证明为假**） |

**跨五题 79 个节点，只有 2 个未承载正面数学（2.5%），其中一个还是关键反证。**

**为什么 grep 会失败**：批量证明**就地证明而非引用**，且**按义务编号组织章节**。

- Q4：`lemmas/main_assembly/generator/proof_v1.md` 是 15 个 Step，与 13 条 lemma
  严格一一对应、按 DAG 顺序；证明自陈 *"**No dependency lemma is assumed.**
  The coordinate normalization, four-case invariant, safe-state obstruction,
  peeling construction, finite stopping, marked-angle recursion, small-angle
  finish, finite assembly, and arithmetic bridge **are all proved below**."*
- Q1：证明的收尾表把 `decomposition.md` 的 LB1–LB12 **十二行原样带回**，
  Verifier 报告第三次复述并附行号（`LB3 … Step 2, lines 138--167`）。
- Q6：证明章节**字面上叫 `W1`…`W16`**，即 sketch 义务账本的 ID。

**另外三条被推翻的子结论：**

- 「Q1 的五个节点是形式目标的逐字重述、属于记账」——**错**。
  它们就是 `Q1/problem.lean` 的五个 `sorry` 定理，**是目标本身；删掉它们就删掉了定理**。
- 「Q5 的 14 个空目录是一次重命名的废弃代」——**错**。目录时间戳显示是
  同一次 Sketcher 轮次内的三稿（17:01:43 七个 → 17:04:10 七个 → 17:07:31 最终九个），
  而 `decomposition.md` 写于 17:09:32，在三稿之后；全树 grep 那 14 个旧名字**零命中**。
  沉没成本是一次 `rmdir`。
- 「Q6 的第一版 DAG 是废弃工作」——**基本错**。6 个节点中 **5 个后来重新出现**
  （`global_enumeration`→W1+W2、`pairwise_support`→W2/W5、
  `finite_union_recognition`→W13+W14、`periodic_enumeration`→W15、`main_assembly`→W16）；
  第 6 个 `finite_blocker` 被证伪，其 `statement.md` 本身是一份反例包
  （*"the `K_n` are infinitely many distinct minimal finite transversals"*），
  成为此后七次 Regulator 决策里的永久约束——**负面知识，不是浪费**。

**内容层面真正的浪费只有一处**：Q1 的 `lemmas_alt/complete`——26 KB 完整证明 +
13 份 statement，**从未验证**，经内容比对是数学上等价的路线
（同样的 `(prod, largeCount)` 秩、同样的 `d=1`/`d>1` 分裂、同样的欧几里得不变量），
唯一区别是它引用 Mathlib 而被采用的那版从头证了 Bézout 与唯一分解——
**被采用的反而更自足**。这是全语料最大的单块浪费。
其次是逐条区制的审计样板：Q5 约 195 KB 的 generator+verifier 散文压缩成
6.5 KB 的 `proof.tex`，**约 30:1**。

> **方法论教训（适用于本仓库的一切后续审计）：
> "某产物是否被使用"不能用名称匹配判定。**
> harness 的证明风格是就地证明而非引用，Refiner 又会为人类重写一遍，
> 文章层把 lemma 内联成没有标签的展示式。必须读内容。

---

## 12. 复利机制：危险率塌陷（而非单次成本增长）

横跨 IMO（易，全解出）→ Ramanujan 已解 → Ramanujan 未解，按 mtime
（2 小时空隙切分会话，剔除归档拷贝）重建 15 次运行的工作时间线。

### 12.1 被证伪：从犯错到纠错的时间**不**增长

把每份 `regulator_decision_N` 的派发目标，与后来第一份将该文件列入
`## Do Not Retry` 的决策配对——字面意义上的「错误决定 → 其推翻」：

| workspace | 配对数 | 中位滞后 | 前 1/3 | 中 | 后 1/3 |
|---|---:|---:|---:|---:|---:|
| 3_1 | 12 | 41 min | 45 | 40 | — |
| Q6 | 4 | 41 min | 41 | — | 41 |
| 3_2 | 1 | 49 min | — | — | — |
| 2_2_old | 1 | 44 min | — | — | — |

**钉在约 40 分钟（≈8 次串行调度），全程不增长。**
版本返工（`*_v1 → *_v2`）的独立度量同向：2_7 的前/中/后中位为 67.8 / 54.2 / 57.8 分钟，平的。

### 12.2 真正复利的：单次调度的存活概率塌到零，单次成本不变

3_1 的决策 16–30——**连续十五次派发，每一次都被紧接着的下一个决策杀掉**：

```
t+20.0h  rd_16 → routes/brainstorm_48.md      54 min 后被 rd_17 禁止
t+20.9h  rd_17 → routes/brainstorm_51.md      45 min 后被 rd_18 禁止
t+21.7h  rd_18 → routes/brainstorm_54.md      24 min 后被 rd_19 禁止
t+22.1h  rd_19 → routes/brainstorm_57.md      26 min 后被 rd_20 禁止
t+22.5h  rd_20 → routes/source_theorem_11.md  80 min 后被 rd_21 禁止
…（至 rd_30）
```

这些决策**结构上完全相同**：同一分类、同样 7 条禁令、同样 5 条 reusable work、
同样 3 条排队备选、同样约 29 处路径引用、**8.0 ± 0.3 KB**。
**只有机制族的名字在变：**

> rd_17 *"…an independent **motivic-period/coaction descent** certificate for the fixed eight labelled endpoint generators."*
> rd_18 *"…a **Rademacher–Dedekind modular-cocycle/continued-fraction** certificate for the fixed eight labelled endpoint generators."*
> rd_19 *"…a **Dirichlet-character/Gauss–Bernoulli L-value** certificate for the fixed eight labelled endpoint generators."*
> rd_21 *"…a genuinely distinct **Kronecker-limit/automorphic-Green** carrier."*
> rd_22 *"…a materially distinct finite **probability-simplex/entropy chain-rule** carrier."*

**固定目标、固定单次成本、每轮加一条排除、从无穷族里抽名字——一个刻板的枚举极限环。**
3_1 有约 10 小时在里面。

> **总时间发散，不是因为每次变慢，而是因为期望需要的次数发散。**

### 12.3 最锐利的动力学判别式：每 recovery 循环的数学产出

| workspace | 结果 | 前 1/3 | 中 | 后 1/3 |
|---|---|---:|---:|---:|
| 2_6 | **解出** | 31.5 | 155.0 | **165.0** ↑ |
| 2_8 | **解出** | 6.5 | 8.5 | — ↑ |
| 2_5 | 失败 | 18.25 | 6.07 | **4.50** ↓ |
| 2_2_old | 失败 | 8.70 | 5.67 | **3.86** ↓ |
| 3_1 | 失败 | 3.35 | 1.94 | 5.29（仅在人类重开后回升） |

**在每个 workspace 上都单调。成功的运行加速冲进终局，失败的衰减 2–4 倍。**

单位时间数学产出（六等分工作时间窗）同向：
2_5 从 16.1 降到 2.0（**8 倍塌陷**）；2_6 从 28.3 升到 **73.3**；2_2 从 12.5 升到 54.0。

IMO 侧的跨难度版本（时长可比）：

| | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |
|---|---|---|---|---|---|---|
| 分钟 | 42 | 46 | 97 | 117 | 145 | 328 |
| MATH 产物 | 41 | 50 | 60 | 42 | 57 | 84 |
| **每件 MATH 产物分钟** | **1.02** | 0.92 | 1.62 | 2.79 | 2.54 | **3.90** |

**Q6 用 7.8 倍的墙钟产出 2.0 倍的内容——单位成本上升 4.2 倍。**
即使在全部解出的这一带，回报也已经是次线性的。

### 12.4 状态膨胀是超线性的，且可分解为两个相乘的因子

`STATUS.md`（每次派发都要读）：

| workspace | 工作小时 | STATUS.md | 义务行 | 分支队列行 | history 事件 |
|---|---:|---:|---:|---:|---:|
| Q1 | 0.7 | 1.2 KB | 0 | 2 | 0 |
| 2_8（解出） | 4.1 | 2.6 KB | 0 | 0 | 4 |
| 2_6（解出） | 16.5 | **3.9 KB** | 0 | 0 | 4 |
| 2_2_old | 24.3 | 54 KB | 0 | 172 | 0 |
| 2_5 | 44.7 | 232 KB | 63 | 222 | 219 |
| 2_7 | 41.6 | 268 KB | 7 | **351** | 270 |
| 3_1 | 46.3 | **325 KB** | **160** | 189 | 282 |

**3_1 的 `STATUS.md` 是 2_6 的 83 倍，而工作时间只有 2.8 倍**——log-log 斜率约 4.3。

两个独立增长的因子：

**(i) 行数**≈线性（分支队列只追加；2_7 有 351 行，且 rank 列已损坏——
第 374–377 行读作 `171, 172, 120, 120v`，它已经不是队列，只是日志）。

**(ii) 行长**也在涨，因为**每一行新记录必须把自己与之前所有行区分开**，
于是不断累加限定词、SHA 锚点与排除子句。STATUS 五分位的行字节中位数：

| workspace | q1 | q2 | q3 | q4 | q5 |
|---|---:|---:|---:|---:|---:|
| 2_7 | 232 | 354 | 292 | 509 | **686** |
| 2_5 | 279 | 229 | 338 | 451 | **475** |
| 2_2_old | 206 | 245 | 260 | 310 | **372** |
| 3_1 history | 496 | 732 | 748 | 795 | **1006** |
| Q6（短运行） | 125 | 129 | 125 | 160 | 138（**平**） |

`size ≈ O(n) × O(n^0.5–1)` → **n^1.5–2**。

**订正**：初稿把「禁令棘轮」当作主要复利项。**禁令增长是严格线性的**
——每个决策约 7 行 / 700 字符，九个运行无一例外
（Q6：5→45 / 7 个决策；3_1：4→327 / 33 个；2_5：7→180 / 28 个）。
它是恒定速率项；**它的效果（可行动空间单调收窄）才是致命的，成本不是。**

**交叉点**：3_1 的 `STATUS.md`+`route_history.md` 在 t+20h 左右达到约 100 KB，
**正是枚举极限环开始、且"每 recovery 循环数学产出"跌破 2 的位置**。
2_5 的同一交叉点在 t≈30h，MATH/h 跌破 3。

### 12.5 阈值点

| workspace | 阈值 | 之后 | 占运行 |
|---|---|---|---:|
| **2_5** | **从未跨过** | 44.7h、60 brainstorm、9 synthesis、**197 次计算审计**、28 次 Regulator 决策 → **0 条 lemma、0 份 `sketch/decomposition.md`、0 个 `proof.tex`** | 100% |
| **2_2_old** | t ≈ 15.7h | lemma 文件冻结在 8；brainstorm 从 29 爬到 52，+4 次 Regulator 决策，+38 行 STATUS 历史，零数学进展 | 35% |
| **3_1** | t ≈ 37.9h（外部导入落盘） | 见 §12.6 | 18%，且是唯一有产出的部分 |

2_5 的终末产物是纯记账。最后一份 `regulator_decision_p09_method_transfer_1.md`（41.6 KB）
开篇即写：*"Scope: routing only — this packet does no mathematical verification
and makes no claim that Ramanujan Challenge 2.5 is proved or refuted."*
最后一条 STATUS 历史：*"Stop protocol completed mechanically … `gate.py stop` → PASS."*
**运行干干净净地穿过了自己的所有门，产出一份 50 页 5101 行的 `progress_notes.pdf`，
和零条 lemma。**

### 12.6 3_1 的导入分界线

| 阶段 | 小时 | brainstorm | synthesis | regulator | source | **generator** | **verifier** | lemma 文件 | proof.tex |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 导入前 | **37.9** | 85 | 32 | 34 | 31 | **0** | **0** | **0** | 无 |
| 导入后 | **8.4** | **0** | **0** | **0** | 3 | 4 | 8 | 44 | 有 |

**37.9 小时、151 次探索派发、零次 Generator。**

### 12.7 一个无法终止的状态（设计缺陷，非运气）

`3_1/recovery/blocked_stop_2026-07-30.md`：

> `STOP_GATE_CANNOT_PASS_INFRASTRUCTURE_BLOCKED` …
> "ERROR: non-proof stop without `writer/progress_notes.tex` and `progress_notes.pdf`;
> dispatch Writer in PROGRESS_NOTES mode before stopping (ADR 0021)"

而同时：**七次连续的 subagent 启动在六个不同的新鲜 agent 上撞上 HTTP 529**
（Verifier ×3、Generator ×2、Writer ×2）。

**停止门要求一份只有 Writer 能拥有的产物；Writer 起不来；
所有权规则禁止 Orchestrator 自己写。运行既不能继续也不能停止。**
最终靠 `recovery/human_reopening_2026-07-30.md` 显式推翻 invariant 1/12/13/15/17 才解开。

### 12.8 成功与失败的结构差（prove : explore 比）

| workspace | 结果 | prove:explore 派发比 | `recovery/` 产物 | `sketch/decomposition.md` |
|---|---|---:|---:|---|
| 2_6 | **解出** | **5.0** | 10 | 有 ×3 |
| 2_2 | **解出** | **3.7** | **0** | 有 |
| Q1 | **解出** | — | **0** | 有 |
| 2_5 | 失败 | 0.34 | 30 | **从未写出** |
| 2_7 | 失败 | 0.33 | 60 | 12 |
| **Q6** | 解出但最慢 | **0.086** | 8 | 有（第二版） |
| 3_1 | 失败 | **0.08** | 71 | 1，`not-generator-ready` |

四个「每个成功都没有、每个失败都有」的特征：

1. **没有 lemma DAG。** 2_5 在 44.7 小时、2_2_old 在 24.3 小时里从未写出
   `sketch/decomposition.md`。成功的运行在前 15 分钟内就有。
   **没有 DAG，Generator 和 Verifier 永远没有入口**，运行只能在
   Brainstormer↔Synthesis↔Regulator 之间循环。
2. **派发结构倒挂**（上表）。
3. **recovery 机器启动了。** 2_2 和 Q1 的 `recovery/` 是空的；3_1 有 71 个。
4. **产物变重。** 2_6 全程把 route 产物压在 3.3 KB / 1–2 处路径引用，
   **而且越跑越快**；失败运行是 5–9 倍重、10–20 处引用。

---

## 13. 被证伪的假设清单

| 假设 | 结论 | 依据 |
|---|---|---|
| 墙钟 = 调度数 × 5 分钟常数 | **证伪** | 单次成本 2.74→4.77，随累计调度数单调上升（§1.0） |
| 产物冗长导致墙钟慢 | **证伪**（对墙钟；对 token 仍成立） | 字节数不预测延迟（§1.1） |
| 每轮记账开销导致 IMO 慢 | **证伪** | IMO 早于该规则；记账文件只在运行结束后写过一次（§1.1） |
| 并发争抢导致 IMO 速度差异 | **证伪** | Q6 分箱非单调（四路最快）；Q4 三路并发仍最快（§10） |
| 批量 lemma DAG 被丢弃、约 46 分钟浪费 | **证伪** | 79 节点中 2 个未用（§11） |
| 批量区制靠降低验证深度换便宜 | **收窄** | 覆盖完整、报告/证明比一致；低的是每节点深度（§1.3） |
| 从犯错到纠错的时间随运行增长 | **证伪** | 钉在约 40 分钟，全程不变（§12.1） |
| 禁令棘轮是主要复利项 | **证伪** | 禁令线性增长；超线性的是 `STATUS.md`（§12.4） |
| 证据引用完整性随运行衰变 | **证伪** | 悬空率 0–4%，不随运行位置增长；初测 35% 是正则伪影，已撤回 |
| 失败调度/agent 存活是主要成本 | **部分证伪** | 2_5/2_7 存活失败为 0；3_1 有 56 次——运行间差异，非全局常态 |
| `proof.tex` 未维护 | **证伪** | 是 `\input{refinement/proof_refined.tex}` 包装，符合 ADR 0008 |
