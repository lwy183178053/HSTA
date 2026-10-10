# HSTA-CM 模型结构

## 主模型：HSTA-CM-DFT

输入是每条流前 30 个数据包的 `[B, 30, 3]` 张量，3 个特征为包大小、方向和到达间隔。30 是 CESNET-TLS22/QUIC22 的 PPI 协议长度，不代表可以任意扩展或截断的数据集变体。

1. **频域卷积分支**：沿 30 个数据包位置执行 `torch.fft.rfft`，紧凑主配置保留每个原始特征通道的实部和虚部，再用三层 PyTorch `Conv1d`（核大小为 3）提取相邻频率点模式。每层卷积都使用残差连接，并保留输入投影残差。幅值表示仍保留为参数匹配的筛选变体。
2. **时序分支**：两层当前 `mamba_ssm` Mamba 直接建模原始数据包顺序依赖，并加入时序嵌入残差。
3. **融合**：紧凑主配置使用 `fusion_mode: tokens`，保留全部 16 个非冗余频点作为频域 Token，与 30 个时序 Token 拼接后交给 FlashAttention；`pooling: temporal_mean` 只汇聚时序 Token，频域 Token 仍作为注意力上下文。`pooled` 是不保留频点局部结构的直接对照。两种融合序列都加入可学习的位置编码和分支类型编码。
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

## DFT 表示与筛选结论

1. 对 30 个数据包位置沿时间轴执行 `torch.fft.rfft`，使用正交归一化。
2. 幅值对照使用 `log1p` 压缩动态范围，输入为 `[B, 3, 16]`；紧凑主配置的实虚部输入为 `[B, 6, 16]`，保留相位相关信息，但这里不把实部/虚部误称为振幅/相位。实数序列的 `rFFT` 16 个复数点已经包含完整非冗余频谱；不能把 16 强行插值成 30 个包位置，因为频率轴和包序列轴语义不同。
3. 三层带残差的 PyTorch `Conv1d` 使用大小为 `3` 的卷积核，在相邻频率点上建模。
4. `pooled` 模式对频率轴做全局池化；`tokens` 模式保留 16 个频点，经频域局部卷积后直接参与 FlashAttention。后者用于检验“池化是否抹掉频点局部结构”，不是默认主配置的隐式替换。

实数序列的 DFT 共轭对称，后半部分频率可以由前半部分恢复，因此 `rFFT` 的 16 个点已包含全部独立信息。CUDA 混合精度下先用 FP32 计算 FFT，以兼容长度 30。

筛选实验固定 TLS22-S/QUIC22-S、seed `599`、30 epoch、相同 unknown 协议和 FlashAttention。TLS small 中，实虚部 Token + 时序汇聚的验证开放集 Macro-F1 约为 `0.794`，幅值 Token + 时序汇聚约为 `0.773`；QUIC small 中幅值 Token + 时序汇聚约为 `0.691`，实虚部 Token + 时序汇聚约为 `0.682`。QUIC 的 no-DFT 验证开放集 Macro-F1 约为 `0.693`，高于实虚部池化 DFT 的约 `0.667`。这些结果表明 Token 化比简单池化更值得继续验证，但尚未证明 DFT 在两个数据集上稳定优于 no-DFT；正式主结果必须按验证集预注册规则选型，再用 `599、5009、813` 三个种子在 `paper` 规模重跑。

设计依据可参考 [FNet](https://arxiv.org/abs/2105.03824) 的 Fourier token mixing、[TimesNet](https://arxiv.org/abs/2210.02186) 的时序变化建模，以及 [FEDformer](https://arxiv.org/abs/2201.12740) 的频域分解思路。它们支持保留频率结构并交给后续混合器，但不意味着对只有 30 个包的流量输入必然带来增益。
