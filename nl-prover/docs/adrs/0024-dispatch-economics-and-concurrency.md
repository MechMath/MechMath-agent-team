# ADR 0024 — 调度经济学：并发、重读预算与重试消除

- **状态**：**Partially Accepted（2026-08-10 修订并部分实现）**。见 §0。
- **依赖**：ADR 0023（发现区与验收区的分离）。二者**相乘**，不相加，见 §2。
- **证据**：`docs/harness-speed-forensics.md`（IMO 2026 六题受控对照 + Ramanujan 取证），
  以及 §0 引入的 **ESConjecture/0806 语料**（2026-08-06/10，比本仓库任何 ADR 都新）。
- **扩展**：ADR 0010（分层）、ADR 0020（信息架构治理）、ADR 0021（强制进度笔记）、ADR 0022（停止写回）
- **不改变**：ADR 0003（无状态 Verifier）、ADR 0005（严格性标准）、ADR 0008（`proof.tex` 单一真源）。
  **本 ADR 不减少任何一次 Verifier 检查，不降低任何证明标准。**

---

## 0. 修订记录（2026-08-10）

本 ADR 的取证建立在 IMO 2026（07-17/18）与 Ramanujan 上。此后新增了一份语料：
`ESConjecture/0806`（2026-08-06 → 08-10，五个 workspace，最长 26.6 小时），
**比本仓库任何一份 ADR 都新**，因此是唯一能代表今天 harness 的数据。
按它复核之后，本 ADR 有三类条款需要改：**已经实现的**、**指错了文件的**、
**被实测否决的**。另有一条本 ADR 完全没有覆盖的机制，它比这里任何一条杠杆都大。

### 0.1 已经成立，无需再做

**§1.5「有效持续并发 ≈ 1」已不成立。** 实测 `newtesta`：
`lem_cert_42_56`、`lem_cert_9_41`、`lem_composite_block`、`lem_es_bridge`、
`lem_positivity`、`lem_s9_exact` **六条 lemma 的 generator 产物落在同一个 10 分钟窗口内**
（2026-08-06 01:28）；`newtestb` 为 4。**声明的 6 已经被用满。**
因此 **§3.A1 / §3.A2（车道并发 3→6）已经无事可做**，§7 第 1–3 项若照做，
是在要求 harness 做它已经在做的事。

**§3.D1 的旗舰例子已经实现。** `prompts/verifier.md:601-603` 与 `:682`
已经写着 *"otherwise write `Applies: NO`"*，`:700-701` 已经允许整节省略。

### 0.2 指错了文件（照做等于空操作）

**§7 第 7 项**要求把 `presentation/index.json` 移出 `AGENTS.md` / `CLAUDE.md` Routing
的每轮必读集。**它不在那里**：`CLAUDE.md:131-141` 早已用
*"when their inputs are relevant"* 限定了 `workspace.py presentation`，
两份 orchestrator 文件里根本没有出现过 `presentation/index.json` 这个路径。
真正无界的每轮必读强制在**另一个 surface**：
`.agents/skills/nl-prover/references/orchestrator-cookbook.md:26-28`
*"read `problem.md`, `STATUS.md`, route history, latest review packets, recovery packets,
and relevant specialist artifacts."* —— 无数量上限，无字节上限。已在该文件修正。

**§7 第 8 项**要求在 `cli_tools/_memory/local.py` 给 `route_history.md` 封顶。
**`local.py` 从不写 `route_history.md`**，整个 `cli_tools/` 里都没有这个字符串。
封顶要么发生在写它的 agent 的 prompt 里，要么不存在。

**§1.6bis 把 Q1 的 `lemmas_alt/complete`（26 KB、从未验证）归因于
`prompts/refiner.md` 强制的备选扇出。** 该归因不成立：`refiner.md:145` 的
`## Candidate Routes Considered` schema 本来就是**每条路线一行**
（`1. <route name>: <why accepted/rejected>`），而且 `refiner.md` 明写
*"Write only under `sketch/`"* —— 它**不可能**写出 `lemmas_alt/`。
那 26 KB 是 Orchestrator 决定对备选 DAG 派一次完整 Generator 的结果，
不是 Refiner 的产物。**修 `refiner.md` 不会消除它。**

### 0.3 被实测否决

**Verifier report / review packet 的 schema 重复不是成本。** `verifier.md` 确实把五个小节
在 report 与 packet 里各写了一遍，而 `:625-627` 又声称 packet 是为了避免重读 report。
看上去是干净的浪费。**实测 165 对真实 report/packet：逐行完全相同的内容只占 packet 字节的 5%。**
两份产物的内容是真的不同。这是文档异味，不是成本。

**§3.D4（停止 `logs/` 镜像）收益极小。** 三个语料合计 1163 个日志文件、2.6 MB，
**均值 2.2 KB**，超过 10 KB 的只有 16 个。封顶几乎省不到东西，
而删掉这条规则会在 §3.H4 正要求新增派发日志的同时,拿掉 NL 侧唯一的派发记录。

**§3.D-bis（探索预算）治的是最新语料没有的病。** 它的判别式是
`prove : explore` 派发比 —— 失败运行 0.08–0.34，成功运行 3.7–5.0。
实测：`newtestb` = **48.0**（3 份 route 对 144 份证明产物），`newtesta` = **19.0**。
两个都远在成功区间之上。**`newtestb` 跑了 26.6 小时却完全不在枚举极限环里**：
它很早就进入 Generator 循环，然后在**一条** lemma 上重写了 11 次。
§4.1 把 D-bis 列为收益最大的 #0，那是对 Ramanujan `3_1` / `2_5` 成立的判断，
**不能外推到今天的失败模式**。§3.F（机制族账本）与 D-bis 绑定，同此。

### 0.4 本 ADR 缺失的机制：**产物重发（artifact re-emission）**

这是今天最大的一项，而本 ADR 通篇没有提到。

`newtestb/lemmas/lem_bounded_divisor_certificate`：

| 版本 | 时刻 | 大小 | 间隔 | 实质行 新增 / 删除 |
|---|---|---:|---:|---|
| `proof_v1` | 08-10 01:43 | 66.4 KB | — | — |
| `proof_v4` | 08-10 02:57 | 104.3 KB | 33.5 min | 305 / 64（共 1141） |
| `proof_v8` | 08-10 08:08 | 135.3 KB | 31.9 min | 155 / 18（共 1647） |
| `proof_v11` | 08-10 09:38 | 159.3 KB | 24.1 min | 144 / 91（共 2053） |

**一条 lemma：7.9 小时，写出 1280 KB，最终产物 159 KB。**
`proof_v10` 的实质行有 **96% 逐字重现在 `proof_v11`** 里。
产物**每一步都在长**，从不缩短。

跨三个语料，所有被修订 ≥3 次的产物族：**共写出 3.97 MB，最终版本只有 0.84 MB
—— 79% 的字节是被推翻的重写。** 且它是 Generator 特有的：
相邻 generator proof 的逐字重合率 **93–99%**，相邻 verifier report 只有 **2–33%**。
Verifier 在正当地重新推导（ADR 0003 无状态验证）；**Generator 在重打字。**

两条 prompt 造成它，都已修正：
`prompts/generator.md` 原 `:179` *"Write a revised proof to …"* 没有任何沿用前一版的指示；
原 `:218` *"If you **disagree**: keep your reasoning but add explicit clarifications"*
是一条只能**增加**的指令，连续应用十次就是棘轮 —— 66 KB → 159 KB 正是它的签名。

**这也解释了 §1.3 的自我否定。** §1.3 从 0.5–23 KB 量级的产物断言
*"产物字节数**不**预测延迟"*。在 66–160 KB 量级上该结论反转：
每版间隔随产物增大而单调上升（19 → 33 分钟）。**重发既是 token 成本也是墙钟成本。**

### 0.8 第二条本 ADR 缺失的机制：**派发固定前置**（与 §0.4 同量级）

§1.3 说 f 增长的机制是**读入量**——这是对的，但本 ADR 只统计了**工作区产物**的读入，
从未统计 **prompt 本身**的读入。后者是固定的、每次派发都付、且从不随问题变化。

实测 `newtestb`（40 次 Verifier 派发、29 次 Generator 派发）：

| | 每次派发固定读入 | 次数 | 小计 |
|---|---:|---:|---:|
| Verifier | `verifier.md` 41.9 KB + ownership 3.9 KB + mode 4.6 KB = **50.4 KB** | 40 | **2.0 MB** |
| Generator | `generator.md` 16.0 KB + ownership 3.9 KB + mode 4.6 KB = **24.5 KB** | 29 | **0.7 MB** |
| | | | **≈ 2.7 MB / 次运行** |

**这与 §0.4 的重写浪费（同一次运行 2.9 MB）几乎一样大。**

其中一块是纯死重：`verifier.md` 的 `## Verification Modes` 里有四种模式，
**一次派发只可能用一种**。已拆出三个非默认模式到
`prompts/references/verification-modes/`，由 dispatch 指定的模式按需加载。
`verifier.md` 41,913 → **33,511 B（−8.4 KB，−20%）**，
默认的 lemma proof 模式（410 B）保留在原处，因为它最常用、且拆出去反而多一次读。

