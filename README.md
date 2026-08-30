# 加密 QUIC/TLS 流量分类实验项目

这是一个基于 PyTorch 的加密流量分类项目，代码和实验配置按论文修改版 10 整理。所有模型统一使用每条 flow 前 30 个包的三个侧信道特征：包大小、传输方向和包间隔时间，输入形状为 `[B, 30, 3]`。

## 项目架构

```text
数据文件
  -> data/preprocess.py      DataZoo 数据预处理
  -> data/dataset.py         flow 划分、标准化和 DataLoader
  -> run_experiments.py      按 YAML 批量运行实验
  -> train.py                训练、验证、测试和断点续训
  -> models/__init__.py      统一模型工厂
  -> results/<实验组>/<实验名>/  checkpoint 和指标
```

核心模型结构和依赖关系见 [docs/architecture.md](docs/architecture.md)。
绘制 HSTA 架构图和数据处理图时，按 [docs/figure_drawing_guide.md](docs/figure_drawing_guide.md) 的文件顺序阅读。

## 代码目录

```text
data/                         数据读取、预处理和采样
models/
  hsta.py                     HSTA 及注意力位置消融
  mamba_model.py              Mamba 模块和 NetMamba 适配主干
  gru.py                      GRU 基线
  transformer.py              Transformer 基线和注意力模块
  adapted_sota.py             30pktTCNET、NetMamba 适配版本
  recent_journal_baselines.py SRViT、TrafficAudio、BPF-GNN
configs/                      最终实验配置
scripts/                      批量运行和结果汇总脚本
tests/                        模型、配置和结果测试
docs/                         架构与实验说明
train.py                      单实验训练入口
run_experiments.py            配置文件批量训练入口
evaluate.py                   checkpoint 独立评估
benchmark_efficiency.py       参数量、FLOPs、延迟和显存测试
```

`paper/` 只保存论文原稿、投稿包和图稿，不参与代码运行，也不由项目脚本写入。

## 模型与实验

最终主表包含 8 个模型：GRU、Transformer、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN 和 HSTA。每个主任务使用随机种子 `42`、`2025`、`3407`。

HSTA 主路径为：

```text
[B,30,3]
  -> 输入映射与位置编码
  -> Mamba 模块 x2
  -> Transition FFN
  -> 四头注意力
  -> Refinement FFN
  -> LayerNorm + 均值池化
  -> 分类器
```

实验配置与输出目录：

| 配置 | 内容 | 输出目录 |
|---|---|---|
| `tls40_s.yaml`、`quic40_s.yaml`、`tls60_s.yaml`、`quic60_s.yaml` | GRU、Transformer 主基线 | 对应 `results/*_s` |
| `hsta_flash.yaml` | HSTA 三种子、四个任务 | `results/hsta_flash` |
| `hsta_no_attention.yaml` | 无注意力消融 | `results/hsta_no_attention` |
| `hsta_flash_ablation.yaml` | 注意力位置消融 | `results/hsta_flash_ablation` |
| `sota_adapted.yaml` | 两个适配方法 | `results/sota_adapted` |
| `recent_journal_baselines.yaml` | 三个近期结构基线 | `results/recent_journal_baselines` |
| `base.yaml` | 公共参数模板，不直接运行 | 无 |

近期基线和 FlashAttention 的实验约定见 [docs/recent_journal_baselines_and_flashattention.md](docs/recent_journal_baselines_and_flashattention.md)。

## 环境与数据

Windows 检查环境和运行 CPU 测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

Mamba/CUDA 训练使用 WSL `Ubuntu-22.04` 和 `/opt/traffic-mamba-venv`。默认数据文件为：

```text
data/processed/datazoo_tls40_s_seq30.csv
data/processed/datazoo_quic40_s_seq30.csv
data/processed/datazoo_tls60_s_seq30.csv
data/processed/datazoo_quic60_s_seq30.csv
```

生成数据示例：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 40
```

`topk 60` 的 TLS/QUIC 任务使用同样命令，将参数改为 `60` 即可。

## 运行与验证

单个配置：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume
```

WSL 批量实验：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh main_all"
```

主表汇总、独立评估和效率测试：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\summarize_paper_main_results.py
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' evaluate.py --checkpoint results\hsta_flash\hsta_flash_tls40_s_seed42\best.pt --split test
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh efficiency"
```

测试命令：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
```

常用结果文件包括 `best.pt`、`latest.pt`、`history.csv`、`summary.csv`、`metrics.json` 和配置组下的 `all_results.csv`。
