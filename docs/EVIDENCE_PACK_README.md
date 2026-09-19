# HSTA v13 Evidence Pack

这个目录下的脚本用来**补齐论文里最关键的缺失证据**，并把所有表格从原始运行记录重新生成一遍。

> **重要前提**：本目录的脚本只负责读取运行记录、构建模型探针和生成配置；新增训练实验仍需在项目规定的 WSL GPU 环境中运行。本版已在 WSL 中复核参数探针和无 GPU 计算器，未把任何未实测的训练结果写入文档。

---

## 1. 这套脚本解决什么问题

| # | 问题 | 对应脚本 | 产出 |
|---|---|---|---|
| 1 | **Table 4 的 "No Attention" 一行没有实验记录。** `configs/hsta_no_attention.yaml` 声明了 12 个实验，`AGENTS.md` 也把 `results/hsta_no_attention` 列为实验组，但该目录在磁盘上不存在 | `configs/hsta_no_attention_v13.yaml` + `run_evidence_pack.sh stage_ablation` | 12 次真实运行的 `metrics.json` |
| 2 | **"参数少 41.5%" 是对着 depth=5 的 Transformer 比出来的。** HSTA 实际只有 2 个 Mamba block + 2 个 FFN，而 GRU/Transformer 统一配了 depth=5 | `alignment_models.py` + `run_evidence_pack.sh stage_alignment` | 参数对齐的 Transformer/Mamba 基线，以及精确的参数对照表 |
| 3 | **全文没有任何统计检验**，而核心结论建立在 0.4–2.0 个百分点的差距上，部分对照的标准差与之同量级 | `aggregate_evidence.py` | 逐任务、逐对照的 Welch t 检验 + 配对检验，以及统计功效警告 |
| 4 | 各表格由人工手抄，无法追溯到单次运行 | `aggregate_evidence.py` | 从 `metrics.json` 重算的 `summary.csv` / `pairwise.csv` / `coverage.csv` |

### 顺带修掉的两个同类可比性缺陷

调查配置时发现，`configs/hsta_no_attention.yaml` **没有设置 `attention_backend`**，因此落到模型默认值 `manual`，而 HSTA 主实验（`configs/hsta_flash.yaml`）用的是 `flash`。**"无注意力"这个对照本来要和主实验比，却处在不同的注意力后端设定下。** 新的 `_v13` 配置显式设为 `flash`，使唯一的差别只剩布局。

另外，`mamba|mamba|mlp|mlp|mlp` 这个布局是**用第三个 FFN 替换掉注意力块**，等深但**不等参**，所以它不是 HSTA 的等容量对照；论文原文 "uses an additional feed-forward module" 的措辞也读起来像"增加"而非"替换"。**它的参数量差距请用 `probe` 实测后写进论文，不要估算。**

---

## 2. 已经在记录里核实过的事实（供对照）

以下数字来自已存在的 `metrics.json`，我已逐项重算并确认与投稿版论文**逐位一致**：

| 项 | 数值 |
|---|---|
| HSTA 参数量（40 类任务） | 602,408 |
| HSTA 参数量（60 类任务） | 604,988 |
| Transformer (depth=5) 参数量 | 1,030,312 / 1,032,892 |
| GRU (depth=5) 参数量 | 452,776 / 455,356 |
| Front / Middle 注意力变体参数量 | **与 HSTA 完全相同**（602,408 / 604,988） |
| No Attention 变体 | **无任何运行记录** |

**可以确定的一点**：Front / Middle 与 HSTA 参数量完全一致，所以 **HSTA vs Front、HSTA vs Middle 是干净的等容量对照**，这两组结论是可信的。No Attention 不是，必须在论文里如实说明。

---

## 3. 怎么跑

在 **WSL (Ubuntu-22.04)** 里，从仓库根目录执行：

```bash
cd /mnt/e/AllProject/流量分析python项目/HSTA
```

### 步骤 0：先测量参数量（不训练，几秒钟）

```bash
bash scripts/run_evidence_pack.sh probe
```

会打印每个候选模型（Transformer / Mamba / GRU / 30pktTCNET，depth 1–5）的**实测参数量**，并自动生成
`configs/alignment_baselines_v13.yaml`（参数最接近 HSTA 的那一档）。