**不改变任何一条检查**：搬走的 157 行逐行核对全部保留，
`Dependency Preconditions` 与 `Load-Bearing Obligation Ledger`（§4.2 明令不动）原位未动，
`gate.py review-packet` 的 lint 不受影响，linkage 的 dangling/orphan/conflict 均无变化。

**剩下的同类空间未做**：`verifier.md` 仍有 33.5 KB，其中 report / review_packet / verdict
三份 schema 约 10 KB 是每次都要写的，属于必要成本；
`prompts/references/discovery-mode.md`（7.9 KB）与 `certification-mode.md`（4.6 KB）
原本在 **13 个 prompt** 里以无标注的两条 bullet 并列列出，字面执行会两份都取。
已改为标注模式并明写 *"Read exactly one of them"* ——两份互斥且规则相反，
读错的那份会与读对的那份直接冲突。**每次派发省 4.6–7.9 KB。**

合计：一次 Verifier 派发的固定前置从 50.4 KB 降到约 **37.3 KB（−26%）**，
按 `newtestb` 的 40 次 Verifier + 29 次 Generator 计，一次运行少读 **约 0.8 MB**。

### 0.5 `STATUS.md` 的真实问题不是 `## History`，是模板已被弃用

§3.C1/C2 假设 `STATUS.md` 的膨胀来自 `## History` 与已关闭队列行。
按 `prompts/references/status-and-recovery.md` 的模板小节计数：

| workspace | 日期 | 符合模板的小节 | 小节总数 |
|---|---|---:|---:|
| `3_1` | 07 | 8 / 6 | 10 |
| `2_7` | 07 | 6 / 6 | 6 |
| `newtesta` | 08 | 3 / 6 | 11 |
| `newtest3` | 08 | 2 / 6 | 12 |
| `newtestb` | 08 | **1 / 6** | **20** |

**七月的运行遵守模板，八月的运行不遵守。** `newtestb` 的 64 KB `STATUS.md` 里是
`## REOPENED by the human`、`## Settled this cycle`、`## The run's process finding`
这类自由叙事 —— 它已经从路由文件漂移成实验笔记，而**没有任何东西检查这件事**。
所以只改模板（§7 第 5、6 项）收益有限；**该做的是让漂移可被机械发现**，
已加入 `gate.py speed`。

### 0.6 范围：§3.B 不属于本仓库

§3.B（`sorry` 骨架 + 波次）与 §7 第 4 项的目标是 `Prover/CLAUDE.md` 和
`.claude/state/proof_tasks.json` —— 它们在 `Prover/` 仓库，**不在 NL-Prover 里**
（本仓库连 `lean_check` 这个字符串都只出现在 docs 里）。
按「一个 harness 一个 binding」，它需要单独开一轮。
§4.1 把它列为收益第二大的 #1（130–160 分钟），该收益**在本仓库无法兑现**。

### 0.7 本轮实际落地

| 条款 | 状态 |
|---|---|
| §0.4 产物重发（本 ADR 新增） | ✅ `prompts/generator.md` 改为复制+编辑，禁止在证明里追加辩解 |
| §3.H2 大产物分块输出 | ✅ `prompts/generator.md` 增量写入纪律 |
| §3.C5 必读集预算 | ✅ `orchestrator-cookbook.md` + `gate.py speed` 报告字节数 |
| §3.C1/C2 `STATUS.md` 拆分 | ✅ 模板已拆；并新增漂移检查（§0.5） |
| §3.J `gate.py speed` | ✅ 本仓库可查的 7 项全部实现（A3 真判据、C1/C2、C5、F1 除外、H3、H4 存在性+完整性）。B1–B3 属 §0.6 范围外，F1/F3 随 §F 暂缓 |
| §3.A3 并发可验收判据 | ✅ 判据写入 `subagent-dispatch-cookbook.md`,并由 `gate.py speed` 事后核对。**修正**：初版用固定 10 分钟窗口,不是 ADR 写的「极差 < 单 agent 中位时长」;现按 ADR 原文实现,且**没有 `logs/dispatch.jsonl` 时报告为「未测」而不是估算**——用产物间隔估 turnaround 是循环论证：一次运行若整体就是一个批次,那些间隔本身就是批次内部的极差 |
| §7 项9 `memory.py budget` | ✅ 新增子命令,**调用 `gate.py speed` 的同一个函数**而非另写一份——两份阈值会漂移,然后两个工具对同一次运行是否超预算给出不同答案 |
| §7 项19 停止时要求计时 | ✅ `gate.py stop` 现在同时报 `RUN_TIMES.md` 与 `logs/dispatch.jsonl` 缺失（均为警告） |
| §7 项20 / §5 回归用例 | ✅ A、C、D、H 覆盖（248 个测试）。B 属范围外,F 随 §F 暂缓 |
| §3.H1 影子 owner | ✅ 第一次错过检查点即派影子到**不同目标文件**，先落盘者胜，另一份原封丢弃。**取消升级阶梯**。所有权模型不变：仍是一文件一写者 |
| §3.H1 推论：并行重试（本 ADR 新增） | ✅ 一条 lemma 两次 `NEEDS_REVISION` 之后，同时派两个 constraint 不同的 Generator 到不同文件。**验证次数不变或更少**：先落盘者送验，另一份不读、仅在前者 FAIL 时启用 |
| §3.H1 的可观测面 | ✅ `gate.py speed` 用 `dispatch.jsonl` 数「派发了但没产物」——这类失败在文件树里完全不可见，只有派发日志能看见 |
| §5 用例 D（一行否定） | ✅ `gate.py review-packet` 现在会在 `Applies: NO` 后跟 ≥3 个占位字段时**警告**（不报错：啰嗦从未让证明出错,为文字长度拦下一份正确的 packet 得不偿失） |
| §3.H3 `RUN_TIMES.md` | ✅ `gate.py stop` 现在报警（**不阻塞**：做对了其它一切的运行必须能停） |
| §0.8 派发固定前置（本 ADR 新增） | ✅ `verifier.md` 拆出三个非默认模式，每次派发少读 8.4 KB |
| §3.E1 候选失配后走一次引用图 | ✅ `prompts/searcher.md` |
| §3.E2 证明前机械认证代数 | ✅ `subagent-dispatch-cookbook.md`（**n=1 证据，见该处限定**） |
| §3.E3 对抗性 Explorer 同批 | ✅ `subagent-dispatch-cookbook.md` |
| §7 项2/项3 串行化措辞 | ✅ cookbook 步骤 2–6 改复数派发；`proof-recovery/SKILL.md:52` 的「exactly one active owner」改为按独立分支计；`branch-queue-cookbook` 明写 `active` 非单例 |
| §7 项7 `presentation/index.json` | ✅ **改在工具层**：`presentation.py` 的 review_packet/verdict 只取最新版（`newtestb` 908 KB → 334 KB，−64%）。ADR 原方案「移出必读」无效，因为 `show`/`latest` 每次都会重建它 |
| §7 项8 `route_history.md` 封顶 | ✅ **改在 `prompts/regulator.md`**（写它的地方），不是 `local.py`（从不写它） |
| §3.D1 Preflight 一行否定 | ✅ `verifier.md`：四个字段全保留，`NOT APPLICABLE` 时 `Analysis:` 限一行 |
| §3.D4 `logs/` | ✅ **不删除，改为限界**：日志是指针不是副本，~2 KB 上限 |
| §7 项17 `logs/dispatch.jsonl` | ✅ 约定写入 cookbook，**并由 `gate.py speed` 用产物数核对行数** —— 这正是 §6 Q6「Orchestrator 会漏」的答案：漏了就被查出来 |
| §5 回归用例 | ⚠️ **部分**：A、C、H 已覆盖，B、D、F 未覆盖 |
| §3.A、§3.D1 | ❌ 不做 —— 已实现（§0.1） |
| §3.D4、§3.D-bis、§3.F | ❌ 不做 —— 实测否决（§0.3）。**§3.F 于 2026-08-10 经人类确认后正式搁置**：它的前提判别式在最新语料上不成立，加一套受控词表加族计数会在仓库里留下一条没有证据支撑的规则，而这类规则只会越堆越多、越来越没人敢删 |
| §3.H1 的一处证据更正 | ADR 称 *"3_1 事后已经在用 `_b`/`_c` 命名做这件事——28 次"*。**复核为 0**：那里的多变体产物全是编号序列（`brainstorm_1..88`、`synthesis` 32 份），没有影子命名。停滞阶梯本身**证据充分**（`bounded polling` 27 次、`hard completion request` 24、`focused checkpoint` 12、`final allowance` 11，共 74 处），但"已经在自发使用影子"这条不成立 |
| §3.B | ❌ 不做 —— 范围外（§0.6） |
| §3.I Refiner 条件触发 | ⏸ 未决 —— 是质量取舍，等人类拍板（§6 Q3） |
| §3.E、§3.G、§3.H1、§3.H4 写入端 | ⏸ 未做 —— 本轮未取证 |

**没有跑任何一次真实证明运行**（成本约束）。因此上表的 ✅ 是「改动已落地并通过 235 个
离线测试」，**不是**「效果已被验证」。§0.4 的修复效果由 `gate.py speed` 在下一次真实运行后判定。

---

## 0bis. 修订记录（2026-08-25）：两条条款已被代码推翻

本节不改动 §1–§7 的任何一个字。它记录的是：2026-08-19/25 的一批改动落地之后，
本 ADR 的两条明文决定在代码里已经不成立，而记录一直读起来像是成立。

