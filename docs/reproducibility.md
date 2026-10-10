# 复现说明

## 环境

Windows 检查和依赖安装使用 `D:\ProgramData\anaconda3\envs\mybase\python.exe`。Mamba、CUDA 和 FlashAttention 训练使用 `Ubuntu-22.04` 的 `/opt/traffic-mamba-venv`，不要使用其他 WSL 发行版。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

环境应提供当前 `mamba_ssm`、CUDA 和 PyTorch FlashAttention 后端。HSTA-CM-DFT 的注意力配置为 `attention_backend: flash`，不接受 CPU、数学实现或 memory-efficient 回退。

## 数据准备

使用现有 CESNET-TLS22-S 和 CESNET-QUIC22-S 文件。官方 PPI 固定为前 30 个包的 `IPT、DIR、SIZE` 三通道，短流由 DataZoo 补零。预处理为 100 个已知类别，并将其余全部应用形成 unknown 候选池；在折叠标签前按应用身份划分训练支持、验证留出和测试留出。每个日期划分中每类最多保留 10,000 条完整流；不足时保留全部。CSV 同时写出 `original_app`、`source_group` 和 `noise_family`，这些字段仅用于审计和分层统计，不进入模型。输出文件名不再附加序列长度后缀，但输入长度仍由 PPI 协议固定为 30。

DataZoo 原生提供训练、验证和测试索引及 DataLoader。项目 CSV 只用于固定 unknown 应用清单、时间均衡采样和逐流来源审计；它不是完整 S 数据集的替代品。

重新导出协议 CSV（默认使用 Top-100 以外的完整 unknown 候选池）：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --out-csv data/processed/datazoo_tls100_s_protocol.csv
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --out-csv data/processed/datazoo_quic100_s_protocol.csv
```

从协议 CSV 创建小规模时间均衡数据集：

```bash
python scripts/sample_temporal_dataset.py \
  --input-csv data/processed/datazoo_tls100_s_protocol.csv \
  --output-csv data/processed/datazoo_tls100_s_protocol_small_sampled.csv \
  --dataset tls --profile small --seed 599
```

采样完成后运行 `scripts/audit_open_set_dataset.py`。只有审计通过的 CSV 才能用于正式开放集实验；旧 CSV 因缺少 unknown 来源元数据，只能作为历史流程文件。

每类训练/验证/测试上限为：`small=100/20/20`、`medium=1000/200/200`、`paper=10000/1000/2000`。采样在已有时间划分内进行，以完整流为单位，不把同一流拆到不同集合。这里的 profile 只改变数据集规模，不改变模型参数。

## 运行

在 WSL 中执行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

首次低成本流程检查：

```bash
bash scripts/run_wsl_experiments.sh small_tls
bash scripts/run_wsl_experiments.sh small_quic
```

`main` 使用 `configs/compact_s.yaml`，其中 HSTA-CM-DFT 是主模型，HSTA-CM-no-DFT 是 DFT 组件对照；`ablation` 使用 `configs/hsta_cm_ablation_s.yaml`。训练采用配置文件中的 AdamW、验证集 Macro-F1 早停和最优检查点；实际种子、模型配置、类别映射、标准化参数、FlashAttention 后端和开放集指标会写入检查点目录。

## 结果与版本管理

结果、日志、数据和检查点存放在被 Git 忽略的目录中。禁止提交原始 H5、检查点、凭据或本地环境。主结果应报告已知分类指标、未知拒识指标、误拒率、参数量和效率指标；HSTA-CM-DFT-open 的三个种子报告均值和标准差。留出应用和独立噪声生成族必须保持测试专用。
