# MM-MLP-A-MLP

这是一个基于 PyTorch 的加密流量分类实验项目，用于比较 5 层基线模型、`Mamba -> Mamba -> MLP -> Attention -> MLP` 混合模型、注意力位置消融、LoRA 迁移、zero-shot 迁移和 full fine-tune 迁移。

Mamba 模块依赖官方 `mamba-ssm`，建议在 WSL/Linux CUDA 环境运行。普通数据检查、CSV 预处理和非 Mamba 脚本也可以在 Windows 的 Anaconda 环境中运行。

## Python 环境

当前 PyCharm 项目使用的解释器是 Anaconda 的 `mybase` 环境：

```powershell
D:\ProgramData\anaconda3\envs\mybase\python.exe
```

如果 PowerShell 没有初始化 conda，可以直接用解释器绝对路径：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume
```

如果已经打开 Anaconda Prompt 或 conda 已在 PATH 中：

```powershell
conda activate mybase
python run_experiments.py --config configs\tls40_s.yaml --resume
```

WSL 批处理脚本默认使用：

```bash
source /opt/traffic-mamba-venv/bin/activate
```

## 安装依赖

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

`mamba-ssm` 在 Windows 上通常不方便安装。需要跑 `mamba`、`hybrid`、`hybrid_lora` 时，优先使用 WSL/Linux CUDA 环境。

## 准备 DataZoo S CSV

默认导出 TLS/QUIC 的 top-40 和 top-60 类，每条 flow 取前 30 个包，每包特征为 `size`、`direction`、`delta_time`。

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 60
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 60
```

默认输出：

- `data/processed/datazoo_tls40_s_seq30.csv`
- `data/processed/datazoo_quic40_s_seq30.csv`
- `data/processed/datazoo_tls60_s_seq30.csv`
- `data/processed/datazoo_quic60_s_seq30.csv`

预处理默认限制：

- 初始化 train: `1000000`
- 初始化 validation known: `200000`
- 初始化 test known: `200000`
- 每类导出 train: `10000`
- 每类导出 validation: `2000`
- 每类导出 test: `2000`
- DataZoo batch size: `64`
- DataZoo workers: `0`

内存紧张时可以降低规模：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 40 --init-train-size 200000 --init-val-size 80000 --init-test-size 80000 --datazoo-batch-size 32 --datazoo-test-batch-size 32 --max-train-per-class 5000 --max-val-per-class 1000 --max-test-per-class 1000
```

常用预处理参数：

- `--dataset tls|quic`：选择 TLS 或 QUIC。
- `--size XS|S|M|L`：DataZoo 数据集规模。
- `--seq-len 30`：每条 flow 使用多少个包。
- `--topk 40`：自动扫描训练集并选出现次数最多的 top-k 类。
- `--classes ...`：手动指定类别，指定后不按 top-k 选择。
- `--out-csv path`：自定义输出 CSV。

## 统一实验入口

主入口是：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config <配置文件> --resume
```

`run_experiments.py` 现在同时支持普通训练、LoRA/full fine-tune 训练和 zero-shot 评估。配置中包含 `source_csv`、`target_csv`、`source_checkpoint` 的实验会自动按 zero-shot 处理。

常用参数：

- `--config configs/tls40_s.yaml`：指定实验配置。
- `--resume`：默认行为；已完成且有 `summary.csv`、`best.pt` 的训练实验会跳过，未完成实验会从 `latest.pt` 继续。
- `--no-resume`：关闭续训和跳过逻辑。
- `--force`：即使已有结果也重新跑。谨慎使用。
- `--extend`：已经完成的实验也从 `latest.pt` 继续跑到当前配置的 `epochs`。
- `--only exp_name ...`：只跑指定实验名，可以一次指定多个。

示例：

```powershell
# 跑完整 TLS40 配置
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume

# 只跑一个实验
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --only hybrid_mm_mlp_a_mlp_tls40_s_seed42

# 已提高 epochs 后继续已完成实验
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume --extend

# 从头重跑某个实验
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --force --only mlp_5layer_tls40_s
```

## 配置文件说明