### 步骤 1：补跑缺失的 No Attention 消融（最高优先级）

```bash
# 串行，约 4–7 小时
bash scripts/run_evidence_pack.sh stage_ablation

# 或 3 个 worker 并行，约 1.5–2.5 小时（显存够的话）
bash scripts/run_evidence_pack.sh parallel_ablation 3
```

> **并行模式的隔离机制**：每个 worker 写入私有 scratch 根目录（`logs/_scratch_*`），全部跑完后**统一合并**回 `results/hsta_no_attention_v13/`。
> 这样做是必要的：`run_experiments.py --resume` 只要看到 `summary.csv` 与 `best.pt` 存在就会跳过该实验，**如果多个 worker 共用一个输出目录，就可能看到另一个 worker 尚未写完的运行而误跳过真实工作**。scratch 放在 `logs/` 而不是 `results/` 下，是为了避免聚合脚本发现重复副本。

### 步骤 2：跑参数对齐基线（**24 次运行，约 7–13 小时串行**，仅 QUIC-60）

```bash
bash scripts/run_evidence_pack.sh stage_alignment
# 或
bash scripts/run_evidence_pack.sh parallel_alignment 3
```

**配置已收敛为 QUIC-60 单任务 × 6 种子 × 4 个模型 = 24 次运行**（3 个 worker 时约 2–3 小时）。各模型的 depth 按 `probe` 的**实测**参数量选定：

| 模型 | depth | 参数量(60类) | vs HSTA | 角色 |
|---|---|---|---|---|
| **transformer** | **3** | **636,348** | **+5.2%** | **等参数量对照（最关键）** |
| netmamba_adapted | 5 | 624,956 | +3.3% | 状态空间对照 |
| 30pktTCNET-adapted | 5 | 520,636 | −13.9% | 仅保持深度一致 |
| gru | 5 | 455,356 | −24.7% | 仅保持深度一致 |

> ⚠️ **`gru` 不是等参数量对照**（比 HSTA 小 24.7%），**绝不能**用它声称参数优势；它只是为了所有基线在同一深度下报告。
> ⚠️ **`transformer depth3` 是本组最重要的对照**：若 HSTA 赢不了它，"参数少 41.5%"这套说法必须改成"**等参数量下精度相当**"，depth=5 的对比只能作为语境。
> ⚠️ SRViT / TrafficAudio / BPF-GNN **不做等深度重跑**（属结构重实现，重调是另一项大工程）；它们的 `depth=4` 配置必须在论文中**如实披露**并附参数量。

### 步骤 3：重新生成全部表格与统计检验

```bash
bash scripts/run_evidence_pack.sh report
```

产出在 `results/evidence_report/`：

| 文件 | 内容 |
|---|---|
| `summary.md` | 人读版：覆盖情况 + 各变体均值±标准差 + 全部两两检验 |
| `summary.csv` | 机读版：每 模型×任务 一行 |
| `pairwise.csv` | 每个对照一行：Δ(百分点)、Welch p、配对方法、配对 p |
| `coverage.csv` | **哪些实验真的存在、哪些缺失**（这一张表就是 A1 问题的答案） |
| `runs.csv` | 全部单次运行记录，可追溯到 seed |

---

## 4. 关于统计功效：一定要看这一段

脚本会显式打印警告，因为这里有个**容易被忽略的硬约束**：

> **在 n=3 个种子下，精确 Wilcoxon 符号秩检验的最小可能 p 值是 2/2³ = 0.25。**
> 也就是说，**无论差距多大，3 个种子都做不出 p < 0.05。**

所以：

- 现在的 3 种子结果**不能用来声称显著性**；得到不显著的结果是"检验没有功效"，而**不是**"效应不存在"的证据。
- 脚本因此以 **Welch t 检验为主**（它没有这个下界），配对检验只在 n ≥ 6 时才报 Wilcoxon，否则退回精确符号检验并标注方法名。
- **要把显著性写成结论，种子数至少要提到 6，最好 10。** 这一项在你当前"时间很紧"的约束下无法完成，建议作为改投前的**必做项**排进下一轮。

---

