# NL-Prover 跨 workspace 取证：为什么本地 harness 达不到网页会话的发现能力

## 文档状态

- 状态：取证报告，不构成决议
- 日期：2026-08-03
- 证据来源：`/home/cyc/RamanujanChallenge/` 下 9 个 workspace 的产物（约 600 MB）
- 方法：文件计数、mtime 时序、逐字引用、md5/sha256 比对。**没有修改任何文件。**
- 关系：本文**修正**了 `harness-discovery-triage-postmortem.md` 的两条根因判断

---

## 0. 一句话结论

> 本地 harness 的探索**广度**远超网页会话（88 轮 brainstorm vs 1 轮，317 条 route vs 0 条）。
> 差距不在广度，在于：**认证阶段的纪律被装进了发现阶段**，于是每一个想法在能长大之前
> 就被合法地杀掉，而每一次击杀还会往永久禁令表里再加一行。
>
> 最刺眼的一条证据：**唯一一次本地自主完成的证明（2_2），是通过刻意丢弃
> 上一次运行积累的全部记忆达成的，用时 2 小时 53 分，Regulator 恢复决策 0 次。**

---

## 1. 记分板

| workspace | routes | logs | recovery | lemmas | 跨度 | 结果 | 证明来源 |
|---|---|---|---|---|---|---|---|
| **2_2** | 9 | 16 | **0** | 5 | 2h53m | ✅ | **本地自主** |
| 2_2_old | 195 | 73 | 33 | 1 | 4 天 | ❌ | — |
| 2_4 | 64 | 43 | 4 | 6 | 10 天 | ✅ | 未核验 |
| **2_5** | 317 | 205 | 30 | **0** | 6.5 天 | ❌ | — |
| 2_6 | 74 | 48 | 10 | 46 | 10 天 | ✅ | 未核验 |
| **2_7** | 197 | 238 | 60 | 48 | 7 天 | ❌ | **外部导入** |
| 2_8 | 36 | 1 | 5 | 6 | 8 天 | ✅ | 存疑（见 §6） |
| **3_1** | 163 | 214 | 71 | 4 | 4 天 | ✅ | **外部导入** |
| 3_2 | 50 | 28 | 6 | 11 | 11h | ❌ | — |

**努力与成功反相关。** 唯一一次确证的本地自主证明用了最少的恢复机制——零次。

| | 文件数 | 墙钟 | 计算审计 | Regulator 决策 | 结果 |
|---|---|---|---|---|---|
| `2_2` | 149 | **2h53m** | 1 | **0** | 已验证的证明 |
| `3_2` | 167 | 11h | 8 | 4 | 耗尽 |
| `2_2_old` | 558 | 4 天 | 58 | 15 | 耗尽 |
| `2_7` | 1353 | 7 天 | 36 | 30 | 证明从外部送达 |

> 恢复机制不是偶尔救场的后备；在这个样本里，**它的出现本身就是这次运行不会完成的标记。**

---

## 2. 决定性案例：2_2 vs 2_2_old（同一道题）

### 2.1 成功那次做了什么

`2_2/STATUS.md`：

> "Prior workspace policy: `/home/cyc/RamanujanChallenge/2_2_old` is **non-authoritative**
> and may be consulted only after fresh route formation, with every imported claim
> independently audited."

`2_2/routes/history.md`：

> "**Deliberately deferred reading mathematical conclusions from `2_2_old`**
> until after independent target reading and fresh route generation."

一轮 brainstorm（三个 brainstormer）、一次 synthesis、**一次**计算审计（首次即 `PASS_AUDIT`）、
五条 lemma 全部 PASS、2 小时 53 分。**零次 Regulator 恢复决策，`recovery/` 是空目录。**

### 2.2 失败那次在第 79 名就拿到了全部原料

`2_2_old/routes/computation_audit_43.md`（分支队列 rank 79 / 172，2026-07-19）
已经取回了获胜证明所用的**完全相同**的 Rivoal 源数据：

```
(P_0^R, P_1^R, P_2^R) = (-1, 4, 77/4)
(Q_0^R, Q_1^R, Q_2^R) = (1, 7, 65/2)
```

然后它冻结了一个宇宙——`"Final gauge: exactly (m!)^2"`——算出

```
| 2 | 5845/37 | 179 | 31906/111 | 306 | fail both |
```

结论：

> "the unique frozen Rivoal cubic jet fails two of the six mandatory exact initial values at m=2"
> **`ROUTE_REPAIR_NEEDED.` Pop synthesis-7 rank 1 without recurrence or asymptotic handoff.**

**然后再也没有回来过**，又跑了 93 个 rank。

### 2.3 错在哪里：一行约定

`2_2/routes/computation_audit_fresh_transform.md:82`——新运行的**第一次**审计就指出了：