| 配置 | 作用 | 输出目录 |
| --- | --- | --- |
| `configs/tls40_s.yaml` | TLS top-40，MLP/CNN/LSTM/GRU/Transformer/Mamba/Hybrid/消融共 10 个实验 | `results/tls40_s` |
| `configs/quic40_s.yaml` | QUIC top-40，模型集合同 TLS40 | `results/quic40_s` |
| `configs/tls60_s.yaml` | TLS top-60，GRU/Transformer/Mamba/Hybrid/消融，以及 Transformer/Mamba/Hybrid 的多 seed 主实验 | `results/tls60_s` |
| `configs/quic60_s.yaml` | QUIC top-60，GRU/Transformer/Mamba/Hybrid/消融，以及 Transformer/Mamba/Hybrid 的多 seed 主实验 | `results/quic60_s` |
| `configs/transfer_s.yaml` | top-40/top-60 的 LoRA、zero-shot、full fine-tune 迁移合集 | `results/transfer_s` |
| `configs/base.yaml` | 公共超参数模板，不是批量实验配置 | 无 |

## 推荐运行顺序

先跑主模型，再跑迁移。LoRA 和 full fine-tune 都依赖源域 Hybrid 的 `best.pt`。

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\quic40_s.yaml --resume
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only hybrid_lora_tls_to_quic40_s hybrid_lora_quic_to_tls40_s
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only zero_shot_tls_to_quic40_s zero_shot_quic_to_tls40_s
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only full_ft_tls_to_quic40_s full_ft_quic_to_tls40_s

& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls60_s.yaml --resume
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\quic60_s.yaml --resume
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only hybrid_lora_tls_to_quic60_s hybrid_lora_quic_to_tls60_s
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only zero_shot_tls_to_quic60_s zero_shot_quic_to_tls60_s
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume --only full_ft_tls_to_quic60_s full_ft_quic_to_tls60_s
```

一次跑完所有迁移实验：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\transfer_s.yaml --resume
```

LoRA 迁移说明：

- `hybrid_lora_tls_to_quic*_s`：加载 TLS Hybrid 的 `best.pt`，重置分类头，在 QUIC 上只训练 LoRA 和 head。
- `hybrid_lora_quic_to_tls*_s`：加载 QUIC Hybrid 的 `best.pt`，重置分类头，在 TLS 上只训练 LoRA 和 head。
- 随机 backbone 的 LoRA 已禁用；每个 LoRA 实验必须定义 `pretrained_path`。

Zero-shot 迁移说明：

- 使用源域 checkpoint 的类别空间。
- 使用源域训练集拟合出的 scaler 标准化目标域测试集。
- 输出 `full_accuracy`、`covered_accuracy`、`covered_macro_f1` 等指标。
- `zero_shot_transfer.py` 已删除；zero-shot 逻辑已合并进 `run_experiments.py`。

## WSL 批量运行

WSL 脚本入口：

```bash
bash scripts/run_wsl_experiments.sh <mode>
```

从 PowerShell 调用时示例：

```powershell
wsl -d Ubuntu-22.04 bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh extend_and_transfer"
```

可用 mode：

| mode | 执行内容 |
| --- | --- |
| `tls` | TLS40 主实验 |
| `quic` | QUIC40 主实验 |
| `tls60` | TLS60 主实验 |
| `quic60` | QUIC60 主实验 |
| `ablation60` | TLS60/QUIC60 的 60 类消融实验 |
| `seed40` | TLS40/QUIC40 中 Transformer、Mamba、Hybrid 的 seed2025/seed3407 补充实验 |
| `seed60` | TLS60/QUIC60 中 Transformer、Mamba、Hybrid 的 seed2025/seed3407 补充实验 |
| `stack40` | TLS40/QUIC40 的 Hybrid 2 Block 和 4 Block 三随机种子堆叠实验 |
| `stack60` | TLS60/QUIC60 的 Hybrid 2 Block 和 4 Block 三随机种子堆叠实验 |
| `stack_all` | TLS40/QUIC40/TLS60/QUIC60 的 Hybrid 2 Block 和 4 Block 三随机种子堆叠实验 |
| `stack_all_3seed` | `stack_all` 的同内容别名，日志单独写入 `wsl_stack_all_3seed_*` |
| `efficiency` | 对已有 `best.pt` 做 FLOPs 和推理时间实验，输出 `results/efficiency_benchmark` |
| `efficiency_quick` | 小迭代快速检查版，输出 `results/efficiency_benchmark_quick` |
| `transfer40` | top-40 LoRA 迁移 |
| `transfer60` | top-60 LoRA 迁移 |
| `zero40` | top-40 zero-shot 迁移 |
| `zero60` | top-60 zero-shot 迁移 |
| `fullft40` | top-40 full fine-tune 迁移 |
| `fullft60` | top-60 full fine-tune 迁移 |
| `all` | TLS40 -> QUIC40 -> top-40 LoRA |
| `all60` | TLS60 -> QUIC60 -> top-60 LoRA |
| `readme_all` | TLS40/QUIC40/LoRA40/TLS60/QUIC60/LoRA60 |
| `transfer_extra` | zero-shot40 -> fullft40 -> zero-shot60 -> fullft60 |
| `extend_all` | 扩展 TLS40/QUIC40/LoRA40/TLS60/QUIC60/LoRA60 |
| `extend_and_transfer` | 扩展已有主实验和 LoRA，再跑 zero-shot/full fine-tune |
| `quic40_then_all60` | QUIC40 -> LoRA40 -> TLS60 -> QUIC60 -> LoRA60 |

