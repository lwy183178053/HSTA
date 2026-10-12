# 复现说明

## 环境

Windows 检查使用项目 Anaconda 环境：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

训练、Mamba 和 FlashAttention 在 WSL `Ubuntu-22.04` 与 `/opt/traffic-mamba-venv` 中运行：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## 新一轮训练

旧配置的五基线队列已停止，旧结果移至仓库外归档目录；当前 `results/formal60` 为空。新一轮使用容量匹配配置，从第 1 轮开始，不复用旧 checkpoint 或历史。

新配置下主比较使用 `configs/compact_s.yaml`，包含 HSTA-CM-open/closed 和五个适配基线；消融使用 `configs/hsta_cm_ablation_s.yaml`。每个主比较模型和消融模型在 TLS、QUIC 上分别运行 seeds `599/5009/813`。完整效率实验使用推理 batch `1/8/32`。

数据已存在并通过审计后，从 PowerShell 启动各组：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_wsl_experiments.sh main"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_wsl_experiments.sh ablation"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_wsl_experiments.sh efficiency"
```

完整正式设置为 42 个主比较运行、18 个分支消融运行，以及两个数据集各自 batch `1/8/32` 的效率测量。运行数不等于模型数量。

## 数值精度

HSTA-CM 的 Mamba selective block 必须在 autocast 外以 FP32 执行，外围模型仍可使用 AMP，以保留 FlashAttention 等算子的混合精度加速。NetMamba 全模型必须关闭 AMP。其余对照使用 AMP。记录每次运行实际精度模式；任何改变都不得与不同模式的旧结果拼在一起汇总。

## 完成判据

运行前执行数据审计，确认类别映射、日期划分、flow ID 无交集、unknown 来源隔离、噪声族隔离及数量。运行时确认实际参数量和 AMP 状态被写入结果，NetMamba 和 HSTA selective Mamba 的损失保持有限，FlashAttention 后端按预期启用。

最终结果需包含所有模型、两个数据集和三个 seed 的成功运行，并对 raw argmax、threshold rejection 及 unknown 来源分层指标分别汇总。只完成部分 seed 或模型的结果必须标为 partial，不得作为正式完整比较。报告 `mean ± std` 前先确认每个运行采用相同的新配置和数据版本。

轻量指标、训练历史、运行配置和说明可作为结果快照提交。运行中快照需明确记录未完成状态。原始数据、日志、checkpoint、预测明细和二进制实验产物保留在本机；论文和图表存放在仓库外的 `E:\AllProject\流量分析python项目\paper`。