> "Theorem 1(i) asserts the integrality property `n!²P_n(z), n!²Q_n(z) ∈ ℤ[z]`;
> **it does not define the recurrence solutions to be factorial-scaled.**"

以及 `:308`：

> "using the factorial-scaled sequences with the same recurrence **would be an error**."

获胜的变换是一个**相邻指标平移**：

```
(𝒯v)_m = ((m+1)(3m+4)w_m + w_{m+1}) / (8m+11)
```

**2_2_old 在 rank 79 距离证明只差一个归一化约定。**它的反应是弹出分支并把这次失败
连同校验和一起归档为不可重开的封闭结论。

### 2.4 这条相邻指标平移，在另一个 workspace 里是被明令禁止的

`2_7/recovery/regulator_decision_p07_endpoint_post_vol17_v1.md:117`：

> "**Do not scan adjacent orders, kernels, basepoints, or scalar prefactors.**"

赢下 2_2 的那个 `w_m → w_{m+1}` 平移，**字面上就是"扫描相邻阶"**。

---

## 3. 主导失败模式：过早冻结宇宙 + 把空扫描当作封闭

harness 的核心认知动作是：

```
冻结一个有限参数化宇宙 → 精确枚举 → 报告为空 → 弹出分支 → 永不重访
```

跨 workspace 的执行次数与规模：

| workspace | 该动作次数 | 代表规模 |
|---|---|---|
| 2_5 | ≥12 次大扫描 | **约 8510 万**枚举案例（单次最大 5792 万） |
| 2_7 | 约 110 次 | 3328 × 2304 水平性系统；480 × 120 极化系统；68 参数多重对数族 |
| 2_2_old | 约 60 次 | 3744 格 Laguerre 块 Hankel 账本；48 未知量 / 106996 行 Darboux 桥 |
| 3_2 | 8 次 | 1380 个 Lucas 进位状态；1133/1134 超几何可容许状态 |

**推进了证明的正面结果总数：一个**（`2_2_old/routes/computation_audit_22.md` 的
Frullani 恒等式 `I(A_m) = Q_m γ − P_m`，把问题约化为单个估计）——
而那个估计后来被证明是**错误的目标**，获胜的证明根本没用到 Frullani 行，
但它消耗掉了接下来的约 130 个分支。

2_5 的扫描还有一个额外的浪费特征：**几乎全部在第一道门就死了**
（通常是 n=0 种子匹配）。10⁷ 量级的枚举被浪费在一个本可以符号化做一次的检查下游。

最纯粹的一个标本，`2_5/STATUS.md:37`：

> `route-repair-needed | All 3888 standard-staircase labels fail rank or degree normality;`
> `a retry requires a **genuinely different** multi-index, basis, endpoint, or Padé convention`

一次 3888 元的负面扫描，其记录在案的下一步动作是「换个想法」。

---

## 4. 禁令棘轮：机制与位置

### 4.1 位置在 `prompts/regulator.md`，不在记忆系统

`prompts/regulator.md` 的输出 schema 有一段**必填**的 `## Do Not Retry`：

```markdown
## Do Not Retry
- <specific route, theorem, estimate, definition reading, or NONE>
```

三个缺陷叠在这 117 行里：

1. **没有作用域字段。** schema 要求"specific"，但没有任何结构化字段强制填写
   五元组（坐标 / 归一化 / 基底 / 高度 / 深度集）。于是 agent 写出的是——
   `2_5/recovery/regulator_decision_human_web_intuition_1.md:89`：

   > "Any closed PFQ, adjoint, integral, cone, Delannoy, Riesz, Padé, Mellin,
   > factorial–Borel, qd, Askey/Racah, split-margin, sibling-transfer, or
   > Raz–Shvets label **under a renamed convention**."

   十三个方法族按名字一次关掉，还专门加了防改名条款。形式上完全合规。

2. **没有失效条件、没有撤销机制、append-only。**
   2_5 跑了 33 次 Regulator，2_7 跑了 60 次，3_1 跑了 71 次。每次只加不减。
   可行动空间单调收缩，义务账本单调增长。2_5 终态：65 条义务 / 224 条排队分支 /
   **0 条 lemma**。

3. **`## Escalation` 只会横向扩，不会纵向深入。**

   > "If route history shows repeated failures of the same class, recommend
   > **a change in search mechanism** rather than another local revision.
   > Examples: **parallel Explorers with different diversity constraints**,
   > counterexample search, source theorem portfolio, or target-reading audit."

   四个例子全是"换方向"，一个都不是"在这条上多花力气"。
   紧接着还有一句强制加宽：

   > "**Do not collapse recovery into a single owner** when materially different
   > next branches exist."

   于是「同一类失败反复出现」——本应是"这条路值得下重注"的证据——
   被翻译成"换一批 Explorer"。

