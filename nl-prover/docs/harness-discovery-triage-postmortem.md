# NL-Prover Harness 发现阶段复盘：Ramanujan Challenge 2.5

## 文档状态

- 状态：改进提案，尚未并入现行 harness 规范
- 范围：候选发现、数值侦察、路线重置和证明阶段之间的接口
- 案例：Ramanujan Challenge 2.5 的矩阵乘积极限

本文不是对 Challenge 2.5 的数学证明，也不改变任何已经接受的
Verifier 结论。它分析一次具体的候选发现失败，并提出 harness 层面的改进，
目标是在不降低最终证明标准的前提下，让系统更早发现低成本、结构明确的候选。

## 结论摘要

这次失败不能完全归因于 harness，但 harness 对失败有实质性的放大作用。

直接的执行错误是：

1. 对经过变换的标量坐标做了识别，没有先识别自然归一化后的原始极限方向；
2. 冻结的 PSLQ 基底遗漏了 \(\log 2\)；
3. 将人类给出的系数行按错误顺序解释；
4. 没有尽早检查初始矩阵的秩、核以及两个初始行的叉积；
5. 人类提示“初始数值可能有用”以后，没有触发一次从原始输入重新开始的轻量审计。

这些错误即使在现有 harness 下也本可避免。因此，最终责任不能推给流程。

但是，现有 harness 缺少一个与严格证明流程明确分离的
**候选发现阶段（discovery triage）**。这使系统过早进入证明桥、来源定理、
特殊函数实现和局部 blocker 修补，导致下列简单流程被延后：

\[
\text{小规模递推}
\longrightarrow
\text{自然归一化}
\longrightarrow
\text{原坐标 PSLQ}
\longrightarrow
\text{核空间消元}
\longrightarrow
\text{精确恒等式检查}.
\]

最需要修改的不是证明标准，而是证明流程之前的候选发现和全局重置机制。

## 事件概述

题目包含一个 \(3\times3\) 矩阵递推和一个 \(2\times3\) 初始矩阵。经过符号
共轭

\[
S=\operatorname{diag}(1,-1,1),\qquad B_n=-SM(n)S,
\]

可将递推转化为正矩阵乘积

\[
C_N=B_0B_1\cdots B_{N-1}.
\]

设正坐标下的初始矩阵为

\[
A_+=AS=\begin{pmatrix}p\\q\end{pmatrix}.
\]

只需取一列 \(u_N=C_Ne_j\)，再按

\[
w_N=\frac{27000}{q\cdot u_N}u_N
\]

归一化，就能以很小的计算量得到稳定的极限方向近似。

对三个原始坐标分别在固定顺序

\[
[w_i,G,\log 2,1]
\]

上运行 PSLQ，会得到候选

\[
\begin{aligned}
w_1&=9000G-7680\log 2-2920,\\
w_2&=3050-13500G+13440\log 2,\\
w_3&=20250G-24960\log 2-1247.
\end{aligned}
\]

令

\[
T=
\begin{pmatrix}
9000&-7680&-2920\\
-13500&13440&3050\\
20250&-24960&-1247
\end{pmatrix},
\qquad
w=T\begin{pmatrix}G\\\log2\\1\end{pmatrix}.
\]

候选随后通过精确整数恒等式

\[
A_+T=
\begin{pmatrix}
27000&0&0\\
0&0&27000
\end{pmatrix}
\]

得到结构性校验。

尤其是

\[
p\times q=27000(4,-7,13),
\]

而 \(\log2\) 的系数向量满足

\[
(-7680,13440,-24960)=-1920(4,-7,13).
\]

因此 \(\log2\) 分量位于 \(A_+\) 的核方向，最终的分子和分母都看不见它。
这说明一个重要的一般现象：

> 最终标量答案只包含某个常数，并不意味着内部极限方向只能由该常数表示；
> 其他 period 可能完全落在初始观测映射的核中。

上述内容构成强候选及其有限、精确的一致性检查，但不是完整极限证明。
仍需证明候选射线确实是所有矩阵列的共同极限，例如证明
\(C_N^{-1}w>0\) 对所有 \(N\) 成立，再结合正矩阵的射影收缩。