### 0bis.1 §4.2「不提高并发上限 6」曾被推翻，同日撤回；前置条件始终没有满足

**结论先写：上限现为 6，与 §4.2 一致。** 本小节保留全部经过，因为「抬了又撤」
比「一直是 6」多告诉后来者一件事：这个决定是在什么依据下被推翻的，以及那份依据
为什么不够。

**代码事实（现状）。** `cli_tools/_gate/speed.py` 为 `DECLARED_CONCURRENCY = 6`，
其 SSOT 是 `.agents/skills/nl-prover/references/orchestrator-cookbook.md`，两处由
新增的 `gate contracts` 机械核对，且 `.codex/config.toml` 的 `max_threads = 6`
与之相等。三处一致。

**经过。** 2026-08-25 该数字被提到 12，理由是 cookbook 里那句
*"The old ceiling was 6 and it was a number in this file rather than a limit of
anything"*。当日经人类决定撤回。撤回的理由不是「12 太多」，而是下面两条中的第二条：
那句话在两个平台上不成立。

**这与本 ADR 两处明文相反：**

- §4.2 明确列为不做：*"**不提高 `CLAUDE.md` 的并发上限 6。** 实测持续并发是 1，峰值 3；
  在 A1–A3 落地之前提高上限没有任何意义。"*
- §6 Q1 给了提高的**前置条件**：*"建议先按 6 落地并用 `dispatch.jsonl` 观测，再谈提高。"*

**前置条件没有满足，这是本节最重要的一条。** Q1 要求的观测数据来自
`logs/dispatch.jsonl`。复核全部语料：**6 个 workspace 共 159 行，其中带
`source: "hook"` 的为 0 行**（`connes` 63、`ESConjecture/0806/newtestc` 38、
`0815/testprime` 18、`0815/testgbcmod24_2` 24、`0815/testgbcmod24` 11、
`0806/newtestb_app` 5）。Claude 侧这个文件由 `.claude/hooks/dispatch_log.py`
的 `PreToolUse`/`PostToolUse` 钩子写——**它一次都没有触发过**；Codex 侧
（在 cookbook 按平台拆分之前）根本没有写入机制。也就是说：**上限从 6 提到 12，
依据的不是 Q1 要求的测量，而是「6 本来也只是一个写在文件里的数字」这一观察。**
这个观察本身可能是对的；它不是 Q1 要的那份证据。

**撤回的直接理由：那句「只是一个写在文件里的数字」对 Codex 不成立。**
`.codex/config.toml` 的 `max_threads = 6` 是平台**强制**的。而 cookbook 是
两个平台共读的同一份文件——它写 "Up to 12" 就是在叫其中一个平台去做它自己的
runtime 会拒绝的事。抬升期间 `speed.py` 把 Codex 的 6 记为「一个更低的 floor，
不算分歧」；那个建模在**度量**上是对的（floor 不是漂移），在**指令**上是错的，
因为编排器读的是 cookbook 而不是 speed.py 的注释。

**两边现在一致于 6。** 是否要一起往上移、移到哪个数，仍然是 §6 的 Q8，
**本节不替它拍板**——而 Q8 的解锁条件恰恰是上面那份始终没拿到的测量。

### 0bis.2 §3.H3 的 `RUN_TIMES.md` 已被删除；删除理由对 Codex 是错的

本 ADR 在四处把 `RUN_TIMES.md` 当作 `gate stop` 的要求或验收指标：
§3.H3、§3.J 的门控表（*"`RUN_TIMES.md` 存在 | H3"*）、§5 两张验收表
（*"每次运行的 `RUN_TIMES.md` | 6/8 存在 | 8/8"*、*"**0 / 5** | 5 / 5"*）、
§5 回归用例 H、§7 项19。**这些已全部作废：** 该检查于 2026-08-19 从
`cli_tools/_gate/stop.py` 与 `speed.py` 中删除。

删除本身站得住：它被要求、从未被交付（检查落地时 0/5），仓库里从来没有它的模板，
它唯一的规格就是那句警告字符串。

**但删除时给出的理由对 Codex 是错的。** `stop.py:149-155` 写的是
*"the hook now records every dispatch's start, end and byte count, which is strictly
more than the file ever held"* —— 这句话预设了 hook 存在。Codex **没有 hook 机制**
（`.codex/config.toml` 只有 `max_threads` 和 `max_depth`；ADR 0020 Q1 考虑过
dispatch wrapper 并否决了）。于是这次删除对 Codex 的实际效果是：**删掉了一次 Codex
运行唯一可能产出的计时产物，而它的替代品在那个平台上并不存在。**
这正是本 ADR §6 Q6（*"NL 侧 `dispatch.jsonl` 由谁写"*）指出的能力差异，
在一次删除里被忘掉了一遍。

**已修正的部分：** cookbook 的 `## Dispatch Log` 一节现按平台拆分——Claude 侧
由 hook 写、prompt 里不再要求手写（*"一条必须在第四百次派发时仍然成立的规则属于
middleware，不属于 prompt"*，实测两次运行手写保留率 38/39 与 5/352）；
Codex 侧明写「由你手工 append，因为没有 hook 替你写」。`stop.py` 的警告文案
也已按平台分述。**未修正的部分：** hook 在 Claude 侧零触发这件事本身
（159 行里 0 行 `source: "hook"`），删除理由所依赖的前提至今没有被验证成立。

### 0bis.3 状态标注

本文件的状态是 **Partially Accepted**（见头部），而 `README.md` 索引长期记作
`Proposed`。已改 README 与本文件一致；本文件的状态行不动。

---

## 1. Context

### 1.1 目标

一次典型运行从 6–10 小时降到约 4 小时，同时显著降低 token 成本，
**不削弱验证**。

### 1.2 受控数据集

`/home/cyc/caosip/github/Prover/projects/experiments/IMO2026/`：
同一 harness、同一操作者、同一周、六道难度可比的 IMO 题，
每次运行自带 `RUN_TIMES.md`（UTC 起止），形式化侧另有 `cli.log` 逐次 `lean_check` 的毫秒级记录。
**这是本仓库唯一一份可以正当比较墙钟的数据。**
（Ramanujan 各 workspace 未必同一人运行，其墙钟只用于**运行内**的时序与并发分析。）

| 题 | NL 分钟 | FL 分钟 | 合计 |
|---|---:|---:|---:|
| Q4 | 41.73 | 18.85 | 60.58 |
| Q1 | 45.83 | 28.30 | 74.13 |
| Q2 | 97.33 | **147.25** | 244.58 |
| Q5 | 117.18 | 24.47 | 141.65 |
| Q3 | 145.47 | **160.33** | 305.80 |
| Q6 | **327.62** | 24.07 | 351.68 |
| 合计 | 775.17 | 403.27 | **1178.43** |

人类判断：**这六题本身都不难，本应很快做完。** 本 ADR 以此为基准。

### 1.3 成本定律（**已按后续测量重写**）

本 ADR 初稿写的是「墙钟 ≈ 调度轮次数 × **5.0 ± 0.9 分钟**，r = 0.995」。
**该表述已废弃**：那个"常数"不是常数。

| 题 | 调度数 | **平均间隔** |
|---|---:|---:|
| Q4 | 12 | **2.74 min** |
| Q1 | 14 | **2.75 min** |
| Q2 | 22 | 3.86 min |
| Q5 | 27 | 3.97 min |
| Q3 | 28 | 4.69 min |
| Q6 | 66 | 4.77 min |

**修正后的定律：**

> **T(N) = N × f(N)，f 递增。总时间在调度数上是超线性的。**
> IMO 量级上 f 从 2.74 涨到 4.77（1.74 倍）。

**f 增长的机制是读入量，不是写出量**（`docs/harness-speed-forensics.md` §1.1）
—— **该结论只在 0.5–23 KB 量级成立，在 66–160 KB 量级上反转，见 §0.4**：

- 产物字节数**不**预测延迟：459 B 耗 4.3 分钟，22,820 B 耗 1.6 分钟。
  （但 `newtestb` 的 `proof_v1`→`v11` 间隔随产物从 66 KB 长到 159 KB
  而单调上升 19→33 分钟。**写出量在大产物上确实预测延迟。**）
- 预测延迟的是 **prompt 强制的上游产物扇入**。
  `prompts/verifier.md` 的 Global Proof Refinement 模式要求读
  *"…the selected decomposition and lemma statements, **accepted generator proofs
  and prior verifier reports**"*；计划级验证要求读**全部** `lemmas/*/statement.md`。
  Q5 的计划验证读九份 12 小节 statement → 13.9 分钟；Q4 读一份短计划 → 3.75 分钟。

**范围声明**：IMO 跑在 2026-07-17/18，早于 07-23（ADR 0020）与 07-26（ADR 0022）
引入的每轮必读硬前置条件——实测六题的 `memory/` 文件只在运行**结束之后**
被写过一次，且无 `.longterm_read.json`。
因此 **IMO 的 42–328 分钟是今天 harness 的下界，不是基准**；
今天会在 f(N) 之上再叠加每轮记账（Ramanujan 侧实测 Orchestrator 记账屏障
中位 15.5 分钟、占每轮 28%）。

**推论（本 ADR 的全部依据）：**

