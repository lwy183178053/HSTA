# HSTA-CM 模型结构

## 主模型：HSTA-CM-DFT

输入是每条流前 30 个数据包的 `[B, 30, 3]` 张量，3 个特征为包大小、方向和到达间隔。30 是 CESNET-TLS22/QUIC22 的 PPI 协议长度，不代表可以任意扩展或截断的数据集变体。

1. **频域卷积分支**：沿 30 个数据包位置执行 `torch.fft.rfft`，保留每个原始特征通道的频谱幅值，再用三层 PyTorch `Conv1d`（核大小为 3）提取相邻频率点模式。每层卷积都使用残差连接，并保留输入投影残差。
2. **时序分支**：两层当前 `mamba_ssm` Mamba 直接建模原始数据包顺序依赖，并加入时序嵌入残差。
3. **融合**：将频域向量扩展到包序列后与 Mamba 序列拼接，经全连接层和门控融合。融合序列加入可学习的数据包位置编码，保证注意力和消融实验都保留顺序信息。
4. **注意力**：使用一个 PyTorch `scaled_dot_product_attention` 的 Flash 后端。配置要求 FlashAttention；CPU、数学实现和 memory-efficient 回退会被拒绝。注意力消融直接跳过该模块。
5. **输出**：LayerNorm、平均池化后接分类头。HSTA-CM-DFT-open 输出 100 个已知类别加 `unknown`（101 类）；HSTA-CM-DFT-closed 输出 100 个已知类别。

结果文件中的 `hybrid_layers` 是 `layout` 结构阶段计数，不是卷积层、Mamba 层或注意力层的总数。DFT 主模型多记录一个 FFT 阶段，因此该字段比 no-DFT 消融大 1；两者的可训练参数量不由序列长度（30 或 16）决定。

## 开放集协议

HSTA-CM-DFT-open 在训练中使用声明的未知支持流量，并把测试时未见过的真实应用和独立噪声生成族映射为 `unknown`。留出的测试未知来源不能参与训练或阈值选择。

HSTA-CM-DFT-closed 和五个对比模型没有 `unknown` 输出，也不使用未知训练标签。它们先按 100 个已知类预测，再用验证集已知流量校准 `1 - max(softmax)` 阈值进行拒识。所有模型的已知分类结果和未知拒识结果分开报告。

## 对比模型

保留 30pktTCNET-adapted、NetMamba-adapted、SRViT-adapted、TrafficAudio-adapted 和 BPF-GNN-adapted。它们都接收相同的 `[30, 3]` 输入，是面向本项目输入的结构适配，不等同于原论文的完整数据管线。TrafficAudio 内部的 BiGRU 保留；GRU 和独立 Transformer 不单列。

## HSTA-CM-no-DFT 消融

no-DFT 版本保留 Mamba、FlashAttention、融合层和分类头，仅将频域卷积分支替换为同宽、同深度、同样逐层残差的原始时域 `Conv1d` 分支。它使用相同的数据、训练预算和 unknown 协议，用于隔离 DFT 对结果的贡献。

## DFT 表示

1. 对 30 个数据包位置沿时间轴执行 `torch.fft.rfft`，使用正交归一化。
2. 只保留每个原始特征通道的频谱幅值并使用 `log1p` 压缩动态范围，输入保持为 `[B, 3, 16]`；不拆分实部/虚部或振幅/相位，也不扩展频域矩阵。
3. 三层带残差的 PyTorch `Conv1d` 使用大小为 `3` 的卷积核，在相邻频率点上建模。
4. 频域向量池化后与 Mamba 分支按主模型的门控、位置编码、FlashAttention 和分类头融合。

实数序列的 DFT 共轭对称，后半部分频率可以由前半部分恢复，因此 `rFFT` 的 16 个点已包含全部独立信息。CUDA 混合精度下先用 FP32 计算 FFT，以兼容长度 30。