## 实际探索为什么偏离

### 1. 把“尚未发现候选”误诊为“缺少高级证明桥”

在没有得到自然极限方向闭式之前，流程已经开始寻找：

- Delannoy/WZ 型表示；
- Hermite–Padé 和 branched Stieltjes 模型；
- Hahn、Racah 和 bispectral 构造；
- Mellin、Euler–Beta 和超几何函数接口；
- Jost 解、Wronskian、渐近模态和不变锥。

这些工具可能与最终的全 \(N\) 证明有关，但不应先于基础数值侦察。
系统实际上在试图证明一个尚未正确识别的对象。

### 2. 防止过拟合的规则被错误地应用于候选发现

冻结坐标、常数基底、系数高度和留出深度，本意是防止看到输出后不断扩大
搜索空间。这对于一个定义完整的单次 PSLQ 实验是合理的。

问题在于，旧实验使用的是变换后的标量坐标，并且基底为

\[
\{1,\sqrt2,G,\sqrt2G\},
\]

其中没有 \(\log2\)。实验失败以后，冻结规则事实上阻止了对以下新对象的
自然检查：

- 三个原始归一化坐标 \(w_i\)；
- 人类明确提供的新常数 \(\log2\)；
- 初始矩阵核所允许的“不可见 period”。

旧实验的冻结范围应只覆盖“旧坐标、旧基底、旧归一化”这一具体实验，
不应成为后续不同实验的全局禁令。

### 3. 局部 blocker 路由压过了全局重新阅读

“选择当前 blocker 的最小 specialist”适合修复已知证明路线，但连续使用会
造成局部最优化：每个代理都解决上一份文件留下的最小缺口，却没有代理定期
重新检查：

- 原题的每一项输入是否都已被使用；
- 是否存在更自然的坐标；
- 新的人类线索是否改变了问题表示；
- 当前 blocker 是否只是错误建模的产物。

这次初始矩阵 \(A\) 的核就是被低估的原始输入。

### 4. 长期负面记忆可能造成路线锚定

长期 memory 对避免重复失败很有价值，但如果它在每轮最先进入上下文，且缺少
严格的作用域说明，就可能让系统优先思考“哪些路线已经关闭”，而不是
“最新证据是否定义了一个不同的问题表示”。

负面结论必须绑定到：

- 精确坐标；
- 精确归一化；
- 精确常数基底；
- 精确参数盒；
- 精确构造约定。

一个坐标上的 PSLQ 失败不能关闭另一个坐标上的 PSLQ；一个不含 \(\log2\)
的基底失败也不能成为排除 \(\log2\) 的证据。

### 5. Hub-and-spoke 增加了低成本反馈的延迟

Orchestrator 不得承担 Explorer、Synthesizer 或 Code Executor 的职责，这对
所有权和审计有好处，但也意味着一个十几行的只读 sanity check 需要完整的
调度、产物和回收过程。

问题不一定要通过放宽 Orchestrator 的数学权限解决。更安全的办法是定义一个
低开销、标准化的 `DISCOVERY_TRIAGE` Code Executor 模式，并在适用题型上
强制首先调度它。

## Harness 与执行责任的边界

### Harness 确实放大的问题

- 没有明确区分 conjecture discovery 与 proof certification；
- blocker-first 路由缺少周期性的 global reset；
- 冻结实验缺少严格的作用域和失效条件；
- 人类新证据没有自动触发独立、只读的重新审计；
- 长期负面记忆容易压过原始目标和最新线索；
- 没有要求在高级路线之前审计每一个打印输入的作用。

### 不能归因于 Harness 的问题

- 小规模整数递推并未被禁止；
- 资源限制足以容纳几十步 \(3\times3\) 矩阵乘法；
- 没有任何规则要求遗漏 \(\log2\)；
- 没有任何规则禁止检查 \(A_+\) 的秩和核；
- 系数排列只有少数可能时，本可全部机械测试；
- 人类已经多次建议高精度、归一化、PSLQ 和利用初始数据。

因此，正确结论是：