### 4.2 修正：这与长期记忆无关

`harness-discovery-triage-postmortem.md` §4 判定「长期负面记忆造成路线锚定」。
**artifacts 直接证伪。**

`memory.md` 受 git 管理。从 2_5 开跑到 2026-07-26 08:36 之前，其内容是 7 行的
`_(no long-term negative-constraint cards yet)_`，
SHA-256 `a56cb0df95c0048d8d5229083c61f642cfc25eae0b5939b70fd6ae3b05f48810`，
**与那次唯一的 PSLQ 审计报告 Inputs Read 表中记录的 hash 逐字节相同**。
跑那次 PSLQ 的 agent 读到的是一个空文件。而发现阶段的失败在 07-24/25 已经完成。

`2_2` 与 `2_2_old` 各自的 `memory/` 里**一张经验卡片都没有**——
558 个文件、172 条被拒分支、16 个 generation，向后传递了**零条**策展教训。

结论：**现象为真，器官判断错误。**锚定长在 `recovery/regulator_decision_*.md`，
不长在 `memory/`。修 `memory.md` 的作用域不会改变任何事情。

---

## 5. 「让自己去有个想法」这个不动点

`stop-conditions.md` 明令禁止把 `future Sketcher/Human after a new idea` 和
`missing intermediate construction` 作为终止状态。于是 harness **不能停在那里**，
只能循环。三个 workspace 的终态都是同一形状的队列行：

`3_2/recovery/regulator_decision_4.md:157`：

> `| 2 | NONE | NONE | NONE | A genuinely new exact primitive-residue mechanism,`
> `denominator-defect mechanism, full-gcd bypass, statement-matched theorem, or`
> `structural obstruction | All currently defined branches have been attempted |`

`2_5/STATUS.md:18`（终态第一条 open obligation）：

> "resume on … **another genuinely new definition-complete bridge datum**"

2_5 中 51 个文件含 "genuinely"，`STATUS.md` 内 17 次；2_7 中 22 次。

`2_2_old` 甚至把它形式化成了一个命名的 **"External Restart Gate"**，
记录了三次满足事件——**三次全部由人类供给**。

`3_2/recovery/regulator_decision_4.md:143` 自己把陷阱说清楚了：

> "Dispatching them now would either repeat a failed rank under a new name or
> **ask a specialist to invent the missing exact object without a falsifiable input**."

**当所有有名字的方法族都被按名字封掉之后，唯一还合法的动作就是一个没有名字的动作。**

---

## 6. 外部导入的确证

### 6.1 3_1（p09）——ChatGPT 网页会话

`3_1/references/.extracted/Proof Completion Request.pdf.txt` 首行逐字：

```
昨天 22:02
Please see this problem, here is the workspace and he
have tried a lot of attempts, please finish the proof of this problem
思考了 94m 2s
Completed proof
```

PDF 二进制中的链接注解：`/URI (https://chatgpt.com/)` ×2、两个 arXiv 链接。

**字节级证据链**：

```
diff routes/computation_audit_4_replay.py  p09_app/verify_whole_arc.py
  → 0 行差异（完全相同）
```

本地 harness 07-26 19:35 写的 rank-25 脚本，被原样送进网页会话，
改名为 `verify_whole_arc.py` 返回。所以：

- **获胜证明的第 1–3 节（分支选择、全弧、实原函数）= 本地产出**
- **第 4–9 节（Bloch 元、Borel 消没、只依赖次数的零化子、Rogers 格、区间隔离）= 外部会话**

**时间线**：07-28 01:14 本地最后一条日志 → 停摆约 36 小时 →
07-28 22:02 人类向网页提问 → 思考 94 分钟 → 07-29 01:38 下载包落盘 →
07-29 13:37 本地运行恢复。

**导入前 Generator 调度次数：0。Verifier 调度次数：0。**
88 轮 brainstorm 中 **78 轮**以 `PRECISE_REJECTION_*` 结束。

### 6.2 关键发现：赢的想法本地提过，而且被协议要求自杀

`3_1/routes/brainstorm_26.md`（Decision-8 rank 1，内部代号 `QLI-1`）
**就是**获胜策略：正规子群格 + 严格区间隔离。它正确识别了唯一缺口，
并把缺失的定理写成了精确规格 `QLI-T`：

> "construct a completely specified common extended-Bloch/regulator object Ξ …
> Prove that Ξ lies in a **target-independently specified finite-order subgroup** …
> derive exact λ₀ ∈ ℝ and Δ > 0 such that the fixed real lift satisfies ℰ ∈ λ₀ + ΔZ."
> "`QLI-T` is not asserted to exist and is not treated as sourced."

然后：

