# 复现说明

## 环境

Windows 检查和依赖安装使用 `D:\ProgramData\anaconda3\envs\mybase\python.exe`。Mamba、CUDA 和 FlashAttention 训练使用 `Ubuntu-22.04` 的 `/opt/traffic-mamba-venv`，不要使用其他 WSL 发行版。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

环境应提供当前 `mamba_ssm`、CUDA 和 PyTorch FlashAttention 后端。HSTA-CM 的注意力配置为 `attention_backend: flash`，不接受 CPU、数学实现或 memory-efficient 回退。

## 数据准备

使用现有 CESNET-TLS22-S 和 CESNET-QUIC22-S 文件。预处理为 100 个已知类别，每个日期划分中每类最多保留 10,000 条完整流；不足时保留全部。预处理同时写出流级 `source`、类别和日期划分，并加入配置的未知应用与合成噪声。

从完整 S CSV 创建小规模时间均衡数据集：

```bash
python scripts/sample_temporal_dataset.py \
  --input-csv data/processed/datazoo_tls100_s_seq30.csv \
  --output-csv data/processed/datazoo_tls100_s_seq30_tiny.csv \
  --dataset tls --profile tiny --seed 599
```

每类训练/验证/测试上限为：`tiny=100/20/20`、`small=500/100/100`、`medium=1000/200/200`、`paper=10000/1000/2000`。采样在已有时间划分内进行，以完整流为单位，不把同一流拆到不同集合。这里的 profile 只改变数据集规模，不改变模型参数。

## 运行

在 WSL 中执行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

首次低成本流程检查：

```bash
bash scripts/run_wsl_experiments.sh quick_tls
bash scripts/run_wsl_experiments.sh quick_quic
```

`main` 使用 `configs/compact_s.yaml`，`ablation` 使用 `configs/hsta_cm_ablation_s.yaml`。训练采用配置文件中的 AdamW、验证集 Macro-F1 早停和最优检查点；实际种子、模型配置、类别映射、标准化参数、FlashAttention 后端和开放集指标会写入检查点目录。

## 结果与版本管理

结果、日志、数据和检查点存放在被 Git 忽略的目录中。禁止提交原始 H5、检查点、凭据或本地环境。主结果应报告已知分类指标、未知拒识指标、误拒率、参数量和效率指标；HSTA-CM-open 的三个种子报告均值和标准差。留出应用和独立噪声生成族必须保持测试专用。