> Harness 造成了路线偏置、认知锚定和反馈迟缓；执行过程则没有使用廉价的
> 基础检查及时纠正这些偏置。

## 建议的流程设计

### 阶段 A：Discovery Triage

目标是快速产生可证伪、可精确检查的候选，不产生数学 `PASS`。

允许：

- 小规模精确或高精度递推；
- 自然坐标和归一化的比较；
- 有限、预先声明的 PSLQ；
- 观察模式和提出猜想；
- 未使用深度上的留出检验；
- 精确代数残差、核空间和矩阵恒等式检查。

输出状态只能是：

- `DISCOVERY_CANDIDATE`；
- `NO_CANDIDATE_IN_DECLARED_BOX`；
- `AMBIGUOUS_INPUT_AFTER_CHEAP_ENUMERATION`。

不得把数值符合、PSLQ 或有限检查提升为证明。

### 阶段 B：Proof Route

候选固定以后，再进入现有的严格流程：

- 接受目标读法；
- 建立 proof-obligation ledger；
- 为全指标陈述构造证明；
- 审计命名定理和来源；
- 由 Generator 编写；
- 由 fresh Verifier 检查。

发现阶段和证明阶段应共享候选定义，但不能共享结论等级。

## 建议加入 `AGENTS.md` 的规范文本

以下英文文本可以作为后续 ADR 或实现变更的起点。

```text
## Mandatory Discovery Triage

Before opening structural proof branches for a numerical recurrence,
matrix-product limit, or special-constant identity, dispatch one lightweight
Code Executor in DISCOVERY_TRIAGE mode.

The probe must:

1. Account for every datum printed in the target, including initial vectors,
   initial matrices, normalizations, and boundary values.
2. Inspect ranks, kernels, determinants, sign conjugations, and simple
   invariant linear functionals.
3. Compute a small, resource-bounded set of iterates.
4. Examine raw coordinates, projective ratios, and each natural normalization.
5. For constants named by the target or explicitly suggested by the human,
   run bounded integer-relation tests on each natural coordinate.
6. Permit nuisance periods that may lie in the kernel of the final observation
   map and therefore disappear from the stated scalar limit.
7. Validate every candidate at untouched depths and by exact symbolic
   residuals whenever possible.

Discovery output is conjectural evidence only. It is not mathematical
verification, does not discharge a proof obligation, and cannot be merged into
proof.tex without the ordinary specialist and fresh-Verifier workflow.
```

```text
## Discovery Reset Triggers

- A new human-supplied coefficient vector, normalization, coordinate, or
  constant basis starts a new read-only discovery experiment. It is not barred
  by a frozen contract belonging to an older experiment.
- Frozen numerical contracts are scoped to their exact coordinate,
  normalization, basis, coefficient bound, and depth set.
- If a coefficient ordering is ambiguous and the plausible permutation set is
  small, mechanically test all plausible orders before requesting human
  clarification.
- After three failed structural branches, dispatch an independent Synthesizer
  that first rereads the original target, raw finite evidence, and newest human
  clues without reading route conclusions. It may consult route history only
  after producing a baseline re-analysis.
- A negative result in one coordinate chart or constant basis must not be
  generalized to another chart or basis.
```

```text
## Observation-Kernel Audit

When an r-by-(r+1) initial matrix observes a projective limit, compute and
record its kernel before constant recognition. Test whether companion periods
or logarithmic terms can occur entirely along that kernel and hence vanish
from every final observed ratio.
```

## 与现有角色体系的兼容实现

无需允许 Orchestrator 自己证明或验证数学。可以采用以下最小改动：

1. 在 `prompts/code_executor.md` 增加 `DISCOVERY_TRIAGE` 模式；
2. 在 dispatch cookbook 中加入适用题型的强制首个轻量任务；
3. 为该模式定义固定的资源上限和标准报告格式；
4. 报告只能写入 `routes/` 或独立 discovery 目录；
5. 报告明确列出“候选”和“仍未证明的无限义务”；
6. 只有候选通过精确残差和留出检查后，才允许进入 Sketcher/Explorer 的正式
   proof-route 选择。