## 5. 结果出来之后怎么写（不要提前写）

**在 `stage_ablation` 真正跑完之前，不要动论文里 No Attention 那一行。** 三种可能的结果对应三种写法：

1. **No Attention 明显低于 HSTA（差 ≥ 1 个百分点，且超过标准差）**
   → 论文的核心论点成立，可以把"注意力模块本身有价值"写成结论，并保留"顺序重要"的表述。

2. **No Attention 与 HSTA 接近（差距在标准差内）**
   → **必须重写整个消融章节和结论**。此时正确的结论是"在轻量侧包输入下，注意力模块的边际贡献有限，HSTA 的收益主要来自状态空间编码"，这会显著改变论文的贡献定位。

3. **No Attention 高于某些注意力变体**（含 Front/Middle）
   → 与现有 Front/Middle 数据一致，应把结论收敛为"**只有后置注意力有效**"，并解释机制（状态空间编码必须先建立上下文，注意力才有作用对象），而不是笼统地说"顺序很重要"。

由于 Front(88.33) 与 No Attention(88.29) 在 QUIC-60 上几乎相同、而 Middle(87.95) 更低，**情况 3 是相当可能的**。请做好准备。

---

## 6. 仍然缺失、本包**没有**解决的证据

这些是论文的其余短板，需要另行安排（详见 `HSTA_JNCA拒稿自查与修改方案.md` 第 6 节第 3 阶段）：

- [ ] 种子数提到 6–10（否则显著性无法成立）
- [ ] 跨数据集泛化 + 量化衰减（JNCA 同类论文的标配）
- [ ] CPU 推理 / P99 延迟 / 内存 / throughput（论文声明了 throughput 但表中没有）
- [ ] 开放集（unknown 类拒识）实验
- [ ] 数据再采样与类别频次扫描过程的披露（`init_train_size=1M`、`scan_batches=300`）
- [ ] 5 条 2026 年引用的元数据逐条核实
- [ ] 代码仓库改名/对齐 HSTA
- [ ] Graphical Abstract

---

## 7. 比例研究（Mamba:Attention = 2:1）—— 本次修订的核心实验

原始投稿**完全没有比例证据**：磁盘上所有 HSTA 系列运行都是 2 Mamba + 1 attention，所以"2:1 效果好"从未被验证过；而且 Front/Middle 也是 2:1 却低约 2 个百分点，说明**比例和排列在现有数据里是混淆的**。

| 文件 | 作用 |
|---|---|
| `configs/ratio_scale_v13.yaml` | 5 个比例臂，**6 种子**，按三个 tier 组织，共 60 次运行 |
| `scripts/ratio_calculator.py` | **不训练**，几秒钟算出所有臂的参数量并给出设计建议 |
| `scripts/ratio_analysis.py` | 从 `metrics.json` 的 `layout` 还原比例，出比例曲线表 + 判定 |

**五个臂（placement 完全固定，只变 Mamba 块数）：**

```
1:0   mamba|mlp
1:1   mamba|mlp|attention|mlp
2:1   mamba|mamba|mlp|attention|mlp        <- 论文提出的配方
3:1   mamba|mamba|mamba|mlp|attention|mlp
4:1   mamba|mamba|mamba|mamba|mlp|attention|mlp
```

**三个 tier（可随时停）：**

| Tier | 内容 | 运行数 | 回答什么 |
|---|---|---|---|
| **A** | QUIC-60 × 全部 5 臂 × 6 种子 | 30 | **只跑这一组就足以给出比例结论** |
| **B** | TLS-60 × 1:1/2:1/3:1 × 6 种子 | 18 | 比例效应是否随协议突发性变化 |
| **C** | QUIC-40 × 2:1/3:1 × 6 种子 | 12 | 类别数从 40 扩到 60 后结论是否稳定 |

**为什么只跑 60 类**：QUIC-40 不是独立任务，它是同一数据集、同一时间划分、同一套预处理下**按训练期频次排序的前 40 个类**，与 QUIC-60 **嵌套**。60 类还更难（不均衡度 Max/Min 从 3.64 升到 8.84），在更难的任务上成立是更强的结论。40 类只保留为 tier C 的"难度阶梯"。

