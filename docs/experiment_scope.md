# 实验范围与评价指标

完整执行口径见 [experiment_protocol.md](experiment_protocol.md)。本文件保留实验矩阵和指标的快速概览；若两者出现差异，以实验协议为准。

## 数据与划分

实验使用 CESNET-TLS22-S 和 CESNET-QUIC22-S。每个数据集选取 100 个已知应用类别，按日期划分训练、验证和测试；同一条流不会跨集合。输入统一为前 30 个数据包的 3 个特征。

## 主实验矩阵

主比较包含：

- HSTA-CM-open：训练 100 个已知类和显式 `unknown` 类（101 类），使用种子 `599、5009、813`。
- HSTA-CM-closed：同一结构但不训练 `unknown`，作为拒识训练对照。
- 30pktTCNET-adapted、NetMamba-adapted、SRViT-adapted、TrafficAudio-adapted、BPF-GNN-adapted：100 类闭集训练，不使用未知标签；紧凑重跑暂用 seed `599`。
- HSTA-CM-DFT：每个数据集一个 seed `599` 的频域扩展结果，单独报告。

“compact”表示数据量或实验矩阵精简，不表示低参数量模型。所有采样规模使用相同的模型超参数。

## 开放集验证

测试集混合已知流量、训练中未出现的真实应用流量和未见过的噪声生成族。HSTA-CM-open 直接输出 `unknown`；闭集模型使用 `1 - max(softmax)`，阈值仅由已知验证流量的 95% 接受分位点确定，不使用未知测试样本调阈值。

分别报告：

- 已知类别 Accuracy、Macro-F1；
- `unknown` Recall、Precision、F1；
- unknown AUROC/AUPR；
- 已知流量误拒率和未知流量误判为已知的比例；
- 拒识后的整体开放集指标、参数量和运行时间；
- 按真实留出应用和噪声来源拆分的未知结果。

不能只报告未知 F1；提高拒识率若同时误拒大量已知流量，不代表模型更好。

## 消融与效率

HSTA-CM 组件消融在两个数据集上各比较三项：去掉卷积分支、去掉 Mamba 分支、去掉 FlashAttention。替代分支保持张量宽度和训练协议一致，消融模型仍使用显式 `unknown` 训练。

效率实验只测 batch size `1、8、32`，报告参数量、MACs/FLOPs、延迟、吞吐量和 CUDA 峰值显存，不计入数据加载时间。

40 类、60 类、独立 GRU、独立 Transformer、层数/宽度扫描和旧证据包不再属于当前实验矩阵。DFT 只作为扩展实验，不扩展主对比和消融矩阵。

## 结果报告

HSTA-CM-open 的三次种子结果报告均值和标准差。对比模型当前只有 seed 599 时，按单次结果报告，不填写虚假的标准差。旧目录 `results/compact_s_tls_seed599` 使用了所有模型都训练 `unknown` 的旧协议，只作流程检查。
