# 项目架构

## 统一输入

数据管线将每条加密 flow 转换为 `[B, 30, 3]`：

```text
包大小 | 传输方向 | 包间隔时间
```

- `data/preprocess.py`：从 DataZoo 原始数据生成统一 CSV。
- `data/dataset.py`：读取 CSV，按 flow 划分数据集，完成标准化并创建 DataLoader。
- `data/sampler.py`：提供数据采样和类别平衡相关逻辑。

训练和测试使用 flow 级、时间隔离的划分，避免同一 flow 的数据泄漏到不同集合。

## HSTA 主模型

`models/hsta.py` 实现论文修改版 10 的主结构：

```text
[B,30,3]
  -> Linear(3,128) + 位置编码
  -> Mamba 模块
  -> Mamba 模块
  -> Transition FFN: 128 -> 512 -> 128
  -> 四头注意力
  -> Refinement FFN: 128 -> 512 -> 128
  -> LayerNorm + 均值池化
  -> Linear(128, 类别数)
```

所有序列模块保持 `[B,30,128]`。`models/mamba_model.py` 提供残差 Mamba 模块，`models/transformer.py` 提供注意力和前馈模块。HSTA 工厂还支持无注意力、前置注意力和中置注意力消融。

最终 HSTA 使用 PyTorch SDPA 的 FlashAttention 后端；它是实现层面的效率优化，不改变论文中的注意力定义。

## 对比模型

```text
models/gru.py                      五层 GRU
models/transformer.py              五层 Transformer
models/adapted_sota.py             30pktTCNET、NetMamba 适配版本
models/recent_journal_baselines.py SRViT、TrafficAudio、BPF-GNN
```

所有模型共用相同的输入、训练入口和评估流程。近期基线保留各自的核心结构，例如 TrafficAudio 的 MFCC/CNN 分支和 BPF-GNN 的分层图构造。

## 运行关系

```text
configs/*.yaml
       |
       v
run_experiments.py -> train.py -> data.dataset + models.build_model
       |                              |
       v                              v
results/<实验组>/<实验名>/       best.pt / latest.pt / metrics.json
       |
       +-> evaluate.py
       +-> benchmark_efficiency.py
       +-> summarize_paper_main_results.py
```

`paper/` 不在上述运行链路中，仅作为论文归档目录保存。
