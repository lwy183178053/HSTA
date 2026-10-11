# 复现说明

## 环境

Windows 检查：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

训练、Mamba 和 FlashAttention 使用 WSL Ubuntu-22.04 与 `/opt/traffic-mamba-venv`：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## 启动

完整队列会依次执行验收、TLS/QUIC 数据导出与审计、主比较、消融、效率和汇总；脚本本身前台执行，可由外部放到后台：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_formal_pipeline.sh"
```

数据已经存在并通过审计后，可单独运行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

主配置为 `configs/compact_s.yaml`，结果目录为 `results/formal60`；消融配置为 `configs/hsta_cm_ablation_s.yaml`，结果目录为 `results/hsta_cm_ablation_formal60`；效率结果写入 `results/efficiency_benchmark`。配置文件名中的 `s` 表示 CESNET S 数据集，不表示小规模数据。

## 复现检查

运行 pytest、Python 编译检查和 CUDA smoke test，确认完整 HSTA-CM 产生 76 个 token，open/closed 分别输出 61/60 类，并实际使用 PyTorch FlashAttention。数据审计确认日期、类别映射、flow ID、unknown 应用身份和噪声族隔离。

结果目录保留配置、seed、类别映射、scaler、阈值、训练历史、checkpoint，以及 raw/threshold 和来源分层指标。数据、原始 H5、日志、结果和 checkpoint 均为本地产物，不提交 Git；代码、配置、测试和文档提交。论文和图表存放在仓库外的 `E:\AllProject\流量分析python项目\paper`。

实验队列启动后可查看 `logs/formal_pipeline.status`；只有出现 `logs/formal_pipeline.completed` 后，才汇总三 seed 的 `mean ± std` 并用于论文。状态文件尚未出现时，先确认启动器是否成功运行。
