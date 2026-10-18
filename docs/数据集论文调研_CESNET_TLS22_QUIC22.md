# CESNET-TLS22-S 与 CESNET-QUIC22-S 数据集论文使用情况调查

> **调查截止：2026 年 10 月 15 日**
> **调查对象：**仓库中的 `CESNET-TLS22-S`、`CESNET-QUIC22-S`，以及它们的上游 CESNET 数据集。
> **核心结论：**这两份数据在真实网络细粒度服务识别领域具有较高研究价值，已经出现在 KDD、Computer Networks、TMA、CNSM、IEEE TNSM 等同行评审论文中；但相较于 ISCX-VPN、USTC-TFC 等沿用多年的基准，直接实证论文仍是一个规模不大的新兴集合，不能说已经成为全领域的“主流标准数据集”。

---

## 1. 执行摘要

1. **高质量研究是有的。** TLS 数据被用于细粒度服务分类与未知服务拒识、可解释模型、类别增量学习、联邦学习、脉冲序列建模、跨数据集迁移和检索式 OOD 识别；QUIC 数据被用于真实 QUIC 服务分类、跨周漂移、特征融合、联邦分类和表示预训练。
2. **数量不算多，但近年在增加。** 按“论文确实把数据用于训练、评估或预训练”的严格口径，排除两篇数据集原始论文后，本次核实到 **TLS 方向 6 篇、QUIC 方向 5 篇正式发表的后续实证研究记录**；其中跨 TLS/QUIC 的迁移学习论文重复一次，合并后是 **至少 10 篇不同的正式发表方法/应用研究**。两篇数据集原始论文另列，另有 2 篇直接使用数据的预印本，不计入正式发表数。此数是可核验下限，不是对所有数据库的绝对总量断言。
3. **不同论文的“数据集同名”不等于相同实验。** 有的用 191 类 TLS22，有的只取 5、20、40、80 类；QUIC 论文也有 7、40、102 类等设置。研究中混有按周时间切分、随机切分、类别平衡、过采样和开放集拒识，准确率不能直接排成一个排行榜。
4. **本项目 CSV 不是论文中的原始全量数据。** 项目从 CESNET DataZoo 的 S 源数据导出，再选取 60 个已知应用，构造真实 unknown 和合成噪声，并按固定日期切分。现有论文结果适合作为相关工作与方法设计依据，**不等于在本项目这份 60 类开放集 CSV 上的直接 SOTA 对照**。
5. **数据集选择有说服力，但研究贡献不能只写“用了新数据”。** 更值得强调的是本项目的时间泛化、60-known/unknown 开放集协议、真实未知来源隔离、噪声族隔离，以及 TLS 与 QUIC 两类协议上的同协议比较。

---

## 2. 调查口径与文献数量说明

### 2.1 何谓“使用了数据集”

本调查将“直接使用”限定为论文在实验中从 CESNET-TLS22 或 CESNET-QUIC22 取数据，进行训练、测试、预训练、漂移检测或融合分析。**只在相关工作中引用数据集论文、只列出数据集名称、只介绍 DataZoo 工具，不计入方法实证论文数。**

以下项目单独处理：

- **CESNET-TLS22 与 CESNET-TLS-Year22 是不同数据集。** TLS22 是 2021 年 10 月的两周 TLS 数据；TLS-Year22 是后续发布的一年跨度数据。论文若只使用 TLS-Year22，不计为 TLS22 直接使用。
- **上游 CESNET 数据集与仓库中的 60 类 CSV 不是同一实验协议。** 文献中的 191/102 类、采样比例与日期切分，通常不同于本项目导出的 60 个已知类别及 open-set unknown。
- **预印本、学位论文、海报/工具论文与期刊或正式会议论文分开。** 预印本可作为新方向线索，但不和同行评审论文等量统计。
- **相近的联邦增量学习会议与期刊版本不重复扩大数量。** 例如 BCCA 会议记录与后续期刊研究主题及实验设置接近，主计数以可核实的正式期刊版本为准。

### 2.2 数量结论如何解读

截至 **2026 年 10 月 15 日**，按上述规则核验到 TLS 后续研究 6 篇、QUIC 后续研究 5 篇正式发表实证记录，去除 1 篇跨数据集重复后为至少 **10 篇不同的方法/应用论文**；另有 **When Simple Model Just Works** 和 **FlowCLIP** 两篇可核对的直接使用预印本。两篇数据集原始论文和 DataZoo 工具论文另列，不放入这 10 篇后续研究的主计数。

