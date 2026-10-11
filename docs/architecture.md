# HSTA-CM 三路主模型

两个数据集使用相同结构，输入 [B,30,3]，通道为包长、方向和包间隔，隐藏维度为 256。scaler 只用训练流拟合。

## 三路提取

| 分支 | 操作 | token |
| --- | --- | ---: |
| 时序状态空间分支 | 输入线性投影、两层残差 Mamba、分支输入到输出残差、LayerNorm | 30 |
| 包序列多尺度卷积分支 | 通道投影、三层残差 Conv1d，核 1/3/5、LayerNorm | 30 |
| 频域多尺度卷积分支 | rFFT、实虚拼接、LayerNorm、通道投影、三层残差 Conv1d，核 1/3/5 | 16 |

卷积使用 PyTorch Conv1d、BatchNorm、GELU、Dropout，以 x + block(x) 逐层更新。Mamba 使用 mamba_ssm 实现。rFFT 沿 30 个包的序列轴执行正交归一化；实信号共轭对称，因此只需 16 个独立频率点。实部和虚部拼接为 [B,16,6]，保留相位信息，不只是幅值。

## 编码与融合

两条包分支使用共享的可学习包位置编码，频域分支使用独立的频率位置编码。三条分支分别加入 Mamba、原始包卷积、频域卷积的类型编码。

按 Mamba、原始包卷积、频域卷积的顺序拼接为 [B,76,256]，经逐 token 融合全连接、GELU、Dropout，再进入一层 FlashAttention 块。块内为 pre-LayerNorm 自注意力与残差，再接 pre-LayerNorm 前馈网络与残差；CUDA 正式运行强制使用 PyTorch SDPA FlashAttention 后端。

最后 LayerNorm 后分别对三路 token 求均值，再对三路均值等权平均，避免较长分支仅因 token 多获得更高权重。分类头 open 为 61 类、closed 为 60 类。

## 消融与基线

- no_conv-open：移除原始包和频域两条卷积路径，保留 Mamba；测量卷积路径整体贡献。
- no_mamba-open：移除 Mamba，保留两条卷积路径；测量时序状态空间路径贡献。
- no_attention-open：保留三路、编码、融合与输出归一化，移除完整 FlashAttention 块及块内前馈网络；测量注意力融合块贡献。

三项消融保持 256 维、相同数据、三个 seed 和 unknown 支持训练。移除分支会改变 token 数及参数量，须如实报告。这三项不能单独证明频域分支、编码和残差各自的收益。

五个基线保留核心建模思想，属于统一 [30,3] 输入下的适配比较，不声称还原原论文全部字节、图像、音频、图或旁信息管线。TrafficAudio 的内部 BiGRU 属于该模型。
