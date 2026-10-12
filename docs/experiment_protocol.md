# 60 类开放集实验协议

本协议适用于 CESNET-TLS22-S 和 CESNET-QUIC22-S。两个数据集独立选择已知应用和类别映射，数据采样 seed 为 599；训练 seed 为 `599/5009/813`。

## 数据划分

| 数据集 | 训练窗口 | 验证窗口 | 测试窗口 |
| --- | --- | --- | --- |
| TLS22-S | 2021-10-04 至 2021-10-10 | 2021-10-11 | 2021-10-12 至 2021-10-17 |
| QUIC22-S | 2022-10-31 至 2022-11-13 | 2022-11-14 至 2022-11-15 | 2022-11-16 至 2022-11-27 |

各自按训练窗口流量量排序选出 60 个已知应用，其余可识别应用构成 unknown 候选池。已知类每类训练/验证/测试上限为 `10000/2000/2000`。真实 unknown 每个 split 目标为已知流量数的 30%，合成噪声目标为 10%，不足时按实际量记录，不跨时间补采、不重复抽样。

真实未知应用在归并为 unknown 前分成训练支持、验证留出和测试留出来源组，应用身份不得跨组。训练、验证和测试噪声使用不同生成族。CSV 中日期、flow ID、原始应用名、来源组和噪声族只用于审计，不输入模型。Scaler 只在已知训练流量上拟合。

## 模型与深度控制

主模型是 256 维三视图 HSTA-CM：两层残差 Mamba、两层残差包关系图消息传递、两层核 1/3 的残差 DFT 卷积，拼成 76 token 后经一层 FlashAttention。五个适配基线为 30pktTCNET-adapted、NetMamba-adapted、SRViT-adapted、TrafficAudio-adapted 和 BPF-GNN-adapted。所有模型以相同 `[30,3]` 输入和类别划分训练。架构深度按串行主干块报告，每条主干路径最多四块；多分支分别说明深度，不能把并行深度相加。

宽度按容量匹配到约 2.21–2.30M 参数。训练开始前必须从实际构建的模型统计参数量，并保存到运行配置与结果。适配模型保留各自的核心计算思想，但不是原论文完整输入或训练管线的复现。

## 主比较和消融

主比较包含 HSTA-CM-open、HSTA-CM-closed 和五个适配基线，在两个数据集分别使用三个 seed，共 42 次训练。open 训练时使用 unknown 支持流量和训练噪声，输出 61 类；closed 及基线只用已知类训练，输出 60 类。

消融包括 `no_mamba`、`no_gnn`、`no_dft`，只移除相应分支，其余数据、seed、训练策略和 unknown 监督相同，共 18 次运行。效率实验测完整 HSTA-CM，在 TLS 和 QUIC 上分别使用推理 batch `1/8/32`。

## 训练设置

- 最多 100 轮，patience 15。
- 按已知验证集 Macro-F1 调度学习率和早停。
- 目标有效训练 batch 为 4096；受显存约束时使用微批次和梯度累积，记录实际设置。评估 batch 为 512。
- 每个 seed 独立初始化、从第 1 轮训练，不复用其他配置的 checkpoint。
- HSTA-CM 的 Mamba selective block 在 autocast 外强制 FP32；NetMamba 全模型关闭 AMP；其余模型可使用 AMP。必须在运行结果披露精度模式。

## 开放集评价

阈值只用已知验证流量校准，验证未知流量和测试流量不参与阈值选择。每个模型保存 raw argmax 与 threshold rejection 两种结果。open 模型用显式 unknown 类；closed 和闭集基线以 `1-max(known probability)` 作为拒识分数。

分别报告：

- 已知测试子集的 Accuracy、Macro-F1；
- unknown Precision、Recall、F1、AUROC、AUPR；
- 已知流量被拒为 unknown 的比例；
- unknown 被分到已知类的比例；
- 混合测试集 Accuracy、Macro-F1；
- `unknown_test_heldout` 和 `noise_test` 的分层结果；
- 参数量、训练轮数、训练耗时和推理效率。

闭集模型的 unknown 指标衡量拒识分数能力，不表示模型接受过 unknown 类监督。AUROC/AUPR 是阈值无关的排序指标；F1 和误拒率反映指定阈值下的行为。

## 审计要求

需检查 60 个已知类、open/closed 输出维度、日期范围、跨 split flow ID 无交集、unknown 应用身份隔离、噪声族隔离、无重复采样，以及所有 unknown `requested/available/actual` 数量。模型检查需确认输入 `[B,30,3]`、HSTA-CM token 数 76、实际参数量及 FlashAttention 后端状态。训练队列全部完成前只能报告中间进度，不能作为完整三 seed 论文主结果。