```
PRECISE_REJECTION_NO_EXECUTABLE_EXACT_REGULATOR_LATTICE_OR_INTERVAL_ISOLATION_CERTIFICATE
first_missing=QLI-1(a)-EXACT-DISCRETE-LATTICE-AND-ENDPOINT-OBJECT-BRIDGE-ROW
```

> "Decision-8 requires abandonment at this first absent lattice/object-bridge row,
> so **this packet performs no enclosure and isolates no coefficient**."

网页会话补上的恰好就是这份规格：λ₀ = 2/3、Δ = 1/(8Wₑ)，
一个**只依赖域次数**的零化子，因此天然 target-independent。
本地 Verifier 在 07-30 08:14 自己记下：

> "`routes/brainstorm_26.md` 的 first missing row **确实被供上了**，
> 它关于 mod π² 的反对意见正是有限零化子消除掉的那一条。"

原料也全在本地：`grep -li` 显示 22 个 brainstorm 提到 Bloch、73 个提到 Rogers、
9 个提到 annihilator。**harness 有全部零件和 88 次机会。**

> **差距不是知识。是 94 分钟不受打断的、面向整个问题的连续推理，
> 对 88 次逐行受限的门控——每一次都被禁止越过自己的第一个缺失行。**

### 6.3 2_7——外部投稿，且未被记录

`2_7/proof.tex` 与 `2_7/inbox/web_submission_2_7_review/submission_2_7/solution.tex`
**md5 相同**（`2d054ff1894d288740614e4e2cf9a796`），后者于 2026-07-21 04:32 从外部出现。

**修正**：初稿称其机制「在本地 1353 个文件中完全没有出现过」——**该说法错误**。
`₄F₃` 对象连同完全相同的参数，在导入前 13 小时就被本地写下并随即降级；
完整证据见 §6.3bis。未在本地出现的只有最终的组装方式
（守恒的离散 Lagrange 配对 + 矩阵 Poincaré–Perron 的收尾）。

而 `2_7/recovery/handoff_p07_endpoint_input_bound_v1.md` 仍写着：

```
ORIGINAL_P07_PROVED=NO   RUN_STATE=RESTART_OBLIGATION
NEXT_OWNER=Human_or_external_EP_X_provider
```

> "No authoritative `proof.tex` is created because the original statement is not yet proved."

**该文件的到达在任何 STATUS 条目和任何 orchestrator 日志中都没有记录。**
`2_7/memory.md:68` 至今仍断言 *"proof.tex must not be assembled"* ——现已为假。

### 6.3bis 2_7 的两次击杀——**修正：这不是"没想到"，是被杀了两次**

本文初稿把 2_7 归为「真的没想到」。**该判断错误。**逐字证据如下。

**第一次击杀：₃F₂ 路线，死于"有限宇宙"前置条件。**

`routes/recovery_brainstorm_p07_rank3_pfq_universe_v1.md` 的约束标签本身就写着：

```
`rank3-pFq-universe / formula-first / non-computational / no-height-box /
 no-gauge-fit / no-package-call / no-p-q`
```

**`non-computational`**——探索 ₃F₂ 载体是否存在的那个 agent，**被明令禁止计算**。

它的终局：

```
DISPOSITION=INCONCLUSIVE / FINITE_UNIVERSE_NOT_DERIVED
RANK3_EXECUTABLE=NO
NO_OBJECT_CLAIM=NO
P07_CLAIM=NO
```

> "**Do not execute** Synthesis Rank 3 as a Computation Auditor search.
> The finite-universe and non-arbitrary gauge-cap preconditions **were not derived**."
> "A height box, increment box, denominator template, or gauge-degree cap
> **would be arbitrary**, so there is no restartable finite Computation Auditor packet."
> "This is not … **permission to invent an adjacent route**."

该 agent 极其诚实，明确写了 `NO_OBJECT_CLAIM=NO`、
"not evidence that no `_3F_2` or Meijer–G carrier exists"、"not a p07 obstruction"。
**它没有说这条路错，它说的是这条路不能开始。**

死因不是内容，是**执行前置条件**：harness 只能在一个可先验枚举的有限冻结宇宙里动手。
一个无法先验圈定成有限清单的对象类，**根本不允许尝试**。
而拒绝做"任意选择"正是它无法开始的原因——网页会话就是随便选一个然后试。

**第二次击杀：₄F₃ —— 获胜对象本身，在导入前 13 小时被写下并降级。**

`routes/brainstorm_p07_post_cda_sibling_transfer_v1.md`（**2026-07-20 15:44**）逐字：

```
It thereby supplied the discovery identity
    M(n) = rho(n) S(n)^(-T)
for the `_4F_3` jet
    K_n = _4F_3(n+1, n+7/6, n+3/2, n+11/6;
                2n+2, 2n+2, 2n+2;  -1/(R-1)).
```

> "**This is the genuinely transferable object**: `trajectory_matrix` generated a
> target-independent contiguous matrix, while inverse transpose supplied the
> recurrence carrier."

