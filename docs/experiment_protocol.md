# 60 类 Small 开放集实验协议

本文档是当前 TLS22-S 和 QUIC22-S 实验的唯一口径。实验只使用 `small` 采样档和随机种子 `599`；不纳入旧的类别规模、宽度或大规模采样结果。

## 1. 数据和划分

每个数据集固定 60 个已知应用类别，类别映射独立保存。每条流按时间划分为训练、验证和测试，流 ID 不得跨集合重复；输入为前 30 个包的 `[30, 3]`（包长、方向、包间隔）。small 的每类上限为：训练 100、验证 20、测试 20；类别样本不足时保留全部并在报告中记录实际数量。TLS 验证集部分类别样本很少，Macro-F1 必须结合类别支持数解释。

项目使用已生成并审计的缓存：

```text
data/processed/datazoo_tls60_s_protocol_small_sampled.csv
data/processed/datazoo_quic60_s_protocol_small_sampled.csv
```

原始 CESNET H5 保留在本地，不重新下载，也不提交 Git。scaler 只在训练流上拟合，验证和测试只调用 `transform`；类别映射、scaler、时间窗口和采样 manifest 随实验配置保存。

## 2. Unknown 构造和隔离

已知 60 类之外的真实应用在折叠标签前按应用身份划分：

- `unknown_support`：训练阶段可见，仅供 HSTA-CM-open 及其消融训练；
- `unknown_test_heldout`：训练和验证都未出现，专用于开放集测试；
- `noise_train`、`noise_val`、`noise_test`：三套生成族互斥，测试族在训练阶段从未出现。

CSV 保留 `original_app`、`source_group` 和 `noise_family`，这些字段只用于审计和分层统计，不能作为输入。训练、验证、测试的 flow ID、留出应用和噪声族必须互斥。测试集必须同时含已知流量、真实留出应用和测试专属噪声。

`small` 测试集每个噪声来源组最多抽取 20 条流。因此 `noise_test` 的指标只作小样本描述；即使本轮得到满分，也不能据此声称对未见噪声具有稳定泛化能力。

## 3. 模型矩阵

每个数据集运行以下 10 个配置：

| 组别 | 配置 | 输出 | unknown 训练 |
| --- | --- | ---: | --- |
| 主模型 | HSTA-CM-open | 61 | 是 |
| 主模型 | HSTA-CM-closed | 60 | 否 |
| 基线 | 30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN | 60 | 否 |
| 消融 | no_conv-open、no_mamba-open、no_attention-open | 61 | 是 |

HSTA-CM 统一 256 维、三层残差 Conv1d、两层残差 Mamba、融合全连接、位置编码、FlashAttention、LayerNorm 和分类头。基线统一输入和数据划分；TrafficAudio 的 BiGRU 属于该模型。GRU 或 Transformer 不单列。

## 4. 训练和阈值

所有运行从第 1 轮开始，不复用旧 checkpoint。最多训练 100 轮，使用验证集**已知类别** Macro-F1 调度学习率和早停，patience 为 15。测试集不能参与 epoch、模型、类别或阈值选择。

每个运行保存两套预测：

1. **raw argmax**：开放模型直接在 61 类取最大概率；闭集模型在 60 类取最大概率。
2. **threshold rejection**：阈值只用已知验证流量校准。开放模型使用显式 `unknown` 概率，闭集模型使用 `1 - max(softmax)`；将分数达到阈值的样本置为 `unknown`。验证 unknown、测试 unknown 不参与阈值拟合。

## 5. 指标

raw 和 threshold 版本都要落盘，并分别报告：

- 已知子集 Accuracy、Macro-F1；
- unknown Precision、Recall、F1；
- unknown 为正类的 AUROC、AUPR；
- 已知流量误拒为 unknown 的比例（known false-unknown）；
- 未知流量误判为已知的比例（unknown false-known）；
- 混合测试集整体 Accuracy、Macro-F1；
- `unknown_test_heldout` 与 `noise_test` 分层指标；
- 参数量、实际训练轮数和运行时间。

已知子集指标只在真值为已知的流量上计算；开放集整体 Macro-F1 在实际出现的 61 个标签上计算。不能只用 unknown F1 评价，拒识率提高时必须同时检查已知误拒率和整体 Macro-F1。单 seed 结果不写成均值±标准差。

## 6. 审计和验收

运行前检查：60 个已知类、开放模型 61 类输出、flow ID 无交集、unknown 应用隔离、噪声族隔离、scaler 只由训练集拟合、测试三类来源均非空。运行后检查 raw/threshold 指标、分类报告、参数量和时间均存在。项目测试、编译检查和 CUDA smoke test 通过后，才可将结果用于论文。
