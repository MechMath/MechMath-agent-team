# ADR 0015: Scholar 内化阶段与经验卡片库(借鉴 AhhProver study 模块)

## Status

Superseded / 部分搁置(中文初稿)。**本 ADR 已向 ADR 0016 对齐** —— 其分层模型、分派规则与三级入口以 ADR 0016 为准,长期层的存储归属以 ADR 0017 为准。下方"Decision/Consequences/Implementation"保留为**设计素材与出处**,不代表当前决定。

## 与 0016/0017 的同步说明(阅读本 ADR 前必读)

**命名。** 下文一律出现的 **Collector** 即本仓的 **KB-Manager**(论文 §3.3 的知识库;代码工具仍名 `collector-write` 等,wiki 仍在 `DATA_DIR/wiki/`)。

**归属映射(以此为准,正文与之冲突处以此为准):**

| 本 ADR 原主张 | 现行决定 | 依据 |
|----------------|----------|------|
| 三分知识边界(陈述性/程序性/问题局部) | 采纳,并入论文三层记忆模型 | ADR 0016 §1、§3.1 |
| 卡片以 `Trigger`/`Failure modes` 为承重字段 | **采纳** | ADR 0016 §3.3 |
| 新建独立经验卡库 `DATA_DIR/library/`(lessons/episodes) | **不采纳**:不建第二存储,长期卡并入 KB-Manager | ADR 0017 |
| `seed → edit → promote` 机制 | 机制保留;六步详解见 | ADR 0016 §3.5 |
| Scholar 内化阶段(第 3 节) | **搁置**:消化/内化倾向归 KB-Manager;16–20 已覆盖主要缺口 | ADR 0016 §3.5、§2 诊断 |
| Reflector specialist + `library_tools.py`(第 2 节) | **搁置**:蒸馏归属与推进待定(倾向 KB-Manager) | ADR 0016 §3.5、§7 Q2 |

**一句话:** 卡片格式与"程序性经验 vs 陈述性事实"的分界被保留并吸收进 0016;而"新建独立库 + 新增 Scholar/Reflector agent + `library_tools.py`"这套落地方案**暂缓搁置**,不在当前推进范围。

## Context

### 借鉴来源

AhhProver 的流水线是 `collect → study → sketch → prove → reflect`,其中
`study` 阶段(Scholar 角色)在"收集资料"与"开始证明"之间插入一个显式的
**学习/内化**步骤,`reflect` 阶段(Reflector 角色)在一题做完后蒸馏
**做题经验**。两者共同维护一个跨问题持久的卡片库,机制上有三个值得移植
的设计:

1. **卡片格式以 Trigger 和 Failure modes 为承重字段**:一张卡必须说清
   "看到什么结构线索时该想起我"和"我什么时候会背叛你",否则只是引文。
2. **seed → 原地编辑 → promote 的库更新机制**:Python 把当前库种子拷贝
   到工作区,agent 原地编辑;未改动的字节不经过模型,防止懒惰全量重写
   静默丢失条目;只有内容真正变化的文件才提升回库,提升前快照可回滚,
   种子非空却回来空文件的拒绝提升。(该机制的六步详解见 ADR 0016 §3.5。)
3. **主动回忆自检**:Scholar 写完知识层后"合上书"复述前置条件、检查
   特化代入,纠错回写,而不是停在第一稿摘抄。

### NL-Prover 现状的两个短板

1. **KB-Manager 与 Sketcher 之间没有"消化"层。** Sketcher 拿到的是原始
   query 结果和论文笔记,没有人把文献预编译成本问题记号下的特化引理、
   知识地图和候选攻击路线。
   (评审结论:此"消化/内化"职责倾向归 KB-Manager;本 ADR 第 3 节的
   Scholar 内化方案**搁置**——见顶部同步说明。)
2. **跨问题记忆弱且靠 prompt 纪律维护。** 现在只有一个 100 行封顶的
   `memory.md`(扁平错误规则列表)。route_history、recovery packets、
   被 DISPROVE 的引理、人类提示纠正过什么——这些经验没有人蒸馏成
   跨问题可复用的结构化教训。ADR 0012 已指出方向(memory channels、
   AI 可读索引、granularity 控制)。
   (经验记忆的最终模型见 ADR 0016;长期层存储归属见 ADR 0017。)

### 两个已知风险(本 ADR 必须正面回答)

**风险 A:与 KB-Manager 知识库重复。** KB-Manager wiki 已有定理/定义/来源
页,以及 `*ErrorKnowledge`、`*CounterexampleKnowledge`、`Analysis_*` 页;
现有流程中验证通过的引理也经 collector-write 入库。若照搬 AhhProver 的
共享库三件套(toolbox/lessons/episodes),等于建第二个知识库,且两份
定理陈述会漂移。
(评审结论:无需照搬三件套,沿用 KB-Manager 既有结构;长期卡并入 KB-Manager
而非新建独立库——见 ADR 0017。)