这应理解为**检索到的、可确认的下限**，而不是“全世界总共只有这些论文”。数据集名称可能在全文、附录或代码仓库中出现而未被索引；反过来，检索命中也可能只是引用或提及。对用户实际写论文而言，以上严格口径比不说明检索范围的“Google Scholar 命中数”更可复核。

---

## 3. 先区分上游数据与本项目的数据

### 3.1 两个上游数据集概况

| 上游数据集 | 数据集论文与出版信息 | 原始研究范围（概括） | 适合回答的问题 |
|---|---|---|---|
| **CESNET-TLS22** | [Fine-grained TLS services classification with reject option](https://doi.org/10.1016/j.comnet.2022.109467)，*Computer Networks* 220，2023 | 真实骨干网 TLS 流量，约 **1.4 亿条流、191 个服务标签**；数据时间约为 2021-10-04 至 2021-10-17。数据集原文同时研究细粒度 TLS 服务分类与未知服务拒识。 | 真实 TLS 环境下的应用/服务识别、未知类拒识、时间变化。 |
| **CESNET-QUIC22** | [CESNET-QUIC22: A large one-month QUIC network traffic dataset from backbone lines](https://doi.org/10.1016/j.dib.2023.108888)，*Data in Brief* 46，2023 | 真实骨干网 QUIC 流量，约 **1.53 亿条流**，覆盖约四周；官方标签中包括约 **102 个应用/服务类及背景流量类**。 | 真实 QUIC 服务分类、协议/服务分布、时间漂移、跨时间评估。 |

数据集发布方 [CESNET DataZoo 文档](https://cesnet.github.io/cesnet-datazoo/datasets_overview/) 提供多个源数据规模和统一读取接口。`S` 是仓库所用的 DataZoo 源版本标记；它**不是**“60 类实验”的含义，也不能把源数据文件名当成最终模型实验的数据协议。

> 上述全量记录数、类别数是上游数据集论文的描述。不同版本、DataZoo 采样规模、筛选类别和实验日期会改变实际样本数，引用时应说明采用的是哪一种。

### 3.2 仓库中的实际实验数据

依照仓库的 [60 类开放集实验协议](experiment_protocol.md)、[正式实验范围](experiment_scope.md) 和 `data/processed/` 中的 manifest/audit 文件，本项目数据为：

| 项目 | TLS22-S 导出 | QUIC22-S 导出 |
|---|---:|---:|
| 已知应用数 | 60 | 60 |
| open 模型输出类别 | 60 known + 1 unknown = 61 | 60 known + 1 unknown = 61 |
| 数据筛选 | 各自按训练窗口内应用频率选 Top-60；两数据集类别映射独立 | 同左；与 TLS 的 60 个已知标签不保证相同 |
| 时间切分 | 训练 2021-10-04—10-10；验证 10-11；测试 10-12—10-17 | 训练 2022-10-31—11-13；验证 11-14—11-15；测试 11-16—11-27 |
| 每个已知类上限 | train/val/test = 10,000/2,000/2,000 | train/val/test = 10,000/2,000/2,000（受数据可用量限制） |
| unknown 设计 | 真实 unknown 目标为已知量的 30%，合成噪声目标为 10%；按 split 隔离来源/噪声族 | 同左；实际导出不足时按可用量审计，不重复补采 |
| 已审计 CSV 流数 | 1,176,000 | 1,079,399 |
| 模型输入 | 每流前 30 个包的包长、方向、包间隔，形状 `[B,30,3]` | 同左 |

所以，本项目实验测到的是**基于 DataZoo S 源数据构造的 60 类时间切分开放集派生基准**，不是原始 191 类 TLS22 或 102 类 QUIC22 的复刻。表内论文的成绩应作为背景或方法参考，不能直接说“本模型超过/落后于论文 X”，除非重新对齐类别、输入特征、样本抽样、时间范围和 unknown 协议。

---

## 4. 值得重点阅读的直接使用论文

### 4.1 CESNET-TLS22：细粒度 TLS 服务分类

| 论文 | 具体使用方式与主要贡献 | 对本项目的参考价值／不可直接比较处 |
|---|---|---|
| **[Fine-grained TLS services classification with reject option](https://doi.org/10.1016/j.comnet.2022.109467)**，Computer Networks，2023 | TLS22 奠基论文；在真实 TLS 服务上研究已知类分类和未知服务拒识。原论文报告分类准确率约 **97.04%**，在 5% false-positive rate 下检测未知服务约 **91.94%**。 | 最适合作为数据集背景和 TLS 拒识相关工作的起点。论文任务虽与 open-set 方向接近，但其类别和划分并非本项目 60 类协议。 |
| **[A Lightweight, Efficient and Explainable-by-Design Convolutional Neural Network for Internet Traffic Classification](https://doi.org/10.1145/3580305.3599762)**，ACM SIGKDD，2023 | KDD 会议论文 LEXNet，研究轻量且可解释的卷积流量分类。使用 CESNET TLS 服务流量的早期/特定规模版本，研究范围包括 191 个服务类别。 | KDD 是本调查中很有代表性的高水平方法工作。可作为轻量时序/卷积分类参考；后续论文引用的约 97.2% TLS 准确率与当前项目分割不等价。 |
| **[MEMENTO: A novel approach for class incremental learning of encrypted traffic](https://doi.org/10.1016/j.comnet.2024.110374)**，Computer Networks 245，2024 | 使用 TLS22-40 和 TLS22-80（Top-40/Top-80 类）以及 MIRAGE19，研究应用类别逐步增加时如何学习新类并减轻旧类遗忘。TLS22 每类随机抽取 0.15% 流量，包含 20+20、39+1、40+40、79+1 等增量设置。 | 适合 related work 中说明 TLS22 已被用于类别增量；它不是固定 60 类一次性训练的对照。论文报告的提升是增量设置下相对 BiC 的比较，不能转写成绝对准确率提升。 |
| **[Explainable federated class incremental learning for Encrypted Network Traffic classification](https://doi.org/10.1016/j.comnet.2025.111448)**，Computer Networks 269，2025 | 以约 40 个服务类进行联邦类别增量实验，比较 2 客户端/10 客户端以及 38+2、30+10 等新类到达方式，同时考察解释能力。 | 说明 TLS22 可用于研究模型在多管理域、持续新增类别下的部署问题。约 82%/79% 的报告 F1 对应不同联邦客户端和增量协议，不是同一闭集测试集 SOTA。 |
| **[Classifying Encrypted Traffic Using Quad-Directional Convolution on Pulse Sequences](https://doi.org/10.1186/s42400-025-00386-1)**，*Cybersecurity*，2025 | PDQ-Net 把包长序列转换成 pulse 序列，沿四个方向做卷积；在 CESNET-TLS22 上报告 5 应用与 20 应用任务，使用前最多 30 个包。论文报告 F1 分别约 99.24% 和 98.74%。 | 输入形式与本项目的包序列相关，适合分析包序列建模思路。但该文使用随机 8:2 切分并过采样到每类 5,000；高分不应直接与按周时间切分的项目结果比较。 |
| **[Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining: A Transfer Learning Success](https://doi.org/10.1109/TNSM.2025.3642984)**，IEEE TNSM，2026 | 使用 QUIC22 做 SNI 域名识别预训练，再迁移到包括 TLS22 在内的多个数据集/下游任务；最终研究报告覆盖 7 个数据集、10 个下游任务，微调方法在 9/10 个任务中超过其比较对象，平均提高约 6.4%。 | 这是连接 TLS22 与 QUIC22 的重要跨数据集工作。准确说法是“QUIC22 预训练、TLS22 等下游评测”，不要说成所有 10 个任务都在 QUIC22 上。 |
| **[Ultra fast encrypted network traffic classification based on classification by retrieval powered by out-of-distribution](https://doi.org/10.1016/j.comnet.2026.112739)**，Computer Networks 289，2026-10-01 | 截至本报告日期最新的一批 TLS22 研究之一。用约 1,520 万条单日 TLS22 流量，保留 184 个应用和 21 个服务类，比较统计特征、CNN/MLP 表示与随机森林，并提出近邻检索分类和 OOD 检测。CNN embedding 检索的 macro-F1 约 0.923，RF 约 0.925；训练快约 10 倍，OOD AUROC 最高约 0.92。 | 很值得读的近期工作，涉及快速增加新类别和 unknown/OOD。数据类别、单日切分和任务仍与项目的 60 类多周 open-set 协议不同。 |

### 4.2 CESNET-QUIC22：QUIC 服务识别、漂移与融合

| 论文 | 具体使用方式与主要贡献 | 对本项目的参考价值／不可直接比较处 |
|---|---|---|
| **[Encrypted traffic classification: the QUIC case](https://doi.org/10.23919/TMA58422.2023.10199052)**，TMA 2023 | QUIC22 早期代表性方法论文，使用约 102 个 QUIC 服务类；比较多模态 CNN、LightGBM 和 IP 分类器，并按周训练/测试。多模态 CNN 平均召回率约 84.02%；移除握手包时报告最高准确率约 87.96%。研究还观察到证书变化相关的周间漂移：部分 Google 服务第二周召回率下降约 30%。 | 说明 QUIC 分类需要时间切分和漂移分析；IP/ASN 方法的提供商级准确率不可与细粒度服务识别指标混为一谈。 |
| **[MFWDD: Model-based Feature Weight Drift Detection Showcased on TLS and QUIC Traffic](https://doi.org/10.23919/CNSM62983.2024.10814630)**，CNSM 2024 | 用 QUIC22 和 **CESNET-TLS-Year22** 研究特征重要性随时间的变化，并探索据此触发重训练。输入比较 DataZoo PPI 元数据与最多 30 个包的 NetTiSA 特征。 | 这是 QUIC22 的漂移研究，但 TLS 部分是 TLS-Year22，不能列为 TLS22 直接使用。论文细粒度数值更多来自 TLS-Year22，引用时要分清两套数据。 |
| **[On Evaluation of Data Fusion Methods for Network Traffic Classification](https://doi.org/10.23919/CNSM67658.2025.11297464)**，CNSM 2025 | 从 QUIC22 取最常见 40 个服务并平衡各类，融合流统计、前 30 包序列、包长直方图、IP/ASN 等基础分类器的输出。报告决策树融合 F1 88.76%、Recall 融合 86.65%、加权投票 85.73%、多数投票 79.86%。 | 数据本身对 Google 服务偏斜，论文因此做 Top-40 平衡；这些数字只代表该融合任务和子集，不是完整自然分布 102 类 QUIC22 的 SOTA。它是与项目三特征包序列输入较相关的比较材料。 |
| **[Taming Volatility: Stable and Private QUIC Classification with Federated Learning](https://doi.org/10.23919/CNSM67658.2025.11297478)**，CNSM 2025 | 使用 QUIC22 第 46–47 周，选择 7 个常见服务，模拟 14 个自治客户端，研究客户端缓存/缓冲对联邦训练和时间波动的影响。报告缓冲后的联邦模型 F1 约 95.2%，较集中式非隐私模型低 2.3 个百分点。 | 适合用来讨论分布式/隐私约束和漂移；仅 7 类、2 周、14 客户端，不能当成完整 QUIC22 或本项目 60 类准确率对照。 |
| **[Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining](https://doi.org/10.1109/TNSM.2025.3642984)**，IEEE TNSM，2026 | QUIC22 主要用作域名/SNI 识别的预训练源，学习的监督目标比 102 个粗粒度服务标签更细，再迁移至 TLS22、AppClassNet、MIRAGE 等下游数据集。 | 代表从“每个数据集从头训练”走向跨数据集表示迁移；需区分预训练数据与下游测试数据。 |

### 4.3 两篇新近预印本：有参考价值，但不计入同行评审数量

| 论文 | 状态与使用方式 | 阅读价值与限制 |
|---|---|---|
| **[When Simple Model Just Works: Is Network Traffic Classification in Crisis?](https://arxiv.org/abs/2506.08655)** | 截至调查日按 arXiv/CoRR 预印本处理。覆盖 12 个数据集、15 个任务，包括 191 类 TLS22 和 102 类 QUIC22；重点比较输入空间 1-NN 与已有模型，并讨论重复/相似流量和切分。 | 对本项目的**评估可信度**很重要。论文报告时间切分下优化 1-NN 在 TLS22/QUIC22 约 92.34%/72.91%，而对应比较的高分结果约 97.2%/80.87%；QUIC22 随机切分和时间切分的结果也明显不同。因为仍是预印本且各项任务协议不同，应当引用其分析思路，不把这些数值当最终定论或直接排名。 |
| **[FlowCLIP: Contrastive Pretraining Using Domain Names for Encrypted Traffic Classification](https://doi.org/10.48550/arXiv.2606.17746)** | 2026 arXiv 预印本。用 QUIC22 的包长、方向、包间隔等侧信道特征，并以域名文本作监督，进行 CLIP 式流量—文本对比预训练；另用 UC Davis QUIC 数据检查迁移。 | 反映最新的域名语义监督/表示学习方向；截至调查日未检索到正式期刊或会议最终版，应在论文中明确标为预印本。 |

---

## 5. 使用量多不多？为什么？

### 5.1 判断：对细分方向来说已有积累，对整个领域来说仍不多

按上文的严格口径，**至少 10 篇正式发表的后续方法/应用研究（TLS 6、QUIC 5，跨数据集论文去重后 10）加 2 篇直接使用预印本**，已经足以说明数据集不是“没人用”或质量不被认可；但和运行十年、被反复写入代码模板和比较表的传统数据集相比，采用量仍有限。若把两篇数据集原始论文也计入“直接使用”，正式论文记录再增加 2 篇，但这不改变“后续方法研究仍不算多”的判断。较准确的写法是：

> **CESNET-TLS22 与 CESNET-QUIC22 已成为真实网络细粒度服务识别、时间漂移和迁移研究中有价值的新兴基准，但截至 2026 年仍未成为加密流量分类所有子领域的通用标准数据集。**

TLS 的后续研究从分类/拒识扩展到增量学习、联邦学习、脉冲序列和检索 OOD；QUIC 研究则从早期多周分类扩展到漂移、融合、联邦和域名预训练。可见使用主题在增长，但数据复用密度还没有传统 VPN、恶意流量或移动应用基准那么高。

### 5.2 使用量较小的合理解释

以下是由数据集特征和已发表研究设置支持的**可能原因**，不是某项计量研究已经证明的单一因果结论：

1. **发布时间较晚，基准惯性尚未形成。** TLS22/QUIC22 的公开论文发表于 2023 年左右；ISCX-VPN、USTC-TFC、CIC 系列等已积累多年公开代码、历史结果和教学材料，研究者沿用旧基准的复现成本低。
2. **数据体量和预处理成本高。** 上游数据达到约 1.4–1.5 亿流规模，即使采用 DataZoo 的 S 版仍需要数据加载、筛类、流级序列处理和硬件资源。论文常见做法是先选 Top-40/Top-80、每类下采样、平衡类别或按周缩小实验。
3. **研究问题较专，不能替代所有流量数据集。** TLS22/QUIC22 最适合细粒度应用/服务识别和漂移研究；VPN/Tor 识别、攻击检测、恶意软件家族分类、移动应用行为或网站指纹研究的标签、威胁模型和输入不一样，往往仍会选更贴题的旧数据集。
4. **真实流量带来漂移与外推问题。** 单个网络和几周窗口提高现实性，却不自动代表其他运营商、国家或未来年份。TMA 的 QUIC 实验及后续多周研究显示时间切分会显著影响指标，模型必须面对分布变化；这比随机切分更有意义，但实验和报告成本也更高。
5. **实验协议分散，降低可比性。** 同一原始数据可以形成 5、20、40、80、102、184、191 类任务；也可能采用随机拆分、按周拆分、平衡数据、过采样或增量阶段。数据集引用数量增加，并不等同于高可比基准结果同步增加。
6. **领域任务本身不统一。** 文献中“encrypted traffic classification”涵盖应用识别、VPN/Tor 检测、移动应用分类、恶意流量检测、DoH 等。一个通用数据集难以覆盖所有标签语义，研究者按任务分散选择数据。
7. **样本重复、标签相关性和字段泄漏需要专门审计。** 近年的评估论文开始讨论流量重复、随机拆分过于乐观，以及 SNI/域名字段可能直接暴露标签等问题。对 CESNET 这种大规模、时间相关的真实数据，正确切分和字段审计本身就是研究工作。

### 5.3 这并不表示数据“水平不够”

数据集是否“有水平”，应看它是否适合研究问题，而不是只看论文引用次数。TLS22/QUIC22 的突出价值是：真实网络来源、较多细粒度应用/服务标签、TLS 与 QUIC 两种协议、可按时间评估，也可用来研究 unknown、迁移和漂移。较少的复用更多说明数据较新、任务专业和评估成本高；不能据此推断数据质量低。

---

## 6. 一般常用的数据集有哪些？各自适合什么问题？

“常用数据集”要按任务分，尤其不能把应用识别和攻击检测放进同一个准确率排行榜。加密网络流量综述可参考 [IEEE Communications Surveys & Tutorials 综述](https://doi.org/10.1109/COMST.2022.3208196) 和 [Computer Networks 2026 综述](https://doi.org/10.1016/j.comnet.2026.112524)。

| 数据集 | 常见研究方向 | 与本项目任务的关系/注意点 |
|---|---|---|
| **ISCX-VPN-nonVPN 2016** | VPN 与非 VPN 分类，也常用于较粗粒度应用类型分类 | 是传统加密/VPN 研究常见数据集，但规模和服务标签粒度不等于 TLS22/QUIC22。原始数据/任务可见 [UNB/CIC 数据集说明](https://www.unb.ca/cic/datasets/vpn.html)。 |
| **ISCX-Tor-nonTor、CIC-Darknet2020** | Tor、VPN、暗网流量和匿名网络检测 | 更偏隧道/匿名通信识别，不是“识别 60 个互联网应用服务”的直接替代。 |
| **USTC-TFC2016** | 恶意软件流量、正常/恶意类别和安全分类 | 安全方向常用，但其标签目标主要是恶意/良性及恶意家族，和服务级应用分类不同。 |
| **MIRAGE19 / MIRAGE22** | Android/移动应用流量识别、移动端流量分析 | 对移动 App 研究更贴题；设备、用户、采集方式与骨干网 CESNET 数据不同。[MIRAGE 项目](https://traffic.comics.unina.it/mirage/) |
| **UTMOBILENET21** | 移动网络应用识别与跨场景评测 | 适合作为移动端补充基准，但不能代替 TLS/QUIC 真实骨干网场景。 |
| **AppClassNet** | 大规模商业级应用分类 | 有大量应用类别与商业级网络来源，适合与 CESNET 做应用识别层面的补充对照。[数据集论文](https://doi.org/10.1145/3561954.3561958) |
| **UCDAVIS QUIC** | 早期 QUIC 应用识别/方法验证 | 常被作为早期 QUIC 参照；公开研究描述其约 6,500 条流、5 个 Google 服务，规模远小于 QUIC22。 |
| **CIC-DoHBrw / DoH 数据集** | DNS-over-HTTPS 流量分类、检测 | 适用于加密 DNS 子任务，不是一般 TLS 服务识别。 |
| **CIC-IDS2017、UNSW-NB15、CTU-13** | 入侵检测、攻击流量/僵尸网络识别 | 网络安全领域常见，但任务是攻击/异常识别，不应直接用它们与本项目的应用服务分类结果作准确率横比。 |
| **CESNET-TLS-Year22** | 一年尺度 TLS 服务分类、长期漂移 | 与 TLS22 不同数据集。若参考其论文，要在文中明确写 Year22；不可把它算成 TLS22 的直接使用记录。 |

### 对本项目最合适的“常用数据集”定位

- **最直接：**CESNET-TLS22-S 与 CESNET-QUIC22-S，因为任务是加密应用/服务识别，且能按时间评估。
- **可作为跨来源补充：**AppClassNet、MIRAGE/UTMOBILENET（需说明场景、输入与标签不同）。
- **仅用于背景，不建议当直接性能对照：**CIC-IDS2017、UNSW-NB15、USTC-TFC2016 等攻击检测数据；ISCX-VPN 与 Tor 数据则对应隧道/匿名通信问题。

---

## 7. 对 MVIF-Net 项目论文定位的建议

1. **写清楚派生数据协议。** 全文建议统一称为 `CESNET-TLS22-S/QUIC22-S 60-known-class open-set temporal benchmark` 或中文“基于 CESNET DataZoo S 源数据构造的 60 类开放集时间切分基准”，不要简称成与上游全量数据完全等同的 TLS22/QUIC22 原始实验。
2. **把两份 60 类标签映射分开报告。** Top-60 是按各自训练窗口频次独立选择；TLS 的 60 个标签不等于 QUIC 的 60 个标签。
3. **把时间切分当作实验贡献之一。** QUIC 的既有研究显示周间漂移显著；按时间切分比随机拆流更接近部署，但需在方法中写出精确训练、验证、测试日期。
4. **与既有文献作“设置对照”，不做裸数字排名。** 建议比较任务（closed/open/CIL/OOD）、类别数、输入字段、数据量、时间切分、类平衡策略、特征采样窗口、seed 和未知类定义。
5. **突出可靠的开放集审计。** 报告真实 unknown 身份跨 split 隔离、噪声生成族隔离、Scaler 只在已知训练流量拟合、日期/flow ID 审计，以及已知类误拒和未知类误收。这与只给 overall accuracy 的闭集论文有实质差异。
6. **不要未经验证地声称“首个”。** 可以说“现有代表性研究多数不是与本项目相同的 60 类、时间切分、真实 unknown/合成噪声共同协议”；如果要声称首个，须另做更系统的数据库检索并定义严格排除标准。

### 可改写进论文相关工作/数据集选择部分的中文表述

> CESNET-TLS22 与 CESNET-QUIC22 基于真实骨干网流量，已被用于细粒度服务分类、未知服务拒识、类别增量与联邦学习、时间漂移、特征融合及跨数据集表示迁移。现有研究证明了其在真实 TLS/QUIC 服务识别中的价值，但实验常采用不同类别子集、采样和平衡策略及时间划分，尚未形成可直接比较的统一基准。本文从 CESNET DataZoo S 源数据构造 60 个已知类别的开放集协议，按照互不重叠的时间窗口训练、验证和测试，并独立隔离真实 unknown 来源与合成噪声族，因此本文结果应与相同数据协议下的模型比较，而不直接按准确率与不同论文的 40/102/191 类结果排名。

---

## 8. 主要参考文献与数据来源

### 数据集、工具与综述

- [CESNET-TLS22 数据集/拒识论文，Computer Networks 220 (2023)](https://doi.org/10.1016/j.comnet.2022.109467)
- [CESNET-QUIC22 数据集论文，Data in Brief 46 (2023)](https://doi.org/10.1016/j.dib.2023.108888)
- [CESNET-TLS-Year22，Scientific Data 11 (2024)](https://doi.org/10.1038/s41597-024-03927-4)（与 TLS22 不同）
- [CESNET DataZoo 数据集概览与元数据](https://cesnet.github.io/cesnet-datazoo/datasets_overview/)
- [DataZoo: Streamlining Traffic Classification Experiments，2023](https://doi.org/10.1145/3630050.3630176)（工具/复现论文，不计入方法实证总数）
- [Machine Learning-Powered Encrypted Network Traffic Analysis: A Comprehensive Survey，IEEE COMST 2023](https://doi.org/10.1109/COMST.2022.3208196)
- [A Comprehensive Survey on Encrypted Network Traffic Classification，Computer Networks 2026](https://doi.org/10.1016/j.comnet.2026.112524)

### 直接实证研究

- [LEXNet，ACM SIGKDD 2023](https://doi.org/10.1145/3580305.3599762)
- [MEMENTO，Computer Networks 2024](https://doi.org/10.1016/j.comnet.2024.110374)
- [Explainable Federated Class Incremental Learning，Computer Networks 2025](https://doi.org/10.1016/j.comnet.2025.111448)
- [PDQ-Net，Cybersecurity 2025](https://doi.org/10.1186/s42400-025-00386-1)
- [Ultra-fast classification by retrieval with OOD，Computer Networks 2026](https://doi.org/10.1016/j.comnet.2026.112739)
- [Universal Embedding Function，IEEE TNSM 2026](https://doi.org/10.1109/TNSM.2025.3642984)
- [Encrypted Traffic Classification: the QUIC Case，TMA 2023](https://doi.org/10.23919/TMA58422.2023.10199052)
- [MFWDD，CNSM 2024](https://doi.org/10.23919/CNSM62983.2024.10814630)
- [On Evaluation of Data Fusion Methods，CNSM 2025](https://doi.org/10.23919/CNSM67658.2025.11297464)
- [Taming Volatility，CNSM 2025](https://doi.org/10.23919/CNSM67658.2025.11297478)
- [When Simple Model Just Works，arXiv 2025 预印本](https://arxiv.org/abs/2506.08655)
- [FlowCLIP，arXiv 2026 预印本](https://doi.org/10.48550/arXiv.2606.17746)

---

*本文件依据公开数据集文档、论文/会议记录、DOI 元数据和论文全文可核实信息整理；出版状态与文献数量以 2026-10-15 为界。对全文无法确认数据版本或实验设置的检索命中，没有纳入严格计数。*