1. 任何不减少**串行**调度轮次的优化都不会移动墙钟；
2. 由于 f 递增，**减少轮次的收益是超线性的**——这也是 ADR 0023 成为速度杠杆的原因；
3. 减少每次调度**被迫读入的上游产物**，直接压低 f。

**lemma 数不预测时长。** Q1 有 16 条 lemma 用 45.8 分钟；Q3 有 9 条却用 145.5 分钟。
预测时长的是 lemma 被拆成了多少次独立调度。

### 1.3bis 复利机制：危险率塌陷

超线性只是表象的一半。真正让**困难**问题做不完的是另一个机制
（`harness-speed-forensics.md` §12）：

- **从犯错到纠错的时间不增长**——钉在约 40 分钟，全程不变。此项假设已证伪。
- **真正复利的是单次调度的存活概率塌向零，而单次成本不变。**
  3_1 的决策 16–30 是**连续十五次派发全部被下一个决策杀掉**；
  这些决策结构完全相同（同一分类、7 条禁令、5 条 reusable work、
  3 条排队备选、约 29 处路径引用、8.0±0.3 KB），**只有机制族的名字在换**
  （motivic-period → Rademacher–Dedekind → Dirichlet-character →
  Kronecker-limit → probability-simplex，全部是
  "certificate for the fixed eight labelled endpoint generators"）。
  **总时间发散，是因为期望需要的次数发散。**
- **最锐利的判别式是「每 recovery 循环的数学产出」**：
  成功的运行 ↑（2_6：31.5 → 165.0），失败的运行 ↓（2_5：18.25 → 4.50）。每个 workspace 上都单调。
- **`STATUS.md` 超线性膨胀（n^1.5–2）**：行数（线性）× 行长（每行必须与之前所有行
  区分开，于是累加限定词与排除子句）。3_1 是 2_6 的 **83 倍**，工作时间只有 2.8 倍。
  **禁令本身是线性增长的**（每决策约 7 行），初稿把它当主要复利项是错的。
- **交叉点可定位**：3_1 在 t+20h、状态达约 100 KB 时进入枚举极限环，
  同时「每 recovery 循环数学产出」跌破 2。

### 1.4 两个成本机制（勿混淆）

| | 机制 | 主证据 |
|---|---|---|
| **轮次数** | 每一轮 ≈ 5 分钟墙钟 + 一份约 12 KB 产物 | §1.3 主定律 |
| **每轮重读** | 每一轮必读集随运行增长，期末达 92K–154K token | Ramanujan 取证 |

Ramanujan 侧测得：`2_5` 全程重读约 **1010 万** input token，
`2_7` 约 **2080 万**，而两个运行**写出的全部文本只有 7.5 MB 和 8.8 MB**——
**它们重读自己状态的量是写过内容的 5–10 倍。**

期末每轮必读集：

| 文件 | 2_5 | 2_7 |
|---|---:|---:|
| `STATUS.md` | 238 KB | **275 KB** |
| `recovery/route_history.md` | — | **114 KB** |
| `presentation/index.json` | 87 KB | **171 KB** |
| 合计 | **367 KB ≈ 92K token** | **615 KB ≈ 154K token** |

首轮该集合仅 6–10 KB。**增长 40–70 倍。**
而 `2_7` 的 `STATUS.md` 里真正描述当前状态的只有 **2.2 KB**：
`## History`（只追加）125 KB = 45.6%，`## Active Branch Queue` 147 KB = 53.6%，
其中 **303/353 行是已经 done/superseded 的死行（88.6%）**。**约 93% 是死重量。**

### 1.5 声明的并发从未被逼近（**已被 2026-08 语料推翻，见 §0.1**）

> **本节结论不再成立。** 下面的测量对 IMO/Ramanujan 依然正确，但 `newtesta`
> 已实测到六条 lemma 同窗口落盘。**§3.A1/A2 无事可做。**

`CLAUDE.md` 允许 6 个并发 subagent。**实测上限处处是 3。**

- IMO 侧 lemma 波次：Q2/Q3/Q5 的最大并发 **3**，并行因子 1.37–1.69；
  Q6 的 20 份 brainstorm 用了 12 轮，其中 **6 轮宽度为 1**。
- Ramanujan 侧更差：3_1 的「三个 Explorer 一批」**0/22 批**存在任意一对产物落盘间隔 < 60 秒；
  批内间隔中位 8.0 分钟且两两近似相等——串行签名。
  对照组：2_2 有一次 `routes/history.md` 明写的并行 Generator，产物相差 **23 秒**。
  跨两个慢运行，**80%+ 的活跃时间只有一个 agent 在写**。
- 3_1 的 STATUS 自陈：*"A materially new **sequential portfolio** is open"*、
  *"**Rank 34 is the sole active owner/file**"*。

**有效持续并发 ≈ 1。那个 6 从来不是约束。**

### 1.6 两个成本区制，7 倍差（**结论已按内容核对修正**）

| 区制 | 题 | 每 lemma 的 Gen/Ver 轮 | 分钟/lemma | 字节/lemma |
|---|---|---:|---:|---:|
| **批量** | Q1, Q4, Q6 | 1 | 2.9–3.2 | 4.0–4.8 KB |
| **逐条** | Q2, Q3, Q5 | 8–9 | 10.8–16.2 | 31–33 KB |

初稿称批量区制"靠降低验证深度换来"。逐份阅读产物后**该判断需要收窄**：

- **覆盖率完整。**批量 Verifier 是**逐节点**填模板的，不是只查组装
  （Q1 的 Risk Audit 14 项中 8 项分别溯源到具体 `lemmas/<name>/statement.md`；
  Q6 有逐边依赖表带行号区间）。
- **`报告字节 / 证明字节` 在两个区制上一致**：批量 0.77–1.14，逐条 0.99–1.07。
  批量 Verifier 花在单位证明上的笔墨与逐条相同。
- 每节点评级步数塌 10–18 倍，**但证明本身也塌了同样倍数**
  （批量约 1.1 KB 数学散文/节点，逐条约 7 KB）。

> **准确表述：真实的 6–7 倍 token 节省，覆盖率完整保留；
> 损失的是每节点深度——一段而不是一页。这个深度差是否代价真实，本语料无法定论。**

**因此本 ADR 仍不强制批量，但理由改变**：不再是"批量削弱验证"，
而是**深度差未经检验**，且 A1（并发跑六个 fresh Verifier）能在不改变
任何验证语义的前提下拿到大部分墙钟收益。两条相反证据都记录在案：

- 全语料**唯一一次 INVALID 评级**来自逐条 Verifier（Q5 `lem_positive_drift`
  端点 `<`/`≤` 写反）——但基率是 27 次逐条中 1 次、3 次批量中 0 次，
  **n=3 对 n=27，统计上不可区分**。
- 逐条区制有批量不可能有的结构性风险：Q5 `lem_dichotomy` 发出**条件式 PASS**
  ——*"The separate v2 proof of `lem_positive_drift` must receive a fresh PASS
  before this downstream result is adopted."*——**下游 lemma 对着一个
  同时正在修订的依赖被验证**；且 Q5 半条死掉的 `lem_defect_trap`
  通过了 lemma 级验证，直到 refinement 才被发现从未被使用。

### 1.6bis 分解不是浪费（撤销初稿的一条决议依据）

初稿据 grep 认定「批量运行的 lemma DAG 被整个绕过、约 46 分钟浪费」，
并据此准备了"限制分解规模"的决议。**该依据被内容核对推翻，相应决议已删除。**

跨五题 **79 个节点，只有 2 个未承载正面数学（2.5%）**，其中一个（Q6 `finite_blocker`）
还是被证伪后转为永久约束的关键反证。Q4 的 13 条 lemma 是那份单体证明的 15 个 Step；
Q1 的证明把 `decomposition.md` 的 LB1–LB12 十二行原样带回；
Q6 的证明章节字面上叫 `W1`…`W16`，即 sketch 义务账本的 ID。
grep 失败是因为**批量证明就地证明而非引用，且按义务编号组织**。

内容层面真正的浪费只有一处：**Q1 的 `lemmas_alt/complete`**——26 KB 完整证明 +
13 份 statement、**从未验证**、且是数学上等价的路线。驱动它的是
`prompts/refiner.md` 强制的两次备选扇出，且被否决的路线也必须写出来。

### 1.7 关于「验证和写作本来就慢」

这条判断需要按数据修正，而且两份取证的表面冲突有一个统一解释。

**写作不是杠杆。** 测得的验证后尾段（Refiner + Writer + LaTeX + PDF + 记忆 + gate）
是一个**近似常数 13–32 分钟**，与运行长度无关：

| 题 | NL 分钟 | 尾段 | 占比 | 其中 Writer |
|---|---:|---:|---:|---:|
| Q1 | 45.8 | 15.5 | 34% | 0.6 |
| Q5 | 117.2 | 21.0 | 18% | 4.4 |
| Q6 | 327.6 | 17.7 | **5%** | 1.3 |

LaTeX/PDF 编译在每次运行中都 **< 30 秒**。尾段在快速运行上"显得大"，
只是因为分子固定而分母小。**即使把写作整个删掉也只省约 15 分钟。**

**验证本身不慢，慢的是验证的调度。**