**⚠️ 不要用 40→60 的衰减来宣称"类别扩展鲁棒性"**：实测衰减 HSTA 0.88pp，而 SRViT 0.47pp、30pktTCNET 0.18pp **都比 HSTA 更稳**。原稿 Abstract 的 "strong adaptation to class expansion" 与正文自述矛盾，正好是审稿人会抓的点，改写时要去掉。

**为什么 6 种子**：n=3 时精确 Wilcoxon 最小 p 值 = 0.25，**无论差距多大都做不出 p<0.05**；n=6 时下界降到 2/2⁶ = 0.031，配对检验才具备判断力。所有臂使用**同一组种子**（42, 2025, 3407, 1337, 7, 2024），保证比较是配对的。

```bash
bash scripts/run_evidence_pack.sh calc              # 先看，几秒，不训练
bash scripts/run_evidence_pack.sh parallel_ratio 3  # 约 6-12 小时（60 次运行）
bash scripts/run_evidence_pack.sh ratio_report      # 出表 + 判定
```

**一个不用跑实验就能成立的论证**：`calc` 会显示，在 dim=128 下 Mamba 块比 attention 块**更大**，而 1:1 臂少一个 Mamba 块。因此 **1:1 臂的参数比 2:1 臂更少**；如果 2:1 仍然胜出，不能把结果归因于更大的模型容量。固定宽度的 3:1 和 4:1 臂参数更多，不能用于等容量结论；需要参数匹配时使用 `ratio_budget_v13.yaml`。

### 参数匹配比例研究

`configs/ratio_budget_v13.yaml` 提供 3 个 QUIC-60 比例臂、每臂 6 个共享种子（共 18 次运行）。每个臂显式指定宽度并保持 attention backend、FFN 比例和状态空间设置不变：M2A1 使用 `dim=128`，M3A1 使用 `dim=116`，M2A2 使用 `dim=112`。三组实测参数量约为 604,988、601,172 和 623,116；其中最后一组是约 3% 的近似匹配，分析报告会保留实际参数列，不把它写成完全等参。

```bash
bash scripts/run_evidence_pack.sh parallel_ratio_budget 3
bash scripts/run_evidence_pack.sh ratio_report
```

### 被删除 / 不再需要跑的

| 项 | 原因 |
|---|---|
| `ratio_fixed_budget_v13.yaml` | 我上一轮过度设计。为每个比例臂重新调宽度会翻倍运行量，还会引入"每层容量随宽度变化"的第二个混淆变量，而上面的参数方向论证已经回答了容量质疑 |
| `configs/hsta_no_attention_v13.yaml`（legacy 无注意力臂） | `mamba\|mamba\|mlp\|mlp\|mlp` 是把 attention **换成第三个 FFN**，除了注意力还差了一整个 FFN，不是干净对照。用 `ratio_scale_v13.yaml` 里的 `1:0` / `2:0` 臂替代 |
| 1:2 / 2:2 / 5:2 及以上 | `calc` 会显示它们要么远超预算，要么已过有效区间。只有当 4:1 仍在上升时才需要补 2:2 来从另一侧定位峰值 |
| 重跑基线 | 7 个基线的记录已存在，直接复用 |

---

## 8. 文件清单

| 文件 | 作用 |
|---|---|
| `configs/hsta_no_attention_v13.yaml` | 重建的 No Attention 消融（已修 attention_backend） |
| `configs/alignment_baselines_v13.yaml` | **由 probe 自动生成**，参数对齐基线 |
| `scripts/alignment_models.py` | 实测各候选模型参数量，选出参数匹配的 depth，并列出各比例臂的参数量 |
| `scripts/ratio_calculator.py` | 参数量/比例计算器（不训练，秒级），输出设计建议 |
| `scripts/ratio_analysis.py` | 比例研究分析：从 layout 还原 M:A，出比例表与判定 |
| `scripts/aggregate_evidence.py` | 从原始记录重算全部表格 + 统计检验 |
| `scripts/run_evidence_pack.sh` | 统一入口（probe / stage_* / parallel_* / report） |
| `run_experiments.py` | 新增 `--output-dir`，供并行 worker 隔离聚合 CSV |
