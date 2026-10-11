# 60 类开放集正式实验协议

TLS22-S 与 QUIC22-S 各一份最终数据。数据 seed 为 599，训练 seed 为 599、5009、813，三次训练共享固定数据与类别映射。

## 数据采集与时间窗口

直接扫描原始 H5 和 servicemap。第一遍统计各日期窗口的数量，按训练窗口数量降序、并列按应用名排序，独立选前 60 个已知应用；其余可辨识应用形成完整真实 unknown 候选池。第二遍按来源组无放回采样，直接写最终 CSV，不保留 source 候选 CSV 或多个规模档。

| 数据集 | 训练 | 验证 | 测试 |
| --- | --- | --- | --- |
| TLS22-S | 20211004–20211010，7 天 | 20211011，1 天 | 20211012–20211017，6 天 |
| QUIC22-S | 20221031–20221113，14 天 | 20221114–20221115，2 天 | 20221116–20221127，12 天 |

日期含首尾日。每个已知类训练/验证/测试上限 10000/2000/2000。每个 split 按实际已知数量计算 30% 真实 unknown 和 10% 噪声预算。不足时保留可用量，记录 requested、available、actual 和实际比例，不重复、不跨日期补足。

最终文件为 data/processed/datazoo_tls60_s_protocol.csv 和 data/processed/datazoo_quic60_s_protocol.csv，各附 report、audit、sampling manifest。保留 split、日期、flow ID、original_app、source_group、noise_family 供审计，模型只接收 PPI 特征。scaler 只在训练集拟合。

## Unknown 与噪声隔离

unknown 来自未入选 60 类的真实应用及合成噪声，不直接把原始模糊标签当作有可审计身份的应用。可辨识应用先固定分组再折叠标签：unknown_support 仅进入训练；unknown_val_heldout 仅进入验证；unknown_test_heldout 仅进入测试。完整候选清单及三组清单落盘，同一应用不得跨组。

真实 unknown 在对应日期内按应用均衡采样，来源耗尽后剩余预算分配给尚有可用量的应用，不能用测试应用补训练。noise_train、noise_val、noise_test 使用互斥生成族；名称及 seed 写入报告。审计字段不得作为输入。

## 训练和校准

open 和消融训练已知、unknown 支持及训练噪声，输出 61 类；closed 与五个基线仅训练已知，输出 60 类。完整 HSTA-CM 固定三路 76 token、256 维。

从第 1 轮开始，不恢复旧 checkpoint。最大 100 轮、patience 15，学习率和早停统一依已知验证 Macro-F1。测试不参与类别选择、scaler 拟合、epoch 或阈值选择。

目标有效优化器 batch 为 4096，验证/测试 batch 为 512。CUDA OOM 时依次尝试 2048、1024、512 微批次并累积梯度，每 4096 个样本执行一次优化器更新；日志和结果记录实际微批次及是否回退。该处理保持梯度按 4096 个样本归一化，但含 BatchNorm 的模型在回退时会按微批次计算批次统计量，不能视为与单次 4096 前向完全等价；主 HSTA-CM 必须通过 4096 批次 CUDA smoke test。若所有回退尺寸仍 OOM，该次运行失败并保留错误日志，不会改变优化器批次。

保存 raw argmax 和 threshold rejection。open unknown 分数为显式 unknown 概率；closed/基线为 1-max(softmax)。阈值仅由已知验证流量校准，未知验证与测试不参与。校准分位数、阈值和原始预测必须保存。

## 评价与验收

两套预测各报告已知 Accuracy/Macro-F1，unknown Precision/Recall/F1，unknown 为正类的 AUROC/AUPR，已知误拒率、未知误判为已知比例，混合测试 Accuracy/Macro-F1，参数量、实际训练轮数、时间。真实留出应用与 noise_test 分层报告实际数量。AUROC/AUPR 是分数排序指标，相同分数下换阈值不会改变它们；缺少正类或负类的分层标为不可计算。

已知 Macro-F1 覆盖固定 60 个类别，缺样类别在支持数中说明；整体 Macro-F1 覆盖已知与 unknown。报告三 seed 单次值及 mean±std。拒识效果必须结合已知误拒率，不能只看 unknown F1。

审计类别数、日期、flow ID 无交集、unknown 应用互斥、噪声族互斥、无重复采样和 requested/actual 数量。pytest、编译、CUDA smoke test 检查 [2,30,3] 输入、76 token、61/60 输出及 FlashAttention 后端。通过后启动正式队列，失败或未完成运行不得当作论文主结果。