- IMO 侧按"产物归属其自身相位"计：Q1 验证 1.6 分钟（3.7%），Q4 4.0 分钟（10.8%），Q6 5.6 分钟（1.7%）。
- Ramanujan 侧按"时间归属其后继事件的车道"计：2_2 验证 36.2%、3_1 导入后 30.7%。

**两者不矛盾。** 统一解释就是主定律：一次 Verifier 轮次的**思考+写作**只要几分钟，
但它要付一次完整的 5 分钟调度延迟。Q2/Q3/Q5 发了 8–9 次 Verifier 调度，
**同样的检查工作量，6–10 倍的墙钟**。

> **结论：验证在一次成功运行中占约 30–50% 是正确的稳态，不该优化掉；
> 该优化的是它被拆成了多少次串行调度。**

### 1.8 形式化侧：Lean 编译不是瓶颈

来自 `cli.log`（配对 call→result，毫秒精度）：

| 题 | 墙钟 | leancheck 次数 | 编译总计 | **占墙钟** | 失败率 |
|---|---:|---:|---:|---:|---:|
| Q1 | 28.3 | 15 | 3.2 min | 11% | 20% |
| **Q2** | **147.25** | 70 | 19.1 min | **13%** | **50%** |
| **Q3** | **160.33** | 128 | 22.4 min | **14%** | **48%** |
| Q4 | 18.85 | 27 | 2.5 min | 13% | 37% |
| Q5 | 24.47 | 25 | 8.2 min | 34% | 24% |
| Q6 | 24.07 | 19 | 1.4 min | 6% | 21% |

**编译处处只占 6–14%。Q2 的 128 分钟、Q3 的 138 分钟是 agent 时间。**

根因已定位：**Q4/Q5/Q6 用了「`sorry` 骨架先锁接口 + 并行波次」，Q2/Q3 没用。**

- Q4 的 `RUN_TIMES.md` 自陈：*"Locked a compiling skeleton (all defs + 13 helper
  lemma statements as `sorry`), which fixed every interface up front.
  Fanned out 4 parallel `lean-proof` subagents."* Q6：*"24 lemmas as `sorry` …
  8 lean-proof subagents ran in parallel."*
- **Q2 的 `RUN_TIMES.md` 完全没有 Method 段**（461 字节，只有结果）。
- `.claude/state/proof_tasks.json`：**Q2 的 11 个任务全部 `dependencies: []`、
  `blocked_by: []`，却被逐个串行执行**；`current_wave` 在**全部六题中都是 0**——
  波次计数器从未被使用。
- 试探性 probe 的代价：Q3 的 `probe_c3.lean` ×14 + `c3dev.lean` ×11 + `C3.lean` ×1
  = **26 次检查才落地一条 lemma**；Q2 的 `akl_noncollinear`（18 行文件）×10。
- 空闲缺口（相邻 leancheck ≥ 6 分钟）：Q2 有 4 段共 **90 分钟 = 61% 墙钟**；
  Q3 有 6 段共 68 分钟 = 41%；**Q4、Q5 为零，Q6 只有 1 段 7 分钟。**

### 1.9 Q6 的解剖：86% 是机器，不是数学

按相位归属分钟（Q6 informal，325.1 分钟）：

| 相位 | 分钟 | % |
|---|---:|---:|
| 日志（镜像 route/recovery 轮次） | 170.8 | 52.5% |
| 路线生成——审计与反例 | 54.4 | 16.7% |
| 路线生成——Explorer | 46.3 | 14.2% |
| 恢复/Regulator 分支管理 | 15.5 | 4.8% |
| 分解/sketch | 10.2 | 3.1% |
| lemma 生成 | 8.6 | 2.6% |
| 写作/LaTeX | 6.4 | 2.0% |
| 精化 | 6.0 | 1.9% |
| **验证** | **5.6** | **1.7%** |

**282 / 327 分钟（86%）是路线搜索与分支恢复机器；43 分钟是有产出的尾段**——
从 `synthesis_8` 开始到 sketch → 16 条 lemma 陈述 → 一次 Generator → 一次 Verifier PASS
→ Refiner → Writer → PDF，全程 43 分钟。

**而获胜路线（`brainstorm_20`，固定有限素数宇宙）是一个在第 25 分钟就已在桌面上的想法的复活。**
`synthesis_8.md` 逐字：*"it supplies the fixed finite prime universe missing from the earlier routes."*

机制族重复（实测）：秩/下降界 **7 次**、有限素数宇宙 **4 次**、三角/自对偶障碍 **3 次**；
42 份 route 产物中 **14 份**属于已被尝试 3 次以上的族，
按每轮 9.3 分钟计 ≈ **130 分钟可证的重复探索**。
第 2 段（145.6 分钟）**除压力测试数据外没有任何产物进入最终证明**。

### 1.10 中断不是资源问题，是 Regulator 误判

Q6 跑了三段。两次中断的**终止产物都是 Regulator 宣布分支预算耗尽**
（`RESTART_OBLIGATION`，尾标 `active_owner=NONE queued=0 target=NONE`），
**都被人类推翻，而且人类三次都是对的**——最后一次判决之后 66 分钟就出了已验证的证明。
第三次同样的判决（`regulator_decision_4.md`）在会话内被推翻，代价 12.6 分钟。

**这与 §1.9 的机制族重复同源**：Regulator 把 7 次秩/下降尝试算作 7 条不同分支，
于是认为空间已穷尽。**按族计数，它看到的是 3 个族，不会宣布耗尽。**

---

## 2. 与 ADR 0023 的关系（必须先读）

**两个 ADR 作用在主定律的不同因子上，效果相乘。**

```
墙钟  ≈  串行调度轮次数  ×  每轮延迟
           ↑                    ↑
        ADR 0023             ADR 0024
     （减少轮次总数）      （降低单轮成本 + 并发化）
```

- **ADR 0023 减少的是"为什么会有这么多轮"。** K1–K8 八种击杀机制导致路线被永久关闭、
  重复探索、机制族反复重来。Q6 的 130 分钟重复探索、3_1 的 88 轮 brainstorm、
  2_5 的 317 条 route，都是它管辖的。
- **ADR 0024 减少的是"每一轮多贵、能不能同时跑几轮"。**
- **两者都不足以单独达标。** 只做 0023，Q6 变成 Q1 的形状但每轮仍是 5 分钟串行；
  只做 0024，Q6 的 56 轮并发化后仍在做 130 分钟的重复工作。

**双向约束（本 ADR 对 0023 的反向要求）：**

ADR 0023 新增了 conjecture ledger、Prospector、`discovery.py revivable` 前置检查——
**这些在主定律下都是新增读写，必须按调度经济学审查**：

1. **Prospector 在主定律下是有利的**：它用**一次长调度**替代**多次短调度**。
   Q6 的 56 轮 × 5 分钟 = 280 分钟；一次 94 分钟的连续推理成本更低。
   **前提是它不能退化成"很多次短调度加起来"**——见 §3.G。
2. **`discovery.py revivable` 必须是增量的**，不得成为又一个随运行增长的必读项（§3.C）。
3. **conjecture ledger 必须有条目上限与紧凑视图**，否则它会变成第二个 `STATUS.md`（§3.C）。
4. **ADR 0023 的 `parked` 状态直接服务于 §3.F 的机制族账本**：
   按族计数需要一个不把"未定"当"已否决"的状态机。

**冲突检查**：ADR 0023 §D2 的 `deepen` 纵向档会**延长**单次路线的投入。
在主定律下这是**有利**的——加深是在同一轮内做更多工作，而横向扩是多开一轮。
两个 ADR 在这一点上同向。

---

## 3. Decision

### A. 使用已经批准的并发额度（零 invariant 改动）

**A1 — lemma 车道并发从 3 提到 6，并取消波次屏障。**
一条 lemma 的 Verifier 在其 Generator 产物落盘的那一刻启动，
而不是等到波次边界。

实测波次间死时间：Q2 17.4 分钟、Q3 20.2 分钟、Q5 20.2 分钟。
lemma 阶段跨度 38.8 / 43.7 / 48.5 分钟，而最长单条 lemma 窗口只有 7.7 / 14.0 / 24.6 分钟。

**依据**：`CLAUDE.md` 已经写明允许 6 个并发；invariant 3（每次检查用新鲜无状态 Verifier）
让并行验证**更安全**而非更危险；invariant 5（只写自己被指派的工作区）
因每条 lemma 独占 `lemmas/<id>/` 而天然满足。
**这不是放宽规则，是使用已有额度。验证次数不变。**

**A2 — Explorer 组合真正并发。**
`subagent-dispatch-cookbook.md` 本来就写的是 "Explorer **x2-3** with distinct
constraints" 并给了八个 diversity constraint。提高到 6，并**禁止**
「单一活跃 owner」这种运行期习惯（它不是任何 invariant，只是 STATUS 层的做法）。

实测：3_1 的三元批 0/22 存在 < 60 秒的共同落盘；Q6 的 20 份 brainstorm 用了 12 轮，
6 轮宽度为 1。按宽度 6，20 份 brainstorm 只需 4 轮。

**A3 — 明确「并发」的可验收定义。**
一批 N 个同类 specialist 视为真并发，当且仅当其产物落盘时间的
**极差 < 单个 agent 中位运行时长**。这个判据在 2_2 上得到验证（并行对 23 秒，
串行批中位间隔 8.0 分钟）。写入 cookbook，并由 `gate.py` 事后核对。

