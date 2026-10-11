# HSTA-CM：CESNET 加密流量开放集识别

本项目实现 HSTA-CM 的 40 类开放集实验。模型统一接收 CESNET-TLS22-S 或 CESNET-QUIC22-S 的前 30 个数据包，每个包包含包长、方向和包间隔三个特征，输入形状为 `[30, 3]`。每个数据集固定 40 个已知类别；开放模型另有 `unknown` 类，因此输出 41 类。

## 当前实验

- **HSTA-CM-open**：三层残差 `Conv1d`、两层残差 Mamba、融合全连接、位置编码、PyTorch FlashAttention、LayerNorm 和分类头；TLS 采用结构筛选胜出的 DFT 三路配置，QUIC 采用胜出的双路多尺度配置；训练 unknown 支持流量，输出 41 类。
- **HSTA-CM-closed**：同一结构但只训练 40 个已知类，输出 40 类；测试时用已知验证流量校准拒识阈值。
- **组件消融**：`no_conv-open`、`no_mamba-open`、`no_attention-open`，保持 256 维、数据划分、unknown 训练规则和随机种子不变。
- **五个适配基线**：30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN。它们均使用闭集 40 类训练，不使用 unknown 监督；TrafficAudio 内部的 BiGRU 属于该模型，不单列 GRU 或 Transformer 对照。

每个数据集的正式主比较运行 HSTA-CM-open、HSTA-CM-closed 和五个基线，共 7 个运行；消融实验单独运行。结构筛选保存在 `results/hsta_cm_structure_s`，用于确定两个数据集的主配置。数据统一提供 `small=200/40/40`、`medium=2000/400/400`、`large=20000/4000/4000` 三档（训练/验证/测试每类上限），随机种子为 `599`，所有训练从第 1 轮开始，最多 100 轮，验证集已知类别 Macro-F1 连续 15 轮不提升时早停。

## 数据

项目保留已经审计的 40 类协议数据和三档采样缓存：

```text
data/processed/datazoo_tls40_s_protocol_small.csv
data/processed/datazoo_quic40_s_protocol_small.csv
data/processed/datazoo_tls40_s_protocol_medium.csv
data/processed/datazoo_quic40_s_protocol_medium.csv
data/processed/datazoo_tls40_s_protocol_large.csv
data/processed/datazoo_quic40_s_protocol_large.csv
```

每套数据同时有 `report.json`、`audit.json` 和 `sampling_manifest.json`。真实 unknown 按应用来源均衡，目标为该 split 已知流量的 50%；合成噪声目标为 10%，且训练、验证、测试使用互斥的噪声族。`source_group`、原始应用和噪声族只用于审计与分层统计，不作为模型输入。原始 CESNET H5 数据不重新下载，也不提交 Git。

## 运行

Windows 环境检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

训练、Mamba 和 FlashAttention 必须在指定 WSL 环境执行：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_wsl_experiments.sh main"
```

三个入口分别是：

```bash
bash scripts/run_wsl_experiments.sh main       # TLS40/QUIC40 主比较
bash scripts/run_wsl_experiments.sh ablation   # 三个 HSTA-CM 组件消融
bash scripts/run_wsl_experiments.sh efficiency # batch 1、8、32 效率测试
```

实验配置位于 `configs/compact_s.yaml` 和 `configs/hsta_cm_ablation_s.yaml`。不使用旧 checkpoint；输出写入 `results/compact_s` 和 `results/hsta_cm_ablation_s`，这些目录被 Git 忽略。

## 评价

每个运行同时保存 raw argmax 和 threshold rejection 两套结果。报告已知类别 Accuracy/Macro-F1、unknown Precision/Recall/F1、AUROC、AUPR、已知流量误拒率、未知流量误判为已知比例、混合测试集 Accuracy/Macro-F1、参数量、训练轮数和运行时间，并按 `unknown_test_heldout` 与 `noise_test` 分层。拒识阈值只由已知验证流量校准。

TLS small 验证集中部分已知类别样本较少，Macro-F1 需结合每类样本数解释；单种子结果不表示均值和标准差。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/` | DataZoo 读取、协议缓存、采样和审计 |
| `models/` | HSTA-CM 与五个适配基线 |
| `configs/` | 当前主实验和消融配置 |
| `train.py` | 单次训练、早停、校准和测试 |
| `evaluate.py` | 载入检查点并重新评估 |
| `run_experiments.py` | 按 YAML 批量运行 |
| `scripts/` | WSL 入口、数据审计和结果汇总 |
| `docs/` | 架构、协议、范围和复现说明 |

详细约定见 [docs/architecture.md](docs/architecture.md)、[docs/experiment_protocol.md](docs/experiment_protocol.md)、[docs/experiment_scope.md](docs/experiment_scope.md) 和 [docs/reproducibility.md](docs/reproducibility.md)。
