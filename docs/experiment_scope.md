# 正式实验范围

当前只保留 CESNET-TLS22-S 和 CESNET-QUIC22-S 两份 60 类数据。每个已知类别的训练、验证、测试上限为 `10000/2000/2000`；真实 unknown 目标为已知流量的 30%，合成噪声目标为 10%，不足时按 actual 记录。

## 运行矩阵

| 组别 | 设置 | seed | 训练次数 |
| --- | --- | --- | ---: |
| 主比较 | HSTA-CM-open、HSTA-CM-closed、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN | 599、5009、813 | 42 |
| 消融 | `no_conv-open`、`no_mamba-open`、`no_attention-open` | 599、5009、813 | 18 |

42 和 18 是独立训练运行数，不是模型数量。主比较有 7 个模型设置，消融有 3 个设置，均在 TLS 和 QUIC 上各运行三个 seed。效率实验只测完整 HSTA-CM 的推理 batch `1/8/32`。

训练最多 100 轮、patience 15，以已知验证集 Macro-F1 调度和早停。优化器目标 batch 为 4096，验证/测试 batch 为 512；OOM 时使用微批次梯度累积，并在结果中记录实际微批次。

## 结果口径

每个模型同时保存 raw argmax 和 threshold rejection。已知 Accuracy/Macro-F1 只在已知流量子集计算；整体 Accuracy/Macro-F1 则覆盖混合测试集：

- 已知类别 Accuracy、Macro-F1；
- unknown Precision、Recall、F1、AUROC、AUPR；
- 已知流量误拒为 unknown 的比例；
- unknown 被判为已知的比例；
- 混合测试集 Accuracy、Macro-F1；
- 参数量、实际训练轮数、训练时间和推理效率。

真实留出应用和测试噪声分层报告。AUROC/AUPR 评价 unknown 分数的排序能力，不等同于某一个固定阈值下的 F1。closed 没有显式 unknown 输出，但仍可用 `1 - max(known probability)` 计算拒识分数；因此 closed 的 unknown 指标用于比较拒识能力，不代表它训练过 unknown 类。

正式结果必须使用完整数据审计和三个 seed 的单次值及 `mean ± std`。在队列完成前，结果只能视为运行中间产物。
