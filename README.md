# HSTA-CM 流量识别

本项目在 CESNET-TLS22-S 和 CESNET-QUIC22-S 上进行 60 类开放集流量识别。每个数据集独立按训练时间窗口的流量数量选择 60 个已知应用，其余可用应用作为真实 unknown 候选。每条流只取前 30 个包的包长、方向和包间隔，模型输入为 `[B, 30, 3]`。

## 数据

文件名中的 `s` 表示 CESNET 的 S 源数据集，不表示 small 档次。最终数据文件为：

- `data/processed/datazoo_tls60_s_protocol.csv`
- `data/processed/datazoo_quic60_s_protocol.csv`

每个已知类别的训练、验证、测试上限为 `10000/2000/2000`。真实 unknown 的目标数量是同一 split 已知流量的 30%，合成噪声目标数量是 10%；不足时按实际可用量导出，不重复流量。数据按固定日期窗口划分，unknown 应用身份和噪声生成族在集合之间隔离。CSV 附带 report、audit 和 sampling manifest；`original_app` 等审计字段不作为模型输入。

数据导出和正式实验是长任务，可由外部放到后台运行。启动器会写入 `logs/formal_pipeline.status`，并在整条队列完成后创建 `logs/formal_pipeline.completed`；状态文件尚未出现时，不能据此判断任务已完成，也不能把中间结果称为正式论文结果。

## HSTA-CM

主模型使用 256 维、76 个 token：

1. **Mamba 时序分支**：原始包序列经过线性投影和两层残差 Mamba，输出 30 个 token。
2. **原始包卷积分支**：沿 30 个包位置使用三个依次堆叠的残差 `Conv1d` 块，卷积核为 `1/3/5`，输出 30 个 token。
3. **DFT 频域卷积分支**：沿包序列做 rFFT，保留实部和虚部得到 16 个频率 token，再沿频率轴使用独立的 `1/3/5` 残差 `Conv1d` 块。

三路来自同一份输入，属于不同的表示和归纳偏置，不能表述为三份独立采集信息。两条卷积分支参数独立，卷积轴分别是包位置和频率位置。`1/3/5` 是顺序残差块，不是三个并行分支。三路加入包位置、频率位置和分支类型编码，拼接后经过融合层、PyTorch FlashAttention、LayerNorm 和分类头。`HSTA-CM-open` 输出 61 类并训练 unknown；`HSTA-CM-closed` 输出 60 类，不使用 unknown 监督。

## 实验与运行

主比较包含 HSTA-CM open/closed 和五个统一 `[30,3]` 输入的适配基线：30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN。它们保留各自的建模思想，但不等同于原论文中的完整字节、音频、图或预训练管线。TrafficAudio 的内部 BiGRU 保留，不单独运行 GRU 或 Transformer。

- 主比较：`2 个数据集 × 7 个模型设置 × 3 个 seed = 42` 次训练。
- 消融：`no_conv`、`no_mamba`、`no_attention`，共 `2 × 3 × 3 = 18` 次训练。
- 效率：只测完整 HSTA-CM，推理 batch 为 `1/8/32`。

训练最多 100 轮，patience 为 15，按已知验证集 Macro-F1 调度和早停。目标有效优化器 batch 为 4096，验证和测试 batch 为 512；显存不足时使用微批次和梯度累积，并记录实际微批次。raw argmax 与 threshold rejection 分开评估，拒识阈值只用已知验证流量校准。

训练和 FlashAttention 使用 WSL Ubuntu-22.04 环境：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_formal_pipeline.sh"
```

数据已经导出并通过审计后，也可以单独运行：

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
bash scripts/run_wsl_experiments.sh all
```

正式流水线默认让数据导出在 Windows 原生进程执行，以避免 WSL `/mnt/e` 的文件 I/O 开销；训练仍在 WSL 中执行。导出 worker 默认使用 CPU 感知并行（最多 8 个），可以按磁盘吞吐调小：

```powershell
$env:DATAZOO_WORKERS = '4'
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && bash scripts/run_formal_pipeline.sh"
```

需要完全在 WSL 导出时设置 `DATA_EXPORT_RUNTIME=wsl`。GPU 不参与 H5 解码和 CSV 序列化，留给后续模型训练。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/raw/` | 本地 H5 和应用映射 |
| `data/processed/` | 两份正式 CSV 及审计文件 |
| `models/` | HSTA-CM、Mamba、FlashAttention 和五个基线 |
| `configs/` | 主比较和消融配置 |
| `train.py`、`evaluate.py` | 训练和评估入口 |
| `run_experiments.py` | 多模型、多数据集、多 seed 批量运行 |
| `scripts/` | 导出、审计、运行和结果汇总 |
| `results/`、`logs/` | 本地生成的结果、checkpoint 和日志 |
| `docs/` | 协议、架构、范围和复现说明 |

数据、结果、日志、checkpoint 和原始 H5 不提交 Git；代码、配置、测试和文档提交。论文文件放在仓库外的 `E:\AllProject\流量分析python项目\paper`。