**这与 `2_8/SOLUTION_ZH.md` 中的 ₄F₃ 参数完全相同**——上参数
`n+1, n+7/6, n+3/2, n+11/6`，下参数 `2n+2, 2n+2, 2n+2`。
也就是说，2_7 从姊妹问题 p08（= 2.8）把获胜机制整个搬了过来，
并且自己判定它是「genuinely transferable」。

**1 小时 43 分钟后**，`routes/source_theorem_p07_forced_rank3_cmf_parameterization_v1.md`
（07-20 **17:27**）把它降级：

> "| p08 verified `_4F_3`/dual-CMF construction | … | It is **a local proof for
> different literal data, not an independent theorem** deriving p07 data.
> **Transferring its concrete parameters or normalization would be unsupported.**
> | accepted local sibling artifact; **precedent only** |"

以及 `:200`：

> "the p08 `_4F_3` object is **not** a relabelled p07 `_3F_2` object."

**外部投稿于 2026-07-21 04:32 到达，用的正是 ₄F₃(1) 伴随解。距离本地写下这个对象
不到 13 小时。**

而这条 brainstorm 给出的"下一步"，是一份**给 Searcher 的文献检索请求**：

> "Locate **a primary-source theorem or author-supplied exact artifact** giving the
> specific rank-three `_3F_2`, Meijer-G, or conservative-matrix-field trajectory …
> Search first the Ramanujan Machine Group, Elyasheev Leibtag, Rotem Kalisch,
> and Alex Shvets public repositories and papers."

**「试一下类比的构造」被翻译成了「找一篇已经这么做过的论文」。**
这与 2_5 把核当成出处指纹是同一个动作（见 §9 的 K2）。

### 6.4 2_8——存疑，未核验

`2_8/SOLUTION_ZH.md`（**中文**，而 harness 全部产出为英文）核心小节标题为
「**关键发现：题目矩阵是超几何连续关系的对偶**」，把 M(n) 认成 ₄F₃ 的
contiguous relation 矩阵的转置逆，并称这一步「完全解释了题目矩阵的来源和
原先最难处理的乘法方向」。本地 route 中最早出现 `contiguous` 是 07-15，
`SOLUTION_ZH.md` 与 `proof.tex` 同为 07-18。

**证据不足以判定来源。**需要单独核验后才能写进任何结论。

---

## 7. 严谨性侧的两个发现

### 7.1 harness 的审稿能力是真的，而且很强

3_1 的 07-30 验证战役**没有橡皮图章**。三条独立 Verifier 通道跑不相交的章节区间，
两条返回 FAIL。它在那份导入证明里抓出：

- **carrier junction 处的真实逻辑断裂**——`thm:borelkernel` 对 `B(F)=ker ν` 陈述，
  却被 `prop:torsion` 用在 `B_NY(F_e)` 上，那里根本没有定义 Borel regulator；
- (7.1) 以硬编码注释而非有来源定理的形式承载；
- 缺失的 a-priori 充分性界（本地补上）；
- 三个虚报的 PASS token（`event_signs["N"]=-1` 硬编码等）；
- **Neumann–Yang Def 2.1 关系 (2) 的原始来源印刷错误**——那份导入证明是
  悄悄按正确读法替换而没有声明；本地从 arXiv LaTeX 源码（`9712224.tex`，附 md5）
  查出并写成 `rem:NY2fidelity`；
- 把导入证明的两条**假设**转成了**定理**；
- 还记录了 Orchestrator **自己**的两个计算错误。

Refiner 自述：52 页中「大约 10 页是这篇相对于它所修复的导入包的主要贡献——
诚实性装置」。

**这是当前 harness 最值钱的器官，任何改动都不应触碰它。**

### 7.2 但外部交叉验证从未成功运行过

在 2_2、2_2_old、2_7、3_2 四个 workspace 中：

- 所有 `refinement/external_{gpt,gemini}_*.json` 均为 **HTTP 402** 失败；
- 2_7 的 30+ 条 verdict 上，Gemini 返回 **HTTP 429**、OpenRouter 返回 **HTTP 402**。

**这四个 workspace 里的每一个 PASS 都是单模型自审。**
ADR 0006（外部 LLM 交叉验证）在这些运行中一次都没有生效。
文档与实际能力之间存在一处需要修补的落差。

---

## 8. 记忆层：该惰性的地方惰性，该沉默的地方禁止

- `2_2` + `2_2_old` 合计产出经验卡片 **0 张**。
- 仓库级 `memory/experience/` 现有 **27 张卡片，100% 是 `neg-do-not-*` 的过程禁令**。
  **没有一张记录数学技巧、来源或可复用的正面结果。**
  它对未来运行唯一可能的作用是增加闸门。
