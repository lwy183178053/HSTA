# 60 类开放集实验协议

本协议适用于 TLS22-S 和 QUIC22-S。两份数据独立选取已知类别和类别映射，数据生成 seed 为 599，训练 seed 为 `599/5009/813`。

## 数据生成

通过 CESNET-DataZoo 读取原始 H5 和 servicemap，不使用中间 source 数据集。第一遍统计当前 S 数据集训练窗口中的可辨识应用数量，按数量降序、应用名排序选择前 60 个已知应用；其余可辨识应用组成完整 unknown 候选池。第二遍按来源组无放回采样并写出最终 CSV。

| 数据集 | 训练 | 验证 | 测试 |
| --- | --- | --- | --- |
| TLS22-S | 2021-10-04 至 2021-10-10 | 2021-10-11 | 2021-10-12 至 2021-10-17 |
| QUIC22-S | 2022-10-31 至 2022-11-13 | 2022-11-14 至 2022-11-15 | 2022-11-16 至 2022-11-27 |

每个已知类别上限为训练/验证/测试 `10000/2000/2000`。每个 split 的真实 unknown 预算为已知流量的 30%，噪声预算为 10%。不足时报告 `requested/available/actual`，不重复流量、不跨日期补采。

真实 unknown 应用在折叠为 `unknown` 前划分为 `unknown_support`、`unknown_val_heldout` 和 `unknown_test_heldout`，同一应用不能跨组。训练、验证、测试使用不同的噪声生成族。CSV 保留 `split`、日期、flow ID、`original_app`、`source_group` 和 `noise_family` 供审计，但这些字段不输入模型。scaler 只用训练集拟合。

## 训练

open 和三项消融使用已知类别、unknown 支持流量和训练噪声训练，输出 61 类；closed 和五个基线只使用已知类别训练，输出 60 类。所有运行从第 1 轮开始，不复用旧 checkpoint。

主模型为 Mamba、包关系图、DFT-CNN 三路 HSTA-CM。正式消融为 `no_mamba`、`no_gnn`、`no_dft`，每次只移除一个分支，保持其余结构与训练设置不变；`no_attention` 不纳入当前正式矩阵。当前仅运行五个基线，更新后的主模型及消融待基线完成后另行启动，不为已有结果更改模型身份。

最大训练轮数为 100，patience 为 15；学习率调度和早停指标均为已知验证集 Macro-F1。目标有效优化器 batch 为 4096，验证/测试 batch 为 512。显存不足时按配置使用微批次和梯度累积，实际值写入日志和结果。

阈值只用已知验证流量校准，未知验证和测试流量不参与阈值选择。open 使用显式 unknown 概率作为拒识分数；closed 和基线使用 `1 - max(known probability)`。raw argmax 与 threshold rejection 必须分别落盘。

## 评价和审计

已知 Accuracy/Macro-F1 只在真实已知测试流量子集上计算；开放集整体 Accuracy/Macro-F1 在包含已知、真实 unknown 和测试噪声的混合测试集上另行计算。另报告 unknown Precision/Recall/F1、AUROC/AUPR、已知误拒率、未知误判为已知比例、参数量、训练轮数和时间。真实留出应用和 `noise_test` 分层报告实际数量。

审计必须确认：60 个已知类别、输出类别数、日期范围、flow ID 无交集、unknown 应用身份不跨集合、噪声族不跨集合、无重复采样，以及所有 `requested/available/actual` 数量。模型验收还要确认输入为 `[B,30,3]`、完整模型为 76 个 token、open/closed head 为 61/60 类，并实际启用 PyTorch FlashAttention。未完成或未通过审计的运行不能作为论文主结果。
