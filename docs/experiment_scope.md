# 正式实验范围

正式数据为 CESNET-TLS22-S 和 CESNET-QUIC22-S 两份 60 类数据。每个已知类别的训练/验证/测试上限是 `10000/2000/2000`；真实 unknown 的目标为已知量的 30%，生成噪声目标为 10%，不足时报告实际量。

## 深度与参数量

深度按串行主干块计算，不将基础算子数当作网络深度。残差块内部的卷积/线性算子、输入输出头不额外计层；并行分支分别报告，各路径最多 4 个主干块。结构与容量方案如下：

| 模型 | 建议配置 | 主干深度 | 预计参数量 |
| --- | --- | ---: | ---: |
| HSTA-CM open/closed | `dim=256`；Mamba、GNN、DFT 各 2 块，1 个 FlashAttention 融合块 | 每个分支 2，融合 1 | 2.294M |
| 30pktTCNET-adapted | `channels=300`，classifier 300 | 4 | 2.278M |
| NetMamba-adapted | `dim=292` | 4 | 2.294M |
| SRViT-adapted | `dim=192`, `mlp_ratio=3` | 4 | 2.204M |
| TrafficAudio-adapted | `dim=416`；3 CNN + 2 BiGRU 并行 | CNN 3，BiGRU 2 | 2.211M |
| BPF-GNN-adapted | `dim=664`，`graph_depths=(1,2,1)` | 总计 4 | 2.259M |

表中参数量是当前配置实例化后的核算值，训练运行仍会保存实际统计值。HSTA 与五个基线参数规模相近，但计算开销仍需通过效率实验单独比较。所有对照组使用共同 `[30,3]` 输入，结果标记 `adapted`，不代表原论文完整复现。

## 运行矩阵

| 实验组 | 设置 | 数据集与随机种子 | 训练数 |
| --- | --- | --- | ---: |
| 主比较 | HSTA-CM-open、HSTA-CM-closed、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN | TLS、QUIC；599、5009、813 | 42 |
| 消融 | `no_mamba-open`、`no_gnn-open`、`no_dft-open` | TLS、QUIC；599、5009、813 | 18 |
| 效率 | 完整 HSTA-CM，推理 batch `1/8/32` | TLS、QUIC | 每个数据集 3 个 batch 设置 |

主比较共 7 个设置 × 2 数据集 × 3 seeds。消融共 3 个设置 × 2 数据集 × 3 seeds。效率是测量配置，不计入训练次数。

## 精度模式和停止规则

HSTA-CM 的 Mamba selective block 固定 FP32，其他算子可使用 AMP。NetMamba 全模型关闭 AMP；其余基线使用 AMP。NetMamba 精度模式的变化须在结果中明确标出，不能将旧 AMP 运行与新 FP32 运行混合计算均值。

最多训练 100 轮，patience 15，学习率调度和早停基于已知验证集 Macro-F1。有效 batch 目标为 4096，评估 batch 为 512；显存不足时以累积微批次实现并记录实际值。所有新运行从头开始，不复用旧队列 checkpoint。

## 当前状态

旧的五基线队列已停止，旧结果已移至仓库外归档目录。新配置下的正式主比较、三分支消融和 batch `1/8/32` 效率实验将从第 1 轮重新开始。归档快照不并入新统计；至少等所有指定运行完成并通过数据/模型审计，才能形成最终三 seed 汇总。

所有模型都同时报告 raw argmax 和 threshold rejection。开放集指标、数据协议及审计项详见 [experiment_protocol.md](experiment_protocol.md)。