WSL 脚本会写入：

- `logs/wsl_<mode>_latest.log`
- `logs/wsl_<mode>_status.txt`
- `logs/wsl_<mode>_windows.pid`

监控当前任务：

```powershell
Get-Content logs\wsl_extend_and_transfer_status.txt
Get-Content logs\wsl_extend_and_transfer_latest.log -Tail 80 -Wait
Get-Process | Where-Object { $_.ProcessName -like '*wsl*' -or $_.ProcessName -like '*python*' }
```

## FLOPs 与推理时间实验

独立脚本为 `benchmark_efficiency.py`，默认扫描 TLS40、QUIC40、TLS60、QUIC60 四个配置中已经存在的所有模型 `best.pt`。缺失 checkpoint 的实验会跳过，结果统一写入 `results/efficiency_benchmark`。

```powershell
wsl -d Ubuntu-22.04 bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh efficiency"
```

只测指定实验：

```powershell
wsl -d Ubuntu-22.04 bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh efficiency --only hybrid_mm_mlp_a_mlp_tls40_s_seed42 transformer_5layer_tls40_s_seed42"
```

常用参数：

- `--batch-sizes 1 32 512`：分别测单条、常用 batch 和大 batch 推理。
- `--repeats 5`：独立重复 benchmark 次数，主表默认写 5 次重复的均值。
- `--warmup 20 --iterations 100`：每次重复内的预热次数和正式计时次数。
- `--checkpoint-name best.pt|latest.pt`：默认测最佳 checkpoint。
- `--cpu` 或 `--device cuda:0`：指定 CPU/GPU。
- `--no-amp`：关闭 CUDA AMP 计时。

核心指标：

- Parameters：`total_params`、`parameters_m`。
- FLOPs / MACs：`gflops_per_sample`、`gmacs_per_sample`。
- Inference latency：`latency_ms_mean`、`latency_ms_p95`、`per_sample_latency_ms`。
- Throughput：`throughput_samples_per_s`。
- GPU memory：`gpu_memory_peak_allocated_mb`、`gpu_memory_peak_reserved_mb`、`gpu_memory_peak_delta_mb`。

输出文件：

- `results/efficiency_benchmark/benchmark_results.csv`：逐实验、逐 batch 的多次重复均值结果。
- `results/efficiency_benchmark/benchmark_repeats.csv`：每次重复的原始结果，用于查看波动。
- `results/efficiency_benchmark/summary.csv`：全模型效率简表。
- `results/efficiency_benchmark/core_model_efficiency.csv`：Transformer、Mamba、Hybrid seed42 在四个任务上的核心对比表。
- `results/efficiency_benchmark/benchmark_results.json`：包含参数、跳过项和 FLOPs 分项。
- `results/efficiency_benchmark/README.md`：本次 benchmark 的设置说明。

