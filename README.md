# HSTA Encrypted Traffic Classification

基于 PyTorch 的加密 QUIC/TLS 流量分类实验项目。项目内容与论文修改版 10 对齐，统一使用每条 flow 前 30 个包的三维侧信道特征：`size`、`direction`、`delta_time`。

## 论文范围

最终主结果包含 8 个模型，在 QUIC-40、QUIC-60、TLS-40、TLS-60 四个闭集任务上使用随机种子 `42`、`2025`、`3407`：

| 类别 | 模型 |
| --- | --- |
| 主模型与基础对比 | GRU、Transformer、HSTA |
| 适配 SOTA | `30pktTCNET-adapted`、`NetMamba-adapted` |
| 近期论文结构 | SRViT、TrafficAudio、BPF-GNN |

HSTA 的固定主结构是：

```text
[B, 30, 3]
  -> Input Projection + Positional Encoding
  -> Mamba Block x2
  -> Transition FFN (128 -> 512 -> 128)
  -> 4-head FlashAttention
  -> Refinement FFN (128 -> 512 -> 128)
  -> Mean Pooling
  -> Linear Classifier
```

注意力位置消融包含 `No Attention`、`Front Attention`、`Middle Attention` 和完整 HSTA。FlashAttention 是 PyTorch SDPA 的严格 CUDA FP16/BF16 后端，用于实现效率，不改变论文中的注意力定义。

## 项目结构

```text
data/                         数据读取、划分、DataZoo 预处理
models/
  hsta.py                     HSTA 及注意力位置消融结构
  mamba_model.py              Mamba Block 与 NetMamba-adapted 主干
  gru.py                      GRU 基线
  transformer.py              Transformer 基线与注意力/FFN 模块
  adapted_sota.py             30pktTCNET-adapted、NetMamba-adapted
  recent_journal_baselines.py SRViT、TrafficAudio、BPF-GNN
configs/                      最终论文实验配置
scripts/
  run_wsl_experiments.sh      WSL/CUDA 批量入口
  summarize_paper_main_results.py 主表汇总
tests/                        模型、配置、效率和主表测试
docs/                         近期基线与 FlashAttention 说明
paper/                        论文归档目录，仅保存，不参与代码运行
train.py                      单实验训练与断点续训
run_experiments.py             配置文件批量训练入口
evaluate.py                    checkpoint 独立评估
benchmark_efficiency.py       FLOPs、延迟、吞吐和显存测试
```

## 环境

Windows 检查、预处理和 CPU 测试使用项目 Anaconda 解释器：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

Mamba/CUDA 训练使用 WSL `Ubuntu-22.04` 和 `/opt/traffic-mamba-venv`：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python -c 'import torch, mamba_ssm; print(torch.__version__, torch.cuda.is_available())'"
```

## 数据准备

项目默认读取以下四个 CSV：

```text
data/processed/datazoo_tls40_s_seq30.csv
data/processed/datazoo_quic40_s_seq30.csv
data/processed/datazoo_tls60_s_seq30.csv
data/processed/datazoo_quic60_s_seq30.csv
```

从 DataZoo 生成数据：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 60
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 60
```

预处理只负责生成统一的 `[flow, packet, feature]` 输入。训练和测试使用按 flow 且按时间隔离的划分，避免同一 flow 的 packet 泄漏到不同 split。

## 实验配置

| 配置 | 内容 | 输出目录 |
| --- | --- | --- |
| `configs/tls40_s.yaml` | TLS-40 的 GRU、Transformer 三 seed | `results/tls40_s` |
| `configs/quic40_s.yaml` | QUIC-40 的 GRU、Transformer 三 seed | `results/quic40_s` |
| `configs/tls60_s.yaml` | TLS-60 的 GRU、Transformer 三 seed | `results/tls60_s` |
| `configs/quic60_s.yaml` | QUIC-60 的 GRU、Transformer 三 seed | `results/quic60_s` |
| `configs/hsta_flash.yaml` | HSTA 三 seed、四任务 | `results/hsta_flash` |
| `configs/hsta_no_attention.yaml` | HSTA No Attention 三 seed、四任务 | `results/hsta_no_attention` |
| `configs/hsta_flash_ablation.yaml` | Front/Middle Attention 消融 | `results/hsta_flash_ablation` |
| `configs/sota_adapted.yaml` | 两个适配 SOTA、三 seed、四任务 | `results/sota_adapted` |
| `configs/recent_journal_baselines.yaml` | SRViT、TrafficAudio、BPF-GNN | `results/recent_journal_baselines` |
| `configs/base.yaml` | 公共超参数模板 | 不直接运行 |

## 训练

单个配置在 Windows 上运行：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume
```

常用选项：`--resume` 跳过已完成实验并续训未完成实验；`--no-resume` 关闭断点续训；`--force` 覆盖同名结果；`--extend` 延长训练；`--only NAME` 只运行指定实验。

WSL/CUDA 批量入口：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh main_all"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh sota_all"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh recent_all"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh hsta_flash_all"
```

可用 mode：`tls40`、`quic40`、`tls60`、`quic60`、`main_all`、`recent_all`、`sota_all`、`ablation_all`、`hsta_flash_all`、`efficiency`。

## 结果与评估

每个实验目录包含 `best.pt`、`latest.pt`、`history.csv`、`summary.csv` 和 `metrics.json`。各配置根目录的 `all_results.csv` 保存该配置汇总结果。

生成论文八模型主表：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\summarize_paper_main_results.py
```

独立评估 checkpoint：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' evaluate.py --checkpoint results\hsta_flash\hsta_flash_tls40_s_seed42\best.pt --split test
```

效率测试只扫描配置中已存在的 `best.pt`，结果写入 `results/efficiency_benchmark`：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh efficiency"
```

效率输出包括参数量、单样本 GFLOPs、MACs、延迟、吞吐和 CUDA 峰值显存。Mamba selective scan 使用解析估计，并在结果中明确标记。

## 论文归档

`paper/` 只保存论文原稿、投稿包和图稿，不作为训练代码输入，也不由项目脚本写入。

测试：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
```
