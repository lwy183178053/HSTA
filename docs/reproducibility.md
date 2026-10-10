# 复现说明

## 环境

Windows 检查和依赖安装使用项目解释器：

```powershell
& 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\\check_environment.ps1
```

训练、Mamba 和 CUDA FlashAttention 使用 `Ubuntu-22.04` 与 `/opt/traffic-mamba-venv`：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

正式配置要求 PyTorch FlashAttention 后端；环境缺少 CUDA 或后端时应先修复环境，不把 CPU 数学回退结果当作正式结果。

## 数据

使用项目中已审计的 60 类 small CSV，不重新下载 CESNET 原始 H5：

```text
data/processed/datazoo_tls60_s_protocol_small_sampled.csv
data/processed/datazoo_quic60_s_protocol_small_sampled.csv
```

对应的 `report.json`、`audit.json` 和 `sampling_manifest.json` 记录类别清单、时间划分、实际样本数、unknown 应用和噪声族。训练/验证/测试按完整 flow 分离；scaler 仅由训练数据拟合。若需重建缓存，必须使用与清单相同的类别映射、时间窗口和 seed 599，并重新运行数据审计。

small 每类目标数量为训练 100、验证 20、测试 20；不足时保留全部。TLS 验证集中部分类别样本不足，复现报告须同时保留每类支持数。

## 运行

在 WSL 项目根目录执行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

`main` 读取 `configs/compact_s.yaml`，运行 TLS60/QUIC60 的 HSTA-CM-open、HSTA-CM-closed 和五个基线；`ablation` 读取 `configs/hsta_cm_ablation_s.yaml`，运行三个组件消融。两个入口均从空的结果目录启动，不使用旧 checkpoint。效率入口只测 batch size `1、8、32`。

训练上限为 100 轮，验证集已知 Macro-F1 连续 15 轮没有提升即早停。每个目录写入 `config.yaml`、`history.csv`、最佳和最近检查点、`summary.csv`、`metrics.json` 以及逐样本预测。`metrics.json` 同时包含 raw argmax 和 threshold rejection；阈值只由已知验证流量校准。

## 验证

运行前执行：

```powershell
& 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' -m pytest -q
& 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' -m compileall -q models data scripts train.py run_experiments.py evaluate.py
```

并确认两个数据审计报告均显示 60 个已知类、unknown 来源隔离、噪声族互斥和无 flow 交集。CUDA smoke test 应验证 HSTA-CM-open 输入 `(2,30,3)` 输出 `(2,61)`，closed 输出 `(2,60)`。结果汇总：

```bash
python scripts/summarize_compact_results.py
```

## 版本和归档

代码、配置和文档由 Git 保存；`data/`、`results/`、`logs/`、检查点和原始流量保持忽略。提交前运行 `git diff --check`，确认提交中没有本地数据、凭据或环境文件。论文只引用通过审计且保存了配置、seed、类别映射、scaler、阈值及来源分层指标的运行。