- 3_2 的两张卡片写得很好（带 `failure_modes` 字段自我限定），
  但它们是关于**编排**的教训——而那次运行失败在**数学**上，不在路由上。
- 结构性缺陷：负面约束层**存不下正面教训**。2_5 有一张卡片因为
  `kind: heuristic` 被 schema 拒绝了三次（07-27 / 07-28 / 07-29）。

这解释了为什么「这个对象其实是什么」这一类知识——也就是 2_8 和 3_1 里
真正起作用的那类知识——在这个系统里**无处安放**。

---

## 9. 击杀机制分类（本文的核心结论）

**先修正一个用词。**「发现了正确路径又被杀」在四个 workspace 里都成立
（2_2_old、2_5、3_1、2_7），但**不是同一种杀法**。它们长在**八个不同的器官**上，
一个补丁修不了。3_2 不属于此类（它是错配，且该题网页也未解出）。

### K1 — 冻结宇宙里的约定错误 → 弹出且永不重访

**证据**：`2_2_old/routes/computation_audit_43.md`（rank 79/172）

```
:27   - Final gauge: exactly `(m!)^2`.
:146  | 2 | 5845/37 | 179 | 31906/111 | 306 | **fail both** |
:186  **ROUTE_REPAIR_NEEDED.**  Pop synthesis-7 rank 1 without recurrence or …
```

那个 gauge 源文献从未主张过。`2_2/routes/computation_audit_fresh_transform.md:82`
一句话点破：「Theorem 1(i) 断言的是整性 `n!²P_n(z) ∈ ℤ[z]`，
**它没有把递推的解定义成阶乘缩放的**」。

**致命的不是算错，是算错之后的处置**：在冻结宇宙里，一次约定误读等价于
"整个宇宙为空"，而空宇宙的规定动作是弹出。之后跑了 93 个 rank，从未回来。

### K2 — 误路由：结构事实 / 可迁移机制被当成出处问题

**这是唯一在两个 workspace 里独立重演的机制。**

- **2_5**：`routes/brainstorm_full_seed_construction_1.md:147-153` 算出
  `A_P × A_Q = −27000(4,7,13)`、`rank A = 2`、本原右核 `κ_A = (4,7,13)ᵀ`，
  agent 自标「比单个比值 206/225 严格更强的数据」。
  它在 `STATUS.md:64` 变成了：

  ```
  | Full initial-data source fingerprint | Searcher | … | resolved |
    Public search closed negative: the challenge statement is the sole exact fingerprint hit |
  ```

  **问题最强的结构数据，成了一条 Searcher 拥有的、标题叫"初始数据来源指纹"的义务，
  结案方式是"没有文献印着它"。**

- **2_7**：把 p08 的 ₄F₃ 机制搬过来并自判为 "genuinely transferable object" 之后，
  给出的下一步是一份文献检索请求——
  "Locate **a primary-source theorem** … Search first the Ramanujan Machine Group,
  Elyasheev Leibtag, Rotem Kalisch, and Alex Shvets public repositories and papers."

**成因在 `prompts/regulator.md` 的失败分类表。** 六个类别里，
「我有一个关于目标对象的精确结构事实，不知道它从哪来」最贴近 `context-source`，
而 `context-source` 的 typical next owner 是 Searcher / Auditor / KB-Manager。
**表里没有一个类别叫"我有一个结构对象，去用它"。**

### K3 — 一次性契约 + 预先封死补救

**证据**：`2_5/recovery/regulator_decision_high_precision_pslq_1.md:111-118`

人类交出了完整的获胜配方，Regulator 冻成：变换后标量坐标 `z_K`、
基底 `{1,√2,G,√2G}`（无 log 2）、一次调用。同一份 packet 预先封死唯一补救：

> "Adding π, **logarithms**, other beta/L-values, or source constants after
> inspecting a failed relation."
> "**failure cannot trigger a basis or coordinate expansion.**"

失败后 `"The gate stopped there… PSLQ was not rerun."`
**整个运行 PSLQ 只跑过这一次。**

K3 与 K1 表面像，实质不同：K1 是错误处置了一次算错，
K3 是**在实验开始之前就禁止了失败之后唯一合理的下一步**。

### K4 — first-missing-row 中止

**证据**：`3_1/routes/brainstorm_26.md`（Decision-8 rank 1）

它是获胜策略本身，正确定位唯一缺口，并把缺失定理写成精确规格 `QLI-T`
（"a target-independently specified finite-order subgroup"），然后：

> "Decision-8 requires abandonment at this first absent lattice/object-bridge row,
> so this packet performs no enclosure and isolates no coefficient."

网页补上的正是这份规格（λ₀=2/3、Δ=1/(8Wₑ)）。
**能把自己的缺口写成规格，是发现阶段的最高产出；协议把它判成失败。**

