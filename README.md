# HSTA-CM 流量识别

本项目在 CESNET-TLS22-S 和 CESNET-QUIC22-S 上进行 60 类开放集流量识别。每个数据集独立按训练时间窗口的流量数量选择 60 个已知应用，其余可用应用作为真实 unknown 候选。每条流只取前 30 个包的包长、方向和包间隔，模型输入为 `[B, 30, 3]`。

## 数据

文件名中的 `s` 表示 CESNET 的 S 源数据集，不表示 small 档次。最终数据文件为：

- `data/processed/datazoo_tls60_s_protocol.csv`
- `data/processed/datazoo_quic60_s_protocol.csv`

每个已知类别的训练、验证、测试上限为 `10000/2000/2000`。真实 unknown 的目标数量是同一 split 已知流量的 30%，合成噪声目标数量是 10%；不足时按实际可用量导出，不重复流量。数据按固定日期窗口划分，unknown 应用身份和噪声生成族在集合之间隔离。CSV 附带 report、audit 和 sampling manifest；`original_app` 等审计字段不作为模型输入。

数据导出和正式实验是长任务，可由外部放到后台运行。启动器会写入 `logs/formal_pipeline.status`，并在整条队列完成后创建 `logs/formal_pipeline.completed`；状态文件尚未出现时，不能据此判断任务已完成，也不能把中间结果称为正式论文结果。

## HSTA-CM

主模型使用 256 维、76 个 token：

1. **Mamba 时序分支**：原始包序列经过线性投影和两层残差 Mamba，输出 30 个 token。
2. **包关系图分支**：每条流的包分别作为节点，使用带自环的相邻包关系和非相邻包特征相似关系，两层残差图消息传递分别聚合这两种关系，保留 30 个 token 位置。
3. **频谱卷积分支**：沿包序列做 rFFT，保留实部和虚部得到 16 个频率 token，投影到 256 维后使用卷积核 `1/3` 的两层残差 `Conv1d`。

三路来自同一份输入，分别建模包顺序、包间关系和频谱，不能称为三份独立采集信息。图仅在单条流内根据经已知训练流量 scaler 标准化的输入构建，不使用标签或其他流；补零包不参与构图和包分支池化。DFT 沿包序号计算，不能直接解释为真实时间的周期频率。三路分别做 LayerNorm，加入包位置编码（Mamba/GNN）、频率位置编码（DFT）和对应分支类型编码，拼接后经过融合层、单层 PyTorch FlashAttention、LayerNorm 和分类头。`HSTA-CM-open` 输出 61 类并训练 unknown；`HSTA-CM-closed` 输出 60 类，不使用 unknown 监督。新结构尚未训练，效果需要实验验证。

## 实验与运行

主比较包含 HSTA-CM open/closed 和五个统一 `[30,3]` 输入的适配基线：30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN。它们保留各自的建模思想，但不等同于原论文中的完整字节、音频、图或预训练管线。TrafficAudio 的内部 BiGRU 保留，不单独运行 GRU 或 Transformer。

- 主比较：`2 个数据集 × 7 个模型设置 × 3 个 seed = 42` 次训练。
- 消融：`no_mamba`、`no_gnn`、`no_dft`，每项只移除对应分支，共 `2 × 3 × 3 = 18` 次训练；`no_attention` 仅为可选补充，不计入正式矩阵。
- 效率：只测完整 HSTA-CM，推理 batch 为 `1/8/32`。

训练最多 100 轮，patience 为 15，按已知验证集 Macro-F1 调度和早停。目标有效优化器 batch 为 4096，验证和测试 batch 为 512；显存不足时使用微批次和梯度累积，并记录实际微批次。raw argmax 与 threshold rejection 分开评估，拒识阈值只用已知验证流量校准。

当前仅执行五个基线在两个数据集、三个 seed 上的 30 次训练。HSTA-CM 主模型、消融和效率任务暂不启动，待基线完成后再安排。当前 Git 保存的部分结果是进度快照，不代表完整三 seed 比较或新主模型结果。

训练和 FlashAttention 使用 WSL Ubuntu-22.04 环境；数据导出由 Windows 原生进程执行：

```powershell
Set-Location E:\AllProject\流量分析python项目\HSTA
& .\scripts\run_formal_pipeline.ps1
```

该入口默认只导出和审计数据，不自动开始训练；确认训练环境后再加 `-RunTraining`。

数据已经导出并通过审计后，也可以单独运行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
bash scripts/run_wsl_experiments.sh all
```

正式流水线让数据导出在 Windows 原生进程执行，以避免 WSL `/mnt/e` 的文件 I/O 开销；训练仍在 WSL 中执行。Windows 入口默认使用 2 个导出 worker，可按磁盘吞吐调整：

```powershell
& .\scripts\run_formal_pipeline.ps1 -DatazooWorkers 4
```

需要完全在 WSL 导出时，可以设置 `DATA_EXPORT_RUNTIME=wsl` 后直接运行 `bash scripts/run_formal_pipeline.sh`。GPU 不参与 H5 解码和 CSV 序列化，留给后续模型训练。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/raw/` | 本地 H5 和应用映射 |
| `data/processed/` | 两份正式 CSV 及审计文件 |
| `models/` | HSTA-CM、Mamba、FlashAttention 和五个基线 |
| `configs/` | 主比较和消融配置 |
| `train.py`、`evaluate.py` | 训练和评估入口 |
| `run_experiments.py` | 多模型、多数据集、多 seed 批量运行 |
| `scripts/` | 导出、审计、运行和结果汇总 |
| `results/` | 数值指标、训练历史、运行配置与本地 checkpoint |
| `logs/` | 本地运行日志和状态文件 |
| `docs/` | 协议、架构、范围和复现说明 |

代码、配置、测试、文档，以及轻量的数值结果、训练历史和运行配置（CSV/JSON/YAML/Markdown）提交 Git。数据、原始 H5、日志、checkpoint、预测明细和二进制产物不提交。运行中的结果快照需标明未完成状态。论文文件放在仓库外的 `E:\AllProject\流量分析python项目\paper`。
