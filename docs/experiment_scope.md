# 当前实验范围

## 固定设置

- 数据集：CESNET-TLS22-S、CESNET-QUIC22-S；
- 类别：每个数据集 60 个已知类，开放模型加 1 个 `unknown`（61 类）；
- 输入：前 30 个包、3 个特征、形状 `[30, 3]`；
- 采样：`small=100/20/20`（训练/验证/测试每类上限）；
- 随机种子：`599`；
- 隐藏维度：所有 HSTA-CM 分支和 Mamba 配置为 256；
- 训练：最多 100 轮，patience 15，按验证集已知 Macro-F1 调度和早停。

## 主比较

每个数据集运行 HSTA-CM-open、HSTA-CM-closed 和五个闭集适配基线：30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN。open 训练 unknown 支持流量并输出 61 类；closed 和基线只训练 60 个已知类，测试时用已知验证流量校准拒识阈值。TrafficAudio 内部的 BiGRU 保留，但独立 GRU 和 Transformer 不属于矩阵。

## 组件消融

每个数据集再运行：

- `no_conv-open`：移除 Conv1d 分支；
- `no_mamba-open`：移除 Mamba 分支；
- `no_attention-open`：移除 FlashAttention。

消融保持 256 维、61 类输出、相同数据、unknown 来源和 seed 599，用于比较各组件对结果的影响；单 seed 结果不预设完整模型在每个数据集上都领先。

## 指标

raw argmax 和 threshold rejection 分开报告：已知 Accuracy/Macro-F1、unknown Precision/Recall/F1、AUROC、AUPR、已知误拒率、未知误判为已知比例、混合测试集 Accuracy/Macro-F1、参数量、训练轮数和运行时间。unknown 结果按 `unknown_test_heldout`、`noise_test` 分层统计。拒识阈值只由已知验证流量获得。

TLS small 验证集存在少数类别样本不足，Macro-F1 需结合每类流量数阅读。单一 seed 只报告单次值，不填虚假的标准差。

small 中 `noise_test` 每个数据集只有 20 条流，分层指标波动较大，当前只作为流程检查，不作为稳定泛化结论。

## 输出和目录

主结果写入 `results/compact_s`，消融写入 `results/hsta_cm_ablation_s`，效率写入 `results/efficiency_benchmark`。每个运行目录保存配置、训练曲线、最佳检查点、raw/threshold 指标、分类报告和逐样本来源信息；结果和检查点被 Git 忽略。`scripts/summarize_compact_results.py` 生成 `results/compact_s/compact_summary.csv`，用于快速比较六项核心指标。

旧类别规模、旧宽度、大规模采样、单独 GRU/Transformer 和历史结果不属于当前范围。