口径说明：FLOPs 采用 `1 multiply-add = 2 FLOPs`，MACs 按 `FLOPs / 2` 输出。计时只包含模型前向推理，不包含 CSV 读取、标准化、DataLoader 或后处理。Latency、throughput、GPU memory 在 `summary.csv` 中默认是 5 次独立 benchmark 的均值，同时保留跨重复的标准差和 CV。GPU memory 在每个模型、每个 batch size、每次重复进入推理 warmup 前重置 CUDA peak memory stats。`LayerNorm`、`GELU`、`Dropout`、残差加法和 reshape/indexing 未计入 FLOPs；Mamba selective scan 因为核心 CUDA kernel 对 Python hook 不透明，使用解析近似估算。

## 结果文件

每个实验目录包含：

- `best.pt`：验证集指标最好的 checkpoint。
- `latest.pt`：最近一个 epoch 的可续训 checkpoint。
- `history.csv`：逐 epoch 训练/验证指标。
- `summary.csv`：该实验最终测试指标。
- `metrics.json`：混淆矩阵、classification report、配置和更多元信息。

每个配置输出目录下还有：

- `all_results.csv`：该配置内所有实验的汇总结果。

迁移实验统一放在 `results/transfer_s`，包括 LoRA、zero-shot 和 full fine-tune 的 40/60 类所有实验目录。

60 类主模型的多 seed 命名规则：

- 原始 seed 42 结果统一命名为 `*_seed42`。
- 新增补充 seed 为 `seed2025` 和 `seed3407`。
- 涉及模型为 Transformer、Mamba 和 `Mamba -> Mamba -> MLP -> Attention -> MLP` Hybrid。

只跑 60 类多 seed 补充实验：

```powershell
wsl -d Ubuntu-22.04 bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && bash scripts/run_wsl_experiments.sh seed60"
```

查看汇总：

```powershell
Import-Csv results\tls40_s\all_results.csv |
  Select-Object exp_name,model,test_accuracy,test_macro_f1,trainable_params,seconds |
  Format-Table -AutoSize
```

查看当前实验最近几个 epoch：

```powershell
Import-Csv results\tls40_s\gru_5layer_tls40_s\history.csv |
  Select-Object -Last 10 |
  Format-Table epoch,train_loss,val_accuracy,val_macro_f1,best_epoch,bad_epochs,stop_reason -AutoSize
```

## 单独评估 checkpoint

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' evaluate.py --checkpoint results\tls40_s\hybrid_mm_mlp_a_mlp_tls40_s_seed42\best.pt --split test
```

写出 JSON：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' evaluate.py --checkpoint results\tls40_s\hybrid_mm_mlp_a_mlp_tls40_s_seed42\best.pt --split test --out results\tls40_s\hybrid_eval.json
```

## 辅助脚本

预处理会在 `data/processed/*.report.json` 中写入 `class_summary` 和 `class_count_summary`：

- `model_label_id`：训练和预测时模型使用的类别编号。
- `datazoo_label`：DataZoo 原始服务编号。
- `traffic_name`：`servicemap.csv` 中对应的真实流量服务名。
- `flow_count` / `packet_row_count`：每个类型的 flow 数和 CSV 包行数。

只补充已有 CSV 的 report，不重新导出数据：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --enrich-existing-reports --project-root .
```

只补充某一个数据集：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --enrich-existing-reports --project-root . --report-csv data\processed\datazoo_tls60_s_seq30.csv
```

打包结果但排除 `.pt` 和 `.csv`：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' zip_without_pt_csv.py --source results --output results\results_without_pt_csv.zip
```

默认会把 `data/processed/*.report.json` 一起打包进去，里面包含数据集类别数量和标签服务名映射。若不需要这些 report：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' zip_without_pt_csv.py --source results --output results\results_without_pt_csv.zip --no-include-data-reports
```

## 常见注意事项

- `--resume` 是默认行为，普通训练实验需要同时存在 `summary.csv` 和 `best.pt` 才会被认为已完成。
- zero-shot 没有训练 checkpoint，完成判断只看 `summary.csv`。
- `--extend` 适合提高 `epochs` 后继续训练；默认会重置 optimizer 和 patience。
- `--force` 会重新跑实验并覆盖同名输出，使用前确认不需要保留旧结果。
- LoRA/full fine-tune 前必须先跑完源域 Hybrid 主模型。
- Windows PowerShell 中的 `python.exe` 可能是 Microsoft Store 占位符；本项目推荐直接使用 `D:\ProgramData\anaconda3\envs\mybase\python.exe`。