这样可以保留以下现有优点：

- Orchestrator 不拥有数学内容；
- 计算证据不冒充证明；
- Verifier 保持 fresh 和 stateless；
- `proof.tex` 仍只接收验证通过的内容；
- 所有发现实验仍有可复现文件和资源记录。

## 建议的标准检查清单

对于矩阵递推或极限常数题，Discovery Triage 至少检查：

- [ ] 原题中的每一个矩阵、向量、初始值和标量是否被显式使用；
- [ ] 是否存在对角符号共轭，使矩阵进入正锥；
- [ ] 单步矩阵是否可逆，行列式是否有简单因子分解；
- [ ] 初始观测矩阵的秩、核和所有低维叉积；
- [ ] 20–50 步以内的原始列方向是否稳定；
- [ ] 每一种自然归一化是否稳定；
- [ ] 原坐标、比例坐标和变换坐标是否都被区分记录；
- [ ] 题目常数、人类提示常数和相邻已验证计算中的 companion periods；
- [ ] PSLQ 输入顺序是否在报告中逐项写明；
- [ ] 少量可能的系数排列是否全部机械测试；
- [ ] 候选是否在未参与识别的深度上通过；
- [ ] 候选是否产生精确矩阵恒等式或精确递推残差；
- [ ] 最终观测映射是否消去了某个隐藏 period；
- [ ] 报告是否明确列出尚未证明的全指标义务。

## 回归测试建议

可以将本案例抽象成一个 harness 回归测试。测试不要求系统证明 Challenge
2.5，只要求它在固定资源预算内完成候选发现。

建议验收条件：

1. 首个 discovery probe 使用全部打印输入，包括初始矩阵；
2. 在不读取预存闭式的条件下，形成自然归一化的三维方向；
3. PSLQ 报告明确写出输入顺序；
4. 当人类提供 \(\log2\) 或对应系数时，旧的不含 \(\log2\) 的冻结实验不会
   阻止新实验；
5. 计算并记录初始观测矩阵的核；
6. 发现 \(\log2\) 系数沿核方向；
7. 精确检查 \(A_+T\)；
8. 将结果标为 candidate，而不是 proof；
9. 将“证明候选是全 \(N\) 极限射线”记录为独立 proof obligation。

## 风险与缓解

### 风险：开放 PSLQ 会产生过拟合

缓解：

- 小而明确的基底；
- 预先声明系数高度；
- 独立留出深度；
- 精确残差；
- 候选不得直接进入 `proof.tex`。

### 风险：Discovery Triage 变成新的固定流水线

缓解：

- 只对数值递推、矩阵极限和特殊常数识别等适用题型触发；
- 设严格的小资源预算；
- 它只产生候选，不决定后续证明路线；
- 对纯理论题允许记录 `NOT_APPLICABLE`。

### 风险：重新分析会重复已经关闭的路线

缓解：

- global reset 首先忽略路线结论，但仍受精确目标和资源上限约束；
- 基线分析完成后再与 negative memory 对照；
- negative memory 的每条结论必须带精确作用域。

### 风险：角色和文件数量继续膨胀

缓解：

- 不新增代理种类，优先复用 Code Executor 的一个模式；
- 使用单一标准 discovery 报告；
- 在 SSOT 中只定义一次触发规则，其余文档使用链接。

## 最终建议

保留 NL-Prover 当前严格的证明、来源和验证制度，但在它之前增加一个廉价、
明确降级为“猜测证据”的 Discovery Triage。

本次案例表明，复杂证明路线并非没有价值；问题是它们在候选尚未正确识别时
过早启动。合理顺序应是：

\[
\boxed{\text{原始输入审计与低成本候选发现}}
\longrightarrow
\boxed{\text{精确一致性检查}}
\longrightarrow
\boxed{\text{全指标证明路线}}
\longrightarrow
\boxed{\text{fresh verification}}.
\]

这样既不会牺牲 NL-Prover 的证明可靠性，也能显著降低因错误坐标、遗漏常数、
局部路线锚定和初始数据未使用而造成的长时间偏航。
