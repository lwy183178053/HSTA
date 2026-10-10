# HSTA-CM：加密流量开放集识别

本仓库用于在 CESNET-TLS22 和 CESNET-QUIC22 的 S 子集上训练、评估 HSTA-CM 及保留的对比模型。每条流取前 30 个数据包，每个数据包使用 3 个可观测特征：包大小、方向和到达间隔，输入形状为 `[30, 3]`。

## 研究设定

- **HSTA-CM-open**：100 个已知类别加显式 `unknown` 类（共 101 类）。训练时加入未知支持流量，用于学习拒识边界。
- **HSTA-CM-closed 与对比模型**：只训练 100 个已知类别，不使用 `unknown` 标签。开放集测试时用验证集校准的置信度阈值拒识。
- 训练、验证、测试按日期划分，未知测试流量包括留出的真实应用和独立生成的噪声流量。
- “compact”只表示实验矩阵或采样规模较小，不表示模型参数量较少。所有采样配置使用相同模型结构。

HSTA-CM 的结构和 DFT 扩展见 [docs/architecture.md](docs/architecture.md)。完整开放集数据构造、unknown 隔离、指标和执行顺序以 [docs/experiment_protocol.md](docs/experiment_protocol.md) 为准。实验范围概览见 [docs/experiment_scope.md](docs/experiment_scope.md)，环境与复现步骤见 [docs/reproducibility.md](docs/reproducibility.md)。

保留的对比实现为 30pktTCNET-adapted、NetMamba-adapted、SRViT-adapted、TrafficAudio-adapted 和 BPF-GNN-adapted。它们统一使用 `[30, 3]` 输入，只保留各参考方法的主要建模思想，不宣称复现原论文的原始字节、图像、音频或旁信息管线。GRU 和独立 Transformer 不再作为单独对比模型；TrafficAudio 内部的 BiGRU 仍属于该方法本身。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/` | DataZoo 数据读取、预处理和开放集采样 |
| `models/` | HSTA-CM、HSTA-CM-DFT 及五个对比实现 |
| `configs/` | 主实验和 HSTA 组件消融配置 |
| `train.py` | 单个实验的训练、验证和测试 |
| `evaluate.py` | 加载检查点并评估 |
| `run_experiments.py` | 按 YAML 批量运行实验 |
| `scripts/` | WSL 运行入口、时间均衡采样和结果汇总 |
| `docs/` | 模型、实验协议、实验范围和复现说明 |

`data/processed/`、`results/`、`logs/` 和检查点属于本地生成物并被 Git 忽略。原始 H5 流量、凭据和本地环境不会提交到 Git。

## 环境

Windows 检查和安装使用项目 Anaconda 解释器：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

Mamba、CUDA 和 FlashAttention 实验必须在指定 WSL 环境运行：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## 数据与实验

使用已有的 CESNET-TLS22-S 和 CESNET-QUIC22-S 文件生成 100 个已知类别：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --datazoo-batch-size 2048 --datazoo-test-batch-size 2048
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --datazoo-batch-size 2048 --datazoo-test-batch-size 2048
```

正式矩阵和消融实验：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

为了快速检查流程，可先按时间窗口均衡采样，再运行 TLS 或 QUIC 的 seed 599：

```bash
python scripts/sample_temporal_dataset.py --input-csv data/processed/datazoo_tls100_s_seq30.csv --output-csv data/processed/datazoo_tls100_s_seq30_tiny.csv --dataset tls --profile tiny --seed 599
bash scripts/run_wsl_experiments.sh quick_tls
```

采样配置为每类训练/验证/测试最多 `100/20/20`（`tiny`）、`500/100/100`（`small`）、`1000/200/200`（`medium`）和 `10000/1000/2000`（`paper`）。采样单位是完整流，不跨时间窗口移动流量；样本规模改变不会改变模型结构或参数量。

主实验报告已知类别 Accuracy/Macro-F1、未知 Recall/Precision/F1、AUROC/AUPR、已知流量误拒率、参数量和运行时间。旧的 `results/compact_s_tls_seed599` 使用了所有模型都带 `unknown` 的旧协议，只能作为流程检查，不能用于证明开放集改进。