**风险 B:内化阶段占用上下文,增加 Orchestrator 压力。** Scholar 产出
的 toolbox/map/attack_plans 若被注入 Orchestrator 或下游 agent 的
prompt,长跑中会持续消耗上下文预算,与 ADR 0012"短索引、按需展开"的
方向相悖。
(评审结论:内化职责倾向归 KB-Manager;第 3 节的独立 Scholar 内化阶段
**搁置**,因 ADR 0016–0020 已覆盖主要缺口。)

## Decision

> **注:以下为原始设计素材。** 推进/存储/命名的现行决定以顶部"同步说明"为准;
> 其中"新建独立 `library/` + Scholar/Reflector agent + `library_tools.py`"整套
> 落地方案**当前搁置**。

### 1. 知识分界:图书馆与做题本

按知识类型划分唯一权威,杜绝重复:

| 知识类型 | 内容 | 归属 | 读取方式 |
|----------|------|------|----------|
| 陈述性 | 定理、定义、来源、反例的精确陈述 | **Collector wiki**(唯一权威) | 拉取式:query 工作流按需深读 |
| 程序性/经验性 | Trigger、Failure modes、使用记录、做题经历、错误模式 | **经验卡片库** `library/` | 推送式:单行索引注入 prompt,全文按 Trigger 命中才读 |
| 问题局部 | 本问题记号下的特化引理、知识地图、攻击路线 | **workspace `knowledge/`**(随问题生灭) | 下游 specialist 按需读文件 |

硬规则:**经验卡片禁止收录完整定理陈述**。若一条经验绑定某个定理,
卡片只存 Trigger / Failure modes / 使用记录,陈述以指针引用 Collector
wiki 页或 arXiv 来源(`Source: wiki/<page>` 或 `2401.12345, Thm 3.2`)。
AhhProver 共享库中"通用形式定理卡"的那一半**不移植**——那是 Collector
的职责。wiki 既有的 ErrorKnowledge 页保留为历史沉淀,新的运行经验统一
写卡片库。

### 2. 第一期:Reflector 与经验卡片库(memory.md 的升级形态)

**库的位置与构成。** `DATA_DIR/library/`(跨问题持久),仅两个文件:

- `lessons.md` — skill / error / schema 卡:有效战术、复发陷阱、已知
  障碍。现有 `memory.md` 的条目一次性迁移为卡片格式,`memory.md` 之后
  退役为指向库索引的存根。
- `episodes.md` — 每题一条经历卡:走了哪些路线、哪条死了为什么、哪些
  引理被 DISPROVE、人类提示纠正了什么。仅 Reflector 可写。

**卡片格式**(承袭 AhhProver,去掉陈述性字段):

```markdown
## <stable-slug>: <名称>
- **Type**: skill | schema | error | episode
- **Claim**: 一句话经验(技术本身或错误模式,非定理陈述)
- **Trigger**: 什么结构线索出现时该想起这张卡
- **Failure modes**: 何时不适用 / 套用时典型翻车方式
- **Source**: wiki 页指针、arXiv 标签或 `problem <id>`(经验来源)
- **Used**: `<problem_id> <stage> ✓|✗ (一行注记)` — 只追加
```

slug 一经写下不再重命名;`Used` 行只追加。

**Reflector specialist。** 新增 `.codex/agents/reflector.toml` +
`prompts/reflector.md`。输入:STATUS.md、route_history、recovery
packets、review packets 中的 DISPROVED 引理、人类提示记录。产物:原地
编辑种子化的 `lessons.md` / `episodes.md`。派发时机:一次运行终结
(verified proof / verified obstruction / 分支预算耗尽 / 人类叫停)后,
由 Orchestrator 作为**侧支**派发——不改变数学停机状态,失败不阻塞主流程。

**库机制 CLI。** 新增 `cli_tools/library_tools.py`(seed / promote /
snapshot / index 四个子命令),移植 AhhProver `scholar.py` 的库机制并
遵守其防护:byte-diff 才提升、提升前快照到 `library/.history/<ts>/`、
拒绝空文件覆盖非空种子。配套 skill `.agents/skills/library/SKILL.md`
说明触发时机与 compact/summary/full 粒度。这是机械索引工具,按
invariant 16 不构成数学验证。

**膨胀控制(crystallize, not accumulate)。** 索引以"每卡一行"计,
上限 80 行;promote 时超限即失败,Reflector 必须先合并近重复卡片
(merge-first:同一经验只允许一张卡)再提交。这继承了 memory.md
"100 行封顶、合并压缩而非盲目追加"的既有纪律。

### 3. 第二期:Scholar 内化阶段

新增 `.codex/agents/scholar.toml` + `prompts/scholar.md`。Orchestrator
在 Collector 查询/文献收集完成后、Sketcher 之前**可选**派发(见第 4 节
预算规则)。输入:`queries/<query_id>/` 结果、reference_extract 产出的
论文笔记、库索引。产物写 workspace `knowledge/`:

- `toolbox.md` — 每条可用结果以**本问题记号**重写,含特化形式(具体
  对象代入后定理实际说了什么)、前置条件、Trigger、失败模式、来源标签
  及 proved/attributed 标记(对接 invariant 10 与 Searcher)。
- `map.md` — 结果间强弱/特例关系、gap 清单、已被排除的死路。
- `attack_plans.md` — 2–4 条候选路线,每条注明所用 toolbox 条目、关键
  剩余 gap、风险点;直接作为 Explorer/Synthesizer 分支队列的输入。

Scholar 必须执行主动回忆自检(合上来源复述前置条件、核对特化代入),
纠错回写。`knowledge/` 一切内容必须可追溯到 query 结果或论文笔记,
不得发明结果。Scholar 不写 `library/`(经验蒸馏归 Reflector,职责
单一);若发现值得入 wiki 的陈述性内容,走 collector-write inbox。

### 4. 上下文预算:为什么内化不增加 Orchestrator 压力(风险 B 的回答)

设计原则:**Scholar 烧自己的上下文,落盘成文件;Orchestrator 只读
单行级索引;下游按需读取**。

1. **Scholar 是独立 subagent**(hub-and-spoke 的又一根辐条)。读论文、
   重写记号、自检的全部 token 消耗发生在它自己的上下文里,结束即释放。
   Orchestrator 派发它的成本与派发一次 Collector 查询同阶。
2. **Orchestrator 永不读 toolbox 全文**。它只读两样:`knowledge/`
   完成回执(一行)和 `attack_plans.md` 的路线清单(每条路线一行,
   ≤ 4 行),用于喂分支队列。`workspace_memory.py refresh` 把
   `knowledge/*` 纳入机械索引即可。
3. **下游按需、按命中读取**。Sketcher 读 `attack_plans.md` + `map.md`
   (短);Generator 只在其引理触及某 toolbox 条目的 Trigger 时读该
   条目,不整读 `toolbox.md`。粒度遵循 ADR 0012 的 compact → summary
   → full。
4. **库索引注入有硬上限**(80 行,见第 2 节),且只注入给 Scholar、
   Sketcher、Explorer 这类策略型 agent;Verifier 保持无状态新鲜
   (invariant 3),不注入任何库内容,避免锚定。
5. **净效果预期是省上下文而非费上下文**:没有内化层时,Sketcher 和
   每个 Generator 都要各自重读原始 query 结果与论文笔记,同样的消化
   工作在多个 agent 的上下文里重复发生;内化层把这件事做一次、落盘、
   复用。toolbox 的特化引理是"预编译"产物,下游直接引用。
6. **小问题跳过**。派发 Scholar 的触发条件:query/文献产出超过阈值
   (建议:≥ 3 个 query 目录或 ≥ 2 篇深读论文)且路线尚不明朗。材料
   少时 Sketcher 直接读原始笔记,不引入额外一跳。

### 5. 与现有不变量的兼容性

- Scholar / Reflector 均为 spoke,只写各自工作区(`knowledge/`、
  种子化的 `library_update/`),不碰 `proof.tex`(invariant 1, 5, 14)。
- 卡片库与 `knowledge/` 是机械索引/参考材料,不构成数学验证;一切
  数学采信仍走 fresh Verifier(invariant 3, 12, 16)。
- toolbox 的 proved/attributed 标记只是线索,具名定理上场前仍须走
  Searcher 与 invariant 10 的记录流程。
- Reflector 是侧支,不推进也不改变停机判定(invariant 11)。

## Consequences

**优点**:跨问题经验首次结构化、可触发召回、可回滚;文献消化从"每个
agent 各读一遍"变为"读一遍、落盘、复用";与 Collector 职责互补无重叠
(陈述性 vs 程序性);全部以 specialist + skill + CLI 落地,不动
hub-and-spoke 架构。

**缺点与缓解**:
- 新增两个 specialist 与一组 CLI,编排面变大 → 分两期落地,第一期
  (Reflector + 库)独立可用,Scholar 可后置。
- 卡片质量依赖 Reflector 蒸馏水平,坏卡会误导后续问题 → Trigger /
  Failure modes 为必填承重字段;`Used ✗` 记录累积后人工或 Reflector
  降级删卡;`.history/` 可回滚。
- Scholar 多一跳可能延迟小问题 → 第 4.6 节阈值规则,小问题不派发。
- 库索引仍占少量固定 prompt 预算 → 80 行硬上限 + merge-first 纪律。

## Implementation Plan(接受后)

1. 第一期:`library_tools.py` + `library` skill + Reflector agent/prompt
   + `memory.md` 条目迁移 + orchestration.md 路由规则(终结后侧支派发)。
2. 第二期:Scholar agent/prompt + `knowledge/` 产物规范 + Sketcher/
   Generator prompt 的按需读取指引 + 派发阈值规则。
3. 两期各配最小测试:seed/promote/snapshot 的 byte-diff 与拒绝空写;
   索引行数上限;promote 后 `.history/` 快照存在。
