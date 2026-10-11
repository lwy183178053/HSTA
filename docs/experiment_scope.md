# 当前正式实验范围

只保留 TLS22-S、QUIC22-S 各 60 已知类加 unknown 的一份最终数据。每已知类训练/验证/测试上限 10000/2000/2000；真实 unknown 目标为实际已知数量的 30%，噪声为 10%，不足以 actual 为准。

## 运行矩阵

| 组别 | 设置 | seed | 训练次数 |
| --- | --- | --- | ---: |
| 主比较 | HSTA-CM-open、HSTA-CM-closed、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN | 599、5009、813 | 42 |
| 消融 | no_conv-open、no_mamba-open、no_attention-open | 599、5009、813 | 18 |

42 和 18 是训练运行数，不是独立架构数量。正式训练目标有效优化器批次为 4096，验证/测试批次为 512；OOM 时用梯度累积，每个优化器更新仍覆盖 4096 个样本。若发生回退，含 BatchNorm 的模型会使用微批次统计量，实际微批次需结合结果解读。效率仅测完整主模型两个数据集的推理 batch 1、8、32；这里的 batch 是一次推理输入流量的数量。

两数据集使用相同三路、三种编码、76 token、256 维架构。open/消融训练 unknown 支持和训练噪声；closed/五个基线不训练 unknown。TrafficAudio 内部 BiGRU 保留，不单独跑 GRU 或 Transformer。正式阶段不再搜索结构。

## 结果阅读

raw 与 threshold 分开报告。closed raw 只能输出已知类，unknown F1 通常为 0；AUROC/AUPR 仍可评价其不确定性分数排序。closed threshold 可以拒识 unknown，比较它与 open 的效果用于判断显式 unknown 监督的收益。改善必须同时检查已知分类指标与误拒率，不能预设没有代价。

三 seed 报单次值、mean±std、参数量、轮数、时间；推理效率记录延迟和吞吐。严格时间窗口可能导致部分类别不足，Macro-F1 结合各类支持数解释。真实 unknown 与测试噪声分层结果及 actual 数量必须保留，不预设主模型胜出。

## 保存与后台运行

当前模型、五个基线、三项消融及必要导出/审计/训练/效率/汇总入口保留。旧数据规模、旧类别数、旧宽度、结构搜索结果移到仓库外归档，原始 H5 与映射保留。后台按序运行并写日志、状态、完成/失败标记；确认启动成功后停止主动检查，用户询问时再读取。