### K5 — 有限歧义升级给人类

**证据**：`2_5/routes/proof_review_human_log2_vectors_1.md`

三个系数行、顺序未知。枚举了 **2** 种排列后：

> "Selected status: **HUMAN_CLARIFICATION**"
> "Reason: the missing information is **external provenance, not a mathematical
> calculation the harness may infer**."

正确顺序是至多二十几种里的第三种。**有限枚举被判成了认识论问题。**

### K6 — 有限宇宙前置条件失败 → 路线不得执行

**证据**：`2_7/routes/recovery_brainstorm_p07_rank3_pfq_universe_v1.md`

```
DISPOSITION=INCONCLUSIVE / FINITE_UNIVERSE_NOT_DERIVED
RANK3_EXECUTABLE=NO      NO_OBJECT_CLAIM=NO      P07_CLAIM=NO
```

> "A height box, increment box, denominator template, or gauge-degree cap
> **would be arbitrary**, so there is no restartable finite Computation Auditor packet."

**agent 明确声明这条路没有被证伪，只是不能开始。**
harness 只能在可先验枚举的有限冻结宇宙里动手；
一个无法先验圈定的对象类不允许尝试。
**拒绝做"任意选择"正是它无法开始的原因。**

同一份 brainstorm 的约束标签里还写着 **`non-computational`**——
评估 ₃F₂ 载体是否存在的 agent 被明令禁止计算。

### K7 — 同侪迁移被降级为"先例"

**证据**：`2_7/routes/source_theorem_p07_forced_rank3_cmf_parameterization_v1.md:139`

本地已验证的姊妹问题（p08 = 2.8）构造被判为不可迁移：

> "It is **a local proof for different literal data, not an independent theorem**
> deriving p07 data. **Transferring its concrete parameters or normalization
> would be unsupported.** | accepted local sibling artifact; **precedent only**"

**在发现阶段，「隔壁那道题的对象管用，试试这里的类比」是数学家最高产的一步动作。
harness 把它判成了无依据的迁移。**这是把认证阶段的"来源必须是独立定理"标准
施加到了发现阶段的类比推理上。

### K8 — 记录只用于排除，不用于回归（**放大器**）

这条回答了「都记录了路径，总该有机会重启」这个问题。**答案是：没有机会，
因为没有任何一个消费者会往回读。**

`route_history` 在整个 harness 中被消费的全部位置：

| 位置 | 用法 |
|---|---|
| `prompts/explorer.md:29` | "If the constraint conflicts with verified route history … choose the **nearest non-repeating variant**" |
| `prompts/synthesizer.md:24` | 评估维度："**overlap with route history**" |
| `prompts/synthesizer.md:39` | 候选比较表列名："**Repeats history**" |
| `prompts/regulator.md:50` | "If route history shows **repeated failures** … recommend **a change in search mechanism**" |
| `prompts/regulator.md:104` | 唯一的**写**：`## Route History Update — <entry to append>` |

**三个读者，三个都是把它当排除清单用；一个写者，append-only。**

对 `revisit / resurrect / reopen / reconsider / unblock` 的全仓库检索，
在路线语境下**零命中**。仅有的两条 "reopen" 是
`prompts/orchestration.md:155` 和 `latex-and-blueprint.md:91`，
说的是「排版失败不得重开已验证证明的数学状态」——方向恰好相反。

分支队列的状态字（`branch-queue-cookbook.md`）为
`active / queued / blocked / rejected / done / superseded`，
而更新规则只规定了**进入** `blocked`/`rejected` 的路径：

> "When the active branch fails, mark it `blocked`, `rejected`, or `inconclusive`,
> then pop the next queued branch."

**没有任何一条规则规定 `rejected → queued` 的反向转移。**

于是：K1–K7 每一种单独看都只是一次挫折；**是 K8 把每一次挫折变成了永久的。**
`2_7` 的 ₃F₂ 明写 `NO_OBJECT_CLAIM=NO`、`INCONCLUSIVE`——
一个自我声明为"未定"的结论，在这套机制下与"已否决"没有任何行为差别，
因为二者都只会让队列往前弹，都会进入 route history，
而 route history 的每一个读者都只会因此**远离**它。

### 综合

| | 2_5 | 3_1 | 2_2_old | 2_7 |
|---|---|---|---|---|
| 击杀机制 | K2 + K3 + K5 | K4 | K1 | K6 + K7 + K2 |
| 放大器 | K8 | K8 | K8 | K8 |
| 被杀时的位置 | 最早几份 brainstorm 之一 | brainstorm_26 / 89 | rank 79 / 172 | 导入前 13 小时 |
| 之后还跑了 | 全程 | 63 轮 | 93 个 rank | 直到外部投稿到达 |

两条被误用的认证纪律，一以贯之：