### B. 形式化侧：`sorry` 骨架 + 并行波次成为强制前置

**B1 — 第一次 `lean-proof` 调度之前，必须先锁一个可编译的 `sorry` 骨架**
（全部定义 + 全部 lemma 陈述以 `sorry` 占位）。
这固定了所有接口，消除试探性 probe。

**B2 — `current_wave` 计数器必须真正使用。**
现状：六题的 `.claude/state/proof_tasks.json` 里 `current_wave` **全是 0**。
`Prover/CLAUDE.md` 的 Subagent Workflow 说"每一波之后调用 Regulator"，
却从未**要求**存在波次。

**B3 — `dependencies: []` 的任务必须并发派发。**
Q2 的 11 个任务全部无依赖却串行执行。这是可机械检查的。

**依据与预期**：Q2/Q3 相对 Q4/Q5/Q6 的超支中，约 73% / 68% 可追溯到这一条。
Lean 编译只占 6–14%，不是瓶颈。**最终 Lean 门一字不改。**

### C. 每轮必读集：分层、增量、封顶

**C1 — `## History` 移出 `STATUS.md` 到 `STATUS_history.md`，不进每轮必读。**
它是纯追加叙事，占 2_5 的 56.5%、2_7 的 45.6%。
路由所需的历史已经有 `recovery/route_history.md`。

**C2 — 已关闭的分支队列行归档到 `STATUS_closed.md`。**
只有 `active | queued | parked | blocked` 留在 `STATUS.md`。
2_7 的队列 88.6% 是死行。

C1+C2 合计把 2_7 期末的 `STATUS.md` 从 275 KB 降到约 **20 KB（−93%）**，
不损失任何可路由信息。

**C3 — `presentation/index.json` 移出每轮必读集。**
它期末达 87 KB（2_5）/ **171 KB（2_7）**，而 `AGENTS.md` 本来就只要求
"when their inputs are relevant"；`presentation/index.md` 与
`workspace.py presentation` 已提供紧凑视图。

**C4 — `recovery/route_history.md` 封顶（默认 25 KB）**，
超出部分滚动到 `route_history_archive.md`。它在 2_7 达 114 KB。

**C5 — 必读集总预算硬上限。**
新增 `memory.py budget <workspace>`，报告当前每轮必读集字节数；
`gate.py` 在超过阈值（默认 60 KB）时报警并指出该归档什么。
**这是防止本 ADR 的收益随时间被重新吃掉的机制。**

**C6 — ADR 0023 的新产物同样受 C5 约束。**
conjecture ledger 的每轮必读视图是 `discovery.py ledger --view compact`，
不是全文；`discovery.py revivable` 只输出触发已满足的条目。

### D. 产物瘦身：只砍仪式，不砍检查

按小节字节归属统计（IMO 六题 114 份产物）：

| 产物类型 | n | 总字节 | **仪式占比** |
|---|---:|---:|---:|
| **Verifier report** | 30 | 385 KB | **62%** |
| **Verifier review packet** | 30 | 134 KB | **59%** |
| Generator proof | 22 | 272 KB | 22% |
| Explorer brainstorm | 32 | 430 KB | **3%** |

Ramanujan 侧同向：`regulator_decision_*.md` **81.9%** 仪式，
`computation_audit_*.md` 35.8%。

**D1 — 不适用的 schema 小节改为一行否定答复，而不是删除。**
样本 `Q5/.../lem_dichotomy/verifier/report_v1.md`（10.5 KB / 239 行）：
前 96 行是真正的数学检查，后 143 行是 schema——
其中 5 项 Preflight Risk Audit 有 **3 项是 `NOT APPLICABLE`**，
`Finite Case and Computation Audit` 第一个字段是 `Applies: NO` 后面跟着 **8 个 `N/A`**，
还有一段为**排中律**开具的 `Theorem Preconditions`
（"Source or derivation route: elementary classical logic"）。

**保留每一个小节作为被检查的字段**（invariant 6/8/9/10 与
`gate.py review-packet` lint 因此不变），**但允许一行否定答复代替整段散文**。

**D2 — 绝不动这两块**：`Dependency Preconditions` 与
`Load-Bearing Obligation Ledger`。样本显示它们在做真实工作
（`lem_positive_drift` v2 的条件式 PASS 就依赖它们）。

**D3 — Regulator 产物按 ADR 0023 §C1 结构化后自然瘦身**，
本 ADR 不重复规定。

**D4 — 停止把每份 route 产物镜像进 `logs/`。**
Q6 的 54 个日志文件（57 KB）是每份 route/recovery 产物一条的薄记录；
Ramanujan 侧 `logs+recovery` 在 Q6 达 140 KB。
改为写 `memory.py append` 的既有账本，不再维护平行文件树。
（"Rules for All Agents #6 — Log meaningful agent activity under `logs/`" 相应修订。）

### D-bis. 探索预算与首次 Generator 时限（**对 2026-08 语料不适用，见 §0.3**）

> 下表的判别式在 Ramanujan 上是对的。但 `newtestb` 的 `prove:explore` = **48.0**、
> `newtesta` = **19.0**，都远在「成功」区间之上，而 `newtestb` 仍跑了 26.6 小时。
> **今天的失败模式是产物重发（§0.4），不是枚举极限环。** 本节与 §F 暂不实施。

取证给出一个单指标就能分开成功与失败的判别式：

| workspace | 结果 | **prove : explore 派发比** | `recovery/` | `sketch/decomposition.md` |
|---|---|---:|---:|---|
| 2_6 | 解出 | **5.0** | 10 | 有 ×3 |
| 2_2 | 解出 | **3.7** | **0** | 有 |
| Q1 | 解出 | — | **0** | 有 |
| 2_5 | 失败 | 0.34 | 30 | **44.7 小时内从未写出** |
| 2_7 | 失败 | 0.33 | 60 | 12 |
| **Q6** | 解出但最慢 | **0.086** | 8 | 有（第二版） |
| 3_1 | 失败 | **0.08** | 71 | 1，`not-generator-ready` |

**每一个成功的运行都在头 15 分钟内进入了 Generator/Verifier 循环。**
3_1 连着跑了 151 次探索派发、37.9 小时零 Generator；
2_5 跑了 41 次、44.7 小时零 lemma。

**D-bis1 — 硬预算：连续无 Generator 介入的探索派发不得超过 N 次（默认 8）。**
达到上限时，Orchestrator 必须在下列三者中择一，且必须记录选择理由：

- 用当前最好的（哪怕不完整的）路线强制进入 Sketcher → Generator，允许失败；
- 派发 `first_missing` 规格任务单（ADR 0023 §D1）；
- 声明需要人类输入并停止（走 ADR 0021/0022 的正常停止路径）。

**不允许的第四种**：再开一轮 Explorer 组合。这正是极限环的燃料。

**D-bis2 — 首次 Generator 时限。**若一次运行在前 T（默认 30 分钟）内
没有写出 `sketch/decomposition.md`，视为**进程级异常**并记录告警。
2_5 与 2_2_old 从未写出它；成功的运行在前 15 分钟内就有。

**D-bis3 — 每 recovery 循环的数学产出必须被度量并显示。**
新增 `discovery.py yield <workspace>`（或并入 `gate.py speed`），
报告最近三个 recovery 循环之间产出的数学产物数。**连续两个循环下降即告警**——
这是取证中唯一在每个 workspace 上都单调的判别式
（成功 2_6：31.5 → 165.0；失败 2_5：18.25 → 4.50）。

**D-bis4 — 机制族计数是 D-bis1 的前提。**没有 §F 的族账本，
Regulator 会把同一族的 7 次尝试算作 7 条不同分支，探索预算形同虚设。
**D-bis 与 F 必须一起实现。**

### E. 上游廉价过滤消除重试（2_2 的真实制胜法）

2_2 全程真并发只贡献约 10 分钟。它赢在三件**上游**的事，结果是
**5/5 lemma 一次 PASS、0 次 recovery 决策**：

**E1 — 尽早锁定源定理。** 2_2 在第 22 分钟找到 Rivoal——三个指定候选都不匹配后，
**沿它们的引用链**找到确切出版源（`routes/history.md`:
*"Following their Rivoal citations reached the exact published source"*）。
规范化：Searcher 在候选失配后**必须**做一次引用图遍历再返回负结果。

**E2 — 证明之前先机械认证代数。**
2_2 在 15:45 让 Code Executor 出 `PASS_AUDIT`，于是 Generator 写的是
**已经数值确认过的恒等式**的证明。STATUS 明确记着这
*"is not a mathematical Verifier verdict"* ——它是一道便宜的机械过滤，
作用是把重试轮数压到零。**这不替代验证，它减少验证的次数。**

**E3 — 对抗性 Explorer 与建设性 Explorer 同批并发。**
2_2 因此在**计划验证**阶段就抓住了归一化陷阱，而不是等到证明阶段。
配合 A2，成本为零（同一批次内多一个 constraint）。

### F. 机制族账本（与 ADR 0023 的接口）

**F1 — route 产物新增 `family` 字段**，取值来自一个受控词表
（秩/下降、有限宇宙、障碍、变换/规范、源定理、数值识别 …）。

