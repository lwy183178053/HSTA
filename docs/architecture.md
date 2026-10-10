# HSTA-CM 模型结构

## 主模型

输入是每条流前 30 个数据包的 `[B, 30, 3]` 张量，3 个特征依次为包大小、方向和到达间隔。

1. **卷积分支**：三层 PyTorch `Conv1d` 提取相邻数据包的局部模式，并加入输入投影残差。
2. **时序分支**：两层当前 `mamba_ssm` Mamba 建模数据包顺序依赖，并加入时序嵌入残差。
3. **融合**：拼接两分支，经全连接层和门控融合。融合序列加入可学习的数据包位置编码，保证注意力和消融实验都保留顺序信息。
4. **注意力**：使用一个 PyTorch `scaled_dot_product_attention` 的 Flash 后端。配置要求 FlashAttention；CPU、数学实现和 memory-efficient 回退会被拒绝。注意力消融直接跳过该模块。
5. **输出**：LayerNorm、平均池化后接分类头。HSTA-CM-open 输出 100 个已知类别加 `unknown`（101 类）；HSTA-CM-closed 输出 100 个已知类别。

卷积或 Mamba 消融用同宽零分支替代，保持融合层形状不变，从而只比较被移除组件的影响。

## 开放集协议

HSTA-CM-open 在训练中使用声明的未知支持流量，并把测试时未见过的真实应用和独立噪声生成族映射为 `unknown`。留出的测试未知来源不能参与训练或阈值选择。

HSTA-CM-closed 和五个对比模型没有 `unknown` 输出，也不使用未知训练标签。它们先按 100 个已知类预测，再用验证集已知流量校准 `1 - max(softmax)` 阈值进行拒识。所有模型的已知分类结果和未知拒识结果分开报告。

## 对比模型

保留 30pktTCNET-adapted、NetMamba-adapted、SRViT-adapted、TrafficAudio-adapted 和 BPF-GNN-adapted。它们都接收相同的 `[30, 3]` 输入，是面向本项目输入的结构适配，不等同于原论文的完整数据管线。TrafficAudio 内部的 BiGRU 保留；GRU 和独立 Transformer 不单列。

## HSTA-CM-DFT 扩展

DFT 版本是独立的探索实验，不替代主模型：

1. 对 30 个数据包位置沿时间轴执行 `torch.fft.rfft`，使用正交归一化。
2. 实部和虚部堆叠为 `[B, 2, 3, 16]`，其中 16 是 `30 // 2 + 1` 个非冗余频率点。
3. 三层带残差的 PyTorch `Conv2d` 使用 `(1, 3)` 卷积核，只在相邻频率点上建模，不把三种特征误当作有空间邻接关系的图像像素。
4. 频域向量池化后广播到 30 个时序位置，与 Mamba 分支按主模型的门控、位置编码、FlashAttention 和分类头融合。

实数序列的 DFT 共轭对称，后半部分频率可以由前半部分恢复，因此 `rFFT` 的 16 个点已包含全部独立信息。CUDA 混合精度下先用 FP32 计算 FFT，以兼容长度 30。
