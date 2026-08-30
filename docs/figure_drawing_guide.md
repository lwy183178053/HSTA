# 论文创新点绘图指南

本文档用于根据当前代码绘制论文中的两张核心图：

1. HSTA 模型架构图
2. 数据处理流程图

`paper/` 目录是论文归档目录，本项目代码和本文档均不修改其中内容。

## 一、HSTA 模型架构图

### 重点阅读文件

按下面顺序阅读即可：

1. `configs/hsta_flash.yaml:19`

   确认最终模型配置：

   ```text
   model: hsta
   dim: 128
   heads: 4
   layout: [mamba, mamba, mlp, attention, mlp]
   attention_backend: flash
   ```

2. `models/hsta.py:37`

   这是 HSTA 的总装配文件，负责按照配置创建模型模块。

3. `models/mamba_model.py:10`

   查看 Mamba 模块内部结构。

4. `models/transformer.py:8`

   查看多头注意力；`models/transformer.py:84` 查看前馈网络 FFN。

5. `models/__init__.py:110`

   只用于确认 `model: hsta` 最终调用 HSTA 工厂，不需要作为架构图主体。

### 主结构

```text
[B, 30, 3]
包大小、传输方向、包间隔时间
        |
Linear(3 -> 128) + 位置编码
        |
Mamba Block
        |
Mamba Block
        |
Transition FFN
128 -> 512 -> 128
        |
四头注意力
Q/K/V 投影 -> SDPA FlashAttention -> 输出投影
        |
Refinement FFN
128 -> 512 -> 128
        |
LayerNorm
        |
Mean Pooling
        |
Linear(128 -> 类别数)
        |
分类结果
```

### 模块内部结构

Mamba Block：

```text
输入 x
  -> LayerNorm
  -> Mamba Mixer
  -> Dropout
  -> Residual Add
  -> 输出
```

Attention Block：

```text
输入 x
  -> LayerNorm
  -> Q/K/V Linear Projection
  -> Multi-Head Attention
  -> Output Projection
  -> Residual Add
  -> 输出
```

FFN Block：

```text
输入 x
  -> LayerNorm
  -> Linear(128 -> 512)
  -> GELU
  -> Dropout
  -> Linear(512 -> 128)
  -> Dropout
  -> Residual Add
  -> 输出
```

### 画图时需要标注的形状

- 输入：`[B, 30, 3]`
- 输入映射后：`[B, 30, 128]`
- 每个 Mamba、FFN 和 Attention 模块之后：`[B, 30, 128]`
- 均值池化后：`[B, 128]`
- 分类器输出：`[B, num_classes]`

`Transition FFN` 和 `Refinement FFN` 在代码中都由 `FeedForwardBlock` 实现。它们的论文名称来自它们在 HSTA 中的功能和位置。

### 消融结构

注意力位置消融配置位于 `configs/hsta_flash_ablation.yaml`，无注意力配置位于 `configs/hsta_no_attention.yaml`。

```text
完整 HSTA：       Mamba -> Mamba -> FFN -> Attention -> FFN
前置注意力：      Attention -> Mamba -> Mamba -> FFN -> FFN
中置注意力：      Mamba -> Attention -> Mamba -> FFN -> FFN
无注意力：        Mamba -> Mamba -> FFN -> FFN -> FFN
```

## 二、数据处理流程图

### 重点阅读文件

1. `data/preprocess.py:29`

   数据处理命令行入口，负责设置数据集、数据规模、类别数量、序列长度和样本上限。

2. `data/sampler.py:314`

   初始化 TLS/QUIC DataZoo 数据集，并设置训练、验证和测试时间段。

3. `data/sampler.py:395`

   从 PPI 数据中解析时间、方向和包大小。

4. `data/sampler.py:431`

   扫描训练数据并选择 Top-K 类别。

5. `data/sampler.py:441`

   将筛选后的 flow 和三个特征导出为统一 CSV。

6. `data/dataset.py:47`

   读取 CSV，并将 packet 行按 `flow_id` 重组为固定长度的 flow 张量。

7. `data/dataset.py:142`

   只使用训练集拟合 `StandardScaler`，再处理验证集和测试集。

8. `data/dataset.py:153`

   创建训练、验证和测试 DataLoader。

### 数据处理流程

```text
DataZoo 原始数据
        |
TLS/QUIC 数据集初始化
        |
按时间段划分 train / val / test
        |
扫描训练集类别
        |
选择 Top-K 类别
        |
解析 PPI
        |
提取 size / direction / delta_time
        |
保留每条 flow 的前 30 个包
        |
导出统一 CSV
        |
按 flow_id 重组为 [flow, 30, 3]
        |
不足 30 个包时补零
        |
仅用训练集拟合标准化参数
        |
生成 Train / Validation / Test DataLoader
```

### CSV 字段

```text
flow_id
label
pkt_index
size
direction
delta_time
split
```

模型实际使用的输入特征是：

```text
[size, direction, delta_time]
```

`flow_id`、`label`、`pkt_index` 和 `split` 是元数据或标签，不作为模型输入特征。

### 数据图中的关键说明

- 数据处理的基本单位是 flow，而不是单独的 packet。
- 一条 flow 最多保留前 30 个 packet。
- 不足 30 个 packet 的 flow 使用零填充。
- 如果 CSV 已经提供 `train`、`val`、`test`，代码优先使用已有划分。
- 如果 CSV 没有完整划分，代码使用分层随机划分。
- 标准化参数只从训练集计算，避免验证集和测试集信息泄漏。
- `delta_time` 在导出阶段从 DataZoo 的 PPI 特征解析并写入 CSV。绘图时不要额外标成代码重新计算相邻包时间差，除非你确认原始 PPI 字段的具体定义。

## 三、可以忽略的文件

绘制这两张创新点图时，不需要重点阅读：

- `train.py`：只负责连接数据管线、模型、优化器和训练循环。
- `evaluate.py`：用于独立评估 checkpoint。
- `benchmark_efficiency.py`：用于参数量、FLOPs、延迟和显存统计。
- `models/gru.py`：GRU 对比模型。
- `models/adapted_sota.py`：SOTA 适配对比模型。
- `models/recent_journal_baselines.py`：近期论文结构对比模型。

## 四、推荐的两张图标题

```text
图 1. HSTA 模型架构与信息流
图 2. 面向加密流量分类的 DataZoo 数据处理流程
```