| | 认证阶段（正确） | 发现阶段（灾难） |
|---|---|---|
| 反过拟合冻结 | 一次定义完整的实验不得事后扩基底 | 换基底恰恰就是发现的定义 |
| 不完整即不成立 | 缺一环的证明不是证明 | 缺一环的想法是发现的常态 |
| 来源必须是独立定理 | 引用必须可追溯、非循环 | 类比迁移不需要先有论文 |
| 必须可先验枚举 | 有限检查必须穷尽且可复现 | 好想法在提出时通常圈不出有限宇宙 |

而 2_2 提供了正面对照：**把积累的封闭结论整体丢掉，1 轮 brainstorm、
1 次计算审计、5 条 lemma 全 PASS、`recovery/` 为空目录。**

> harness 的定义性承诺——*让每一步都成为有限的、精确认证的、带校验和的、
> 不可重开的决策*——是优秀的认知卫生，也是灾难性的搜索策略。
> **数学发现需要廉价的、可反复的、错误的猜测。这个 harness 让每一个猜测
> 都昂贵、不可逆、且被归档。**

---

## 10. 证据不支持的结论

- **不是算力问题。** 2_5 的决定性计算耗时 **0.455 秒 / 512 MiB**
  （`routes/computation_audit_human_anchor_correct_order_1.md:235`），
  而这次运行在别处烧掉了约 8510 万枚举案例。
- **不是长期记忆锚定**（复盘 §4）。`memory.md` 经 hash 核验在整个发现窗口内为空。
- **不是"核检查得太晚"**（复盘执行错误 #4）。核在开跑 7.3 小时后被算出，
  带正确本原生成元 `(4,7,13)`，且 agent 自己标注了「比单个比值 206/225 是
  严格更强的数据」。它被路由给了 **Searcher 去找一篇印着这个指纹的文献**，
  当成了出处问题而不是坐标。
- **不是 Discovery Triage 缺失。** harness 已经做了 triage 的工作
  （第 1 天的精确乘积到 N=256、第 1 天的核、第 2 天的高精度极限方向），
  然后把结果扔掉了，因为每一项都被锁进了一次性、不可重开的契约。
  **一个只会产出被棘轮立刻冻结的事实的新阶段，只会更快地到达同一个死胡同。**
- **2_4 / 2_6 / 2_8 的证明来源未核验。** 不应据此断言。
- **2_2 的 STATUS 有一处记账不实**：声称「先前已验证的 53 页组装保留在
  `refinement/original_proof.tex`」，而该文件是 2277 字节的 `\VerbatimInput` 包装，
  53 页 PDF 未保留。数学无误，这句记账不实。
- **署名风险**：3_1 的 `proof.tex` 中 "imported package/manuscript" 出现约 20 次
  但从未说明来源；`writer/article_candidate*.tex` 中 "imported" 出现 **0 次**。
  Writer「剥离 agent 运行历史」的指令把"核心来自外部"一并剥掉了。
  `well-written-proof.pdf` 对 E1–E4 的文献借用交代细致，唯独略过最大的一笔。

---

## 11. 按杠杆排序的改动方向

1. **禁令带作用域、会过期、可撤销。**`NO_RELATION_IN_DECLARED_BOX` 必须是带类型的
   判定，携带它关闭的确切五元组，并**强制带一个后继槽位**。
   反过拟合由「预先声明 + 未触碰的留出深度 + 精确残差」保证，
   而不是由「禁止第二次实验」保证。在 2_5 上，一个这样的后继实验
   （原始 `w_i` 坐标、基底 `[w_i, G, log2, 1]`）**成本 0.455 秒**。
2. **`first_missing` 从终止条件改为派单触发器。** 一条路线能把自己的缺口写成规格，
   是发现阶段能产出的最高价值信号，不是失败。
3. **升级阶梯增加纵向档位。** 同类失败反复 ⇒ 当前允许的唯一响应是加宽；
   必须允许"加大投入"和"把缺口规格派出去"。
4. **小的离散歧义先枚举再问人。** 在 2_5 值约 9 小时。
5. **建立 conjecture ledger**，让系统能存下一个还不严谨的信念，
   以及「这个对象其实是什么」这类正面结构性知识。
6. **加一个长程连续推理 agent，并给它 REPL。**
   现有 Explorer 的输入是 `{problem, contract, decomposition, route_history,
   diversity_constraint}`——**没有任何计算能力**；Code Executor 只审计已有声称。
   所以现有的"探索"发生在路线名称空间里，不在数学对象上。
7. **生成阶段删除 `verifier checkability` 排序**（Synthesizer 评估维度表），
   验收阶段保留。真正的突破在提出瞬间 checkability 都最低。
8. **修复外部交叉验证通道**（§7.2），否则 ADR 0006 是空文。
9. **审稿/验证器一个字不改。**（§7.1）