**F2 — 耗尽判定按族计数，不按分支计数。**
`branch-queue-cookbook.md` 的 "materially different" 定义本身是对的
（改策略/源定理/定义读法/构造/不变量/DAG 桥/计算证据/障碍假设），
**但没有任何东西计算族成员关系**。Q6 因此把 7 次秩/下降尝试算作 7 条不同分支。

**F3 — 宣布耗尽前必须先跑一次复活检查**
（ADR 0023 §H3 的 `discovery.py revivable`）。
Q6 的获胜路线正是一次复活。

**预期**：F1–F3 直接消除 Q6 约 130 分钟的重复探索，
并且**顺带修掉 §1.10 的两次中断**——按族计数的 Regulator 看到的是 3 个族，
不会宣布 `queued=0`。

### G. Prospector 的调度经济学约束（ADR 0023 §J 的补充）

**G1 — Prospector 必须是一次长调度，不得退化为多次短调度。**
在主定律下，一次 94 分钟的连续推理成本低于 19 次 5 分钟轮次。
若 Prospector 因产物长度或工具往返被切成 N 段，它的经济优势就消失了。

**G2 — Prospector 的 REPL 往返不计入调度轮次**，
因为它们在同一个 agent 上下文内，不付 5 分钟的重新加载代价。
这是给它配 REPL 的第二个理由（第一个是 ADR 0023 §J3）。

**G3 — Prospector 与 Explorer 组合互斥派发**，避免同一轮既长又宽。

### H. 中断与存活治理

**H1 — 影子 owner 取代「中断—替换」阶梯。**
现状（3_1）：56 次存活/调度事故、≥70 个失败轮次，
每次要走 *"bounded polling → focused checkpoint → hard completion request →
final allowance"*，**替换 owner 被派出之前就已花掉 5–17 分钟**。
07-29 的 Synthesis 链：四个连续 owner 全失败 → invariant 17 停机 →
等人 20 分钟 → 一个只写 `DRAFT_SKELETON` 的浪费轮次 → 第六轮才成功，
**一份产物 48 分钟**。

改法**不动所有权模型**：在第一次错过检查点时，给影子 owner 一个
**不同的目标文件**（`synthesis_33b.md`），谁先落盘就采用谁。
3_1 事后已经在用 `_b`/`_c` 命名做这件事——**28 次**，只是都发生在失败之后。

**H2 — 大产物分块追加输出。**
2_5 有两次 Generator 撞上 64000 输出 token 上限，
原因是 *"emitting the artifact monolithically"*，两次调度全额付费、零产物。

**H3 — `RUN_TIMES.md` 由 `gate.py stop` 机械要求。**
Q4、Q5 的 informal 运行**根本没有** `RUN_TIMES.md`，
而 `gate.py stop` 不检查它。没有计时就没有优化。

**H4 — NL 侧缺少工具调用日志。**
形式化侧有 `cli.log`（毫秒级 `lean_check` 记录），**NL 侧没有等价物**，
所有 NL 计时只能靠 mtime 反推。新增一份轻量 `logs/dispatch.jsonl`
（每次 subagent 派发一行：角色、目标、起止、字节数），
它同时是 §3.A3 并发判据和 §3.C5 预算检查的数据源。

### I. Refiner 改为条件触发

`CLAUDE.md` Routing 与 `orchestrator-cookbook.md` 都强制「验证通过后 Refiner 跑一次」，
而每次 Refiner 又触发一次**新鲜**验证（invariant 15）。
实测精化耗时：Q1 5.1 + Q2 0 + Q3 8.3 + Q4 4.0 + Q5 13.3 + Q6 5.3 = **36 分钟**，
外加它们各自触发的验证轮次。

**改为按长度/复杂度阈值触发。** 原证明作为 fallback 保留不变，
因此**验证强度不受影响**；受影响的是 `proof.pdf` 的可读性——
这是一个真实的质量旋钮，需要人类拍板（见 §6 Q3）。

### J. 机械门控

`gate.py speed <workspace>`（或并入现有 gate），全部为可机械核对项：

| 检查 | 对应 |
|---|---|
| 同类批次落盘极差 < 单 agent 中位时长 | A3 |
| 存在 `dependencies: []` 却被串行派发的任务 | B3 |
| 首次 `lean-proof` 调度前存在可编译 `sorry` 骨架 | B1 |
| `current_wave` 单调递增且 > 0 | B2 |
| 每轮必读集字节数 ≤ 预算 | C5 |
| `STATUS.md` 不含 `## History`，不含已关闭队列行 | C1/C2 |
| route 产物含 `family` 字段 | F1 |
| 宣布耗尽前跑过 `discovery.py revivable` | F3 |
| `RUN_TIMES.md` 存在 | H3 |
| `logs/dispatch.jsonl` 存在且行数与产物数一致 | H4 |

---

## 4. Consequences

### 4.1 预期收益（本数据集，逐项标注实测/估计）

| # | 杠杆 | 类别 | 预计节省 | 置信度 | 验证影响 |
|---|---|---|---|---|---|
| 0 | **探索预算 + 首次 Generator 时限（D-bis）** | **切断极限环** | **Q6 约 165 min；对失败运行是"能否完成"而非快慢** | 高（判别式在每个 workspace 上单调） | 无 |
| 1 | 形式化 `sorry` 骨架 + 波次（B） | 并发+去重试 | **130–160 min** | 高（实测支撑） | 无 |
| 2 | 机制族账本（F），并顺带修中断 | 去重复 | **65–130 min**（与 #0 重叠，勿相加） | 中（估计） | 无 |
| 3 | lemma 车道 3→6、去屏障（A1） | 并发 | **60–70 min** | 高（实测支撑） | 无 |
| 4 | Explorer 并发到 6（A2） | 并发 | **40–50 min** | 中 | 无 |
| 5 | Refiner 条件触发（I） | 去冗余 | **25–35 min** | 高（实测） | 无（fallback 保留） |
| 6 | Verifier schema 条件化（D1） | 降冗长 | **20–30 min + 约 5 万 token** | 中 | **触及 invariant 6/8/9/10——以一行否定答复实现，不删除** |
| 7 | 中断阈值修正（F3/H1） | 避免重启 | **15 min 直接** | 高（实测） | 无 |
| 8 | 每轮必读集瘦身（C） | token | **约 2000 万 input token（Ramanujan 量级；IMO 量级为零）** | 中（估计） | 无 |
| 9 | 停止 `logs/` 镜像（D4） | token | 约 140 KB/run | 高 | 无 |
| 10 | 取消 Refiner 的强制备选扇出（§1.6bis） | 去冗余 | Q1 约 7 min（26 KB 未验证的等价证明） | 高（实测） | 无 |

**重要限定**：#8 的 token 收益**只在 Ramanujan 量级成立**。IMO 侧的必读集
从未被读（§1.3 范围声明），所以那一批的 token 成本不在这里。
初稿把该收益无差别地记在整体上，已修正。

**关于超线性的复利效应**：由于 T(N) = N × f(N) 且 f 递增，
**减少轮次的杠杆（#0、#1、#2）收益是超线性的，而并发杠杆（#3、#4）是线性的**。
这与初稿把两类并列的做法不同——**#0 应当最先做**。

> **2026-08-10 修订**：上表在本仓库范围内**不再可兑现**。
> #0（D-bis）对最新语料不适用，#1（形式化）在 `Prover/` 仓库，
> #2（机制族）与 #0 绑定，#3/#4（并发）已经实现。上表十项里有五项归零。
> 取而代之的是表外的一项：**产物重发（§0.4）**——单条 lemma 实测 7.9 小时、1280 KB
> 写出对 159 KB 产物，跨三个语料 79% 的修订字节是被推翻的重写。
> **它同时是墙钟杠杆和 token 杠杆，且不触碰任何一次 Verifier 检查。**
> 具体收益待第一次真实运行后由 `gate.py speed` 判定 —— 本轮未跑任何运行。

**墙钟合计：1178 → 690–825 分钟（六题），即每题端到端 115–137 分钟。**
Q6 级别的运行从 351.7 分钟（5.9h）降到约 **170–210 分钟（2.8–3.5h）**。
**清过 4 小时目标且有余量，而杠杆 1–5、7–9 不改变任何一份 Verifier 产物。**

**Token：** 上述必读集瘦身 + 产物瘦身，估计可省 Ramanujan 侧 3100 万 input token 中的约 2000 万，
**不动任何一道 Verifier 门、不动计算审计、不动 finite-universe 声明。**

**与 ADR 0023 相乘**：0023 把 Q6 的 56 轮压向 Q1 的 13 轮量级，
0024 把剩下的轮次并发化并降低单轮成本。两者不应把 §4.1 的数字与 0023 的收益直接相加——
**杠杆 2（机制族账本）与 ADR 0023 的 K1/K8 覆盖同一块重复工作，存在重叠。**

### 4.2 明确不做的事

- **不减少 Verifier 检查次数。** A1 是让六个 fresh Verifier **同时**跑，不是合并成一个。
- **不强制批量 lemma 区制。** 尽管它便宜 7 倍，Q1 的 1.4 KB/lemma vs Q5 的 12.8 KB/lemma
  是验证深度的真实下降，与约束冲突。
- **不删除任何 schema 小节**，只允许一行否定答复。
- **不动 `Dependency Preconditions` 与 `Load-Bearing Obligation Ledger`。**
- **不提高 `CLAUDE.md` 的并发上限 6。** 实测持续并发是 1，峰值 3；
  在 A1–A3 落地之前提高上限没有任何意义。

