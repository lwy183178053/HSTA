# 复现说明

## 环境

Windows 检查：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

训练、Mamba 和 FlashAttention 使用 WSL Ubuntu-22.04 与 `/opt/traffic-mamba-venv`：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## 启动

当前五个基线的 30 次训练继续执行；新主模型、消融和效率实验暂不启动。以下命令供之后复现，不应在基线运行时启动完整队列。

Windows 导出入口默认只生成和审计 TLS/QUIC 数据，不自动训练：

```powershell
& .\scripts\run_formal_pipeline.ps1
```

数据已经存在并通过审计后，可单独运行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

上述 Bash 命令应在 Ubuntu-22.04 中运行，工作目录为 `/mnt/e/AllProject/流量分析python项目/HSTA`。需要完整训练时可显式使用 Windows 入口的 `-RunTraining` 参数；这会启动主比较、消融和效率等后续任务。

主配置为 `configs/compact_s.yaml`，结果目录为 `results/formal60`；消融配置为 `configs/hsta_cm_ablation_s.yaml`，结果目录为 `results/hsta_cm_ablation_formal60`；效率结果写入 `results/efficiency_benchmark`。配置文件名中的 `s` 表示 CESNET S 数据集，不表示小规模数据。

## 复现检查

运行 pytest、Python 编译检查和 CUDA smoke test，确认 Mamba/GNN/DFT-CNN 完整 HSTA-CM 产生 76 个 token，open/closed 分别输出 61/60 类，并实际使用 PyTorch FlashAttention。分别关闭 `no_mamba`、`no_gnn`、`no_dft` 时确认只移除目标分支。数据审计确认日期、类别映射、flow ID、unknown 应用身份和噪声族隔离。代码验收和 smoke test 不产生准确率结论。

结果目录保留配置、seed、类别映射、scaler、阈值、训练历史、checkpoint，以及 raw/threshold 和来源分层指标。Git 提交代码、配置、测试、文档及轻量结果（CSV/JSON/YAML/Markdown），用于备份数值指标、训练历史和运行配置。数据、原始 H5、日志、checkpoint、大体积预测明细及二进制产物保持忽略。结果快照应注明记录时间、运行范围和完成状态；本次新架构尚未训练，基线的部分结果不能作为完整三 seed 比较。论文和图表存放在仓库外的 `E:\AllProject\流量分析python项目\paper`。

完整流水线启动后可查看 `logs/formal_pipeline.status` 和 `logs/formal_pipeline.completed`；单独启动的基线队列应查看其对应日志与完成标记。最终汇总需逐一确认预期运行全部成功、模型结构和数据版本一致、三个 seed 结果完整，再报告 `mean ± std`。状态文件尚未出现或只存在部分指标文件，都不能据此判断队列完成。