### 4.3 风险

| 风险 | 缓解 |
|---|---|
| 6 路并发放大 HTTP 429/529 类瞬时故障 | H1 影子 owner；并发度可配置降级 |
| 并发 Verifier 之间产生冲突写 | invariant 5 已保证 `lemmas/<id>/` 互斥；A3 的判据只读 |
| schema 条件化被滥用成"什么都不适用" | 每个小节仍是必填字段，`gate.py review-packet` lint 不变；否定答复必须给一行理由 |
| `STATUS.md` 拆分破坏现有工具/gate | `memory.py refresh` 的 glob 与 `gate.py` 需同步更新（实现清单 §7） |
| 必读集预算成为新的形式主义 | 预算超限只报警并指出该归档什么，不阻塞 |
| 与 ADR 0023 的新产物叠加后必读集再次膨胀 | C6 把 0023 的产物纳入同一预算 |
| Refiner 条件化降低 `proof.pdf` 可读性 | 这是真实权衡，列为待决 Q3 |

---

## 5. 验收

**目标（本数据集可复核）：**

| 指标 | 现状 | 目标 |
|---|---|---|
| Q6 级 informal 运行 | 327.6 min | **≤ 180 min** |
| Q2/Q3 级 formal 运行 | 147 / 160 min | **≤ 70 min** |
| 六题合计 | 1178 min | **≤ 825 min** |
| lemma 阶段最大并发 | 3 | **6** |
| Explorer 批次落盘极差 | 中位 8.0 min/间隔 | **< 单 agent 中位时长** |
| 期末每轮必读集 | 92–154K token | **≤ 15K token** |
| `current_wave` | 恒为 0 | 单调递增 |
| Verifier 产物仪式占比 | 62% | **≤ 35%** |
| 每次运行的 `RUN_TIMES.md` | 6/8 存在 | 8/8 |

**2026-08-10 新增验收指标（问题无关，`gate.py speed` 直接给出）：**

| 指标 | 现状（`newtestb`） | 目标 |
|---|---|---|
| 重写浪费率 | **70%** | **≤ 30%** |
| `size(proof_vN) / size(proof_v1)`，N ≤ 10 | **2.40** | **≤ 1.5** |
| 单条 lemma 写出字节 / 最终字节 | **8.0** | **< 3.0** |
| `STATUS.md` 符合路由形状的小节 | **1 / 6** | **≥ 5 / 6** |
| 每次运行的 `RUN_TIMES.md` | **0 / 5** | 5 / 5 |

**回归用例（可机械核对）：**

- **A** 给定 N 条无依赖的 generator-ready lemma，必须在一批内派发，落盘极差 < 单 agent 中位时长。
- **B** 首次 `lean-proof` 调度前必须存在可编译 `sorry` 骨架；`dependencies: []` 的任务不得串行。
- **C** 运行任意时刻的必读集字节数 ≤ 预算；`STATUS.md` 不含 `## History` 与已关闭队列行。
- **D** 一份 `Applies: NO` 的 Finite Case 小节必须是一行，不得是 8 个 `N/A` 字段。
- **F** 同一 `family` 的第 3 次尝试必须被门拦下并指向复活检查。
- **H** 每次停止都产出 `RUN_TIMES.md` 与 `logs/dispatch.jsonl`。

---

## 6. 待决问题

**Q1 — 并发度该定在 6 还是更高。**
实测从未超过 3，所以 6 尚未被检验。建议先按 6 落地并用 `dispatch.jsonl` 观测，
再谈提高。提高上限**在 A1–A3 之前毫无意义**。

**Q2 — Verifier schema 条件化的边界。**
D1 提议"保留字段、允许一行否定"。需要你确认这不触碰你对审稿深度的底线——
这是本 ADR 唯一触及 invariant 6/8/9/10 的条款。

**Q3 — Refiner 条件触发的阈值。**
它是速度与 `proof.pdf` 可读性的真实权衡，不是纯粹的浪费。按什么阈值？页数？lemma 数？

**Q4 — `STATUS.md` 拆分的兼容代价。**
C1/C2 会影响 `memory.py refresh` 的 glob、`gate.py` 的多处检查、
以及所有引用 `STATUS.md` 行号的既有产物。是否值得，还是先只做 C3/C4（零兼容代价）？

**Q5 — 机制族词表由谁维护。**
F1 需要一个受控词表。是每个问题各自声明，还是仓库级共享？
跨问题共享的话，它天然属于 ADR 0023 §G3 的长期正面通道。

**Q6 — NL 侧 `dispatch.jsonl` 由谁写。**
Orchestrator 自己写（简单，但它可能漏）还是 hook 写（可靠，但 Codex harness 无 hook）？
这是两个 harness 能力差异的又一处体现。

**Q8 — 两个平台的并发上限该不该一致，以及一致到几（2026-08-25 新增，见 §0bis.1）。**
现状（2026-08-25 撤回之后）是三处一致于 6：`DECLARED_CONCURRENCY = 6`、
cookbook "Up to 6 at once"、`.codex/config.toml max_threads = 6`。Q8 问的因此
不再是「如何收拾一个分歧」，而是「要不要一起往上移，以及凭什么」。
三个选项：把 Codex 提到 12（需要改 `.codex/config.toml`，且没有证据说 12 是安全的）；
把 cookbook 的数字按平台拆分（与 §0bis.2 里 Dispatch Log 的处理一致）；
或把两边都退回 6，直到 Q1 要求的 `dispatch.jsonl` 测量真正拿到。
**这是一个决定，不是一处笔误，本 ADR 的修订记录不替人类拍板。**
它的解锁前置仍然是 Q1 的老前置：先让 `dispatch.jsonl` 真的有数据
（Claude 侧 hook 触发，Codex 侧手工 append 被执行）。

**Q7 — 本 ADR 与 ADR 0023 的实施顺序。**
我倾向 **0024 的 A/B/C 先行**（零 invariant 改动、收益确定、可立即验证），
0023 随后——因为 0023 的改动更深，而 0024 提供的 `dispatch.jsonl` 与必读集预算
正是评估 0023 是否真的减少了轮次所需要的测量基础设施。
**先把秤造好，再改配方。**

---

## 7. 实现清单

> **2026-08-10：本清单已按 §0 复核。** 逐项状态见 §0.7。
> 第 1–3 项已无事可做（§0.1）；第 4 项范围外（§0.6）；
> 第 7、8 项指错了文件（§0.2）；第 11 项实测否决（§0.3）；
> 第 14、15 项与 D-bis 绑定，暂缓（§0.3）。
> **清单里没有的、且已落地的最大一项是产物重发（§0.4）。**

**并发（零 invariant 改动，优先）**

1. `.agents/skills/nl-prover/references/subagent-dispatch-cookbook.md`：
   Explorer 宽度 2-3 → 至多 6；新增并发可验收判据（A3）
2. `.agents/skills/nl-prover/references/orchestrator-cookbook.md`：
   lemma 车道并发派发；取消波次屏障；Verifier 随 Generator 落盘即启动
3. `AGENTS.md` / `CLAUDE.md`：删除运行期"单一活跃 owner"习惯的措辞依据（逐字同步）
4. `Prover/CLAUDE.md`（形式化侧）：`sorry` 骨架成为首次 `lean-proof` 调度的前置；
   `current_wave` 强制递增；`dependencies: []` 必须并发

**必读集与产物瘦身**

5. `STATUS.md` 模板：`## History` 拆出到 `STATUS_history.md`
6. `STATUS.md` 模板：已关闭队列行归档到 `STATUS_closed.md`
7. `AGENTS.md` / `CLAUDE.md` Routing：`presentation/index.json` 移出每轮必读
8. `cli_tools/_memory/local.py`：`route_history.md` 封顶滚动
9. 新增 `cli_tools/memory.py budget`；`gate.py` 接入预算检查
10. `prompts/verifier.md`：不适用小节改一行否定答复（保留字段，保留 lint）
11. `prompts/*.md` + "Rules for All Agents #6"：停止 `logs/` 镜像，改写 `memory.py append`

**去重试与去重复**

12. `prompts/searcher.md`：候选失配后强制一次引用图遍历再返回负结果（E1）
13. `.agents/skills/nl-prover/references/subagent-dispatch-cookbook.md`：
    证明前的机械代数认证列为标准前置（E2）；对抗性 Explorer 同批派发（E3）
14. route 产物 schema 增 `family` 字段；`branch-queue-cookbook.md` 耗尽标准改按族计数（F1/F2）
15. `orchestrator-cookbook.md` / `stop-conditions.md`：宣布耗尽前跑复活检查（F3）
16. `CLAUDE.md` Routing + `orchestrator-cookbook.md`：Refiner 改条件触发（I）

**测量基础设施（Q7 建议最先做）**

17. 新增 `logs/dispatch.jsonl` 写入约定（H4）
18. `cli_tools/_gate/speed.py` + `gate.py speed` 子命令（J）
19. `_gate/stop.py`：要求 `RUN_TIMES.md` 与 `dispatch.jsonl`（H3）
20. `tests/harness_tools/test_speed_gate.py` 覆盖 §5 用例 A–H
21. `docs/adrs/README.md` 索引更新（本次已更新）
