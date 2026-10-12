# HSTA-CM 流量识别

本项目在 CESNET-TLS22-S 和 CESNET-QUIC22-S 上开展 60 个已知应用类别的开放集流量识别。每条流输入前 30 个包的包长、方向和包间隔特征，张量形状为 `[B, 30, 3]`。数据集文件名中的 `s` 指 CESNET S 源数据集，不表示小规模数据。

## 数据

当前正式数据文件为：

- `data/processed/datazoo_tls60_s_protocol.csv`
- `data/processed/datazoo_quic60_s_protocol.csv`

每个已知类别训练/验证/测试上限为 `10000/2000/2000`。每个 split 的真实 unknown 目标为已知流量的 30%，合成噪声目标为 10%；不足时按实际可用量导出，不重复流量。按固定日期窗口划分，unknown 应用身份和噪声生成族在集合间隔离。审计字段不作为模型输入。

## HSTA-CM

主模型输入维度为 256，完整输出 76 个 token：30 个 Mamba 时序 token、30 个包关系图 token、16 个 DFT 频率 token。三路分别建模包序列状态依赖、单流包关系和频谱局部结构，拼接后使用单层 PyTorch FlashAttention 融合。各分支包含两层残差主干块，open 输出 61 类并训练 unknown，closed 输出 60 类且不使用 unknown 监督。

三路是同一份流量特征的不同归纳视角，不是三份独立观测。DFT 沿包序号计算，不能直接解释为真实时间周期。详细结构见 [docs/architecture.md](docs/architecture.md)。

## 深度与容量公平性

深度按每条串行特征主干路径上的主干块计数，最多 4 个。输入投影、分类头、残差块内部的卷积/线性算子不单独计层；并行分支按各自路径计数，不把并行路径深度相加。参数量控制在约 2.2–2.3M，兼顾深度上限与容量接近。当前配置已完成实例化核算：

| 模型 | 建议结构 | 预计参数量 |
| --- | --- | ---: |
| HSTA-CM | `dim=256`；Mamba/GNN/DFT 各 2 块，融合注意力 1 块 | 2.294M |
| 30pktTCNET-adapted | `channels=300`，分类层 300，4 个残差时序卷积块 | 2.278M |
| NetMamba-adapted | `dim=292`，4 个 Mamba 块，全模型关闭 AMP | 2.294M |
| SRViT-adapted | `dim=192`、`mlp_ratio=3`，4 个注意力块 | 2.204M |
| TrafficAudio-adapted | `dim=416`，3 层 CNN 与 2 层 BiGRU 并行 | 2.211M |
| BPF-GNN-adapted | `dim=664`，图层级深度 `(1,2,1)`，总计 4 个图块 | 2.259M |

上述数值是当前配置实例化后的参数量核算值；训练结果仍会把实际统计值写入运行配置。参数匹配控制模型容量的大致尺度，不代表 FLOPs、优化难度或原论文实现完全相同。五个对照模型都适配到共同的 `[30,3]` 输入，须在论文中标明 `adapted`，不能称作原论文完整复现。

## 实验矩阵

- 主比较：HSTA-CM-open、HSTA-CM-closed 和五个适配基线；TLS、QUIC 两数据集，seed `599/5009/813`，共 42 次训练。
- 消融：`no_mamba`、`no_gnn`、`no_dft`，相同数据、seed 和 open unknown 监督，共 18 次训练。
- 效率：完整 HSTA-CM 在 TLS、QUIC 上测试推理 batch `1/8/32`。

所有运行最多 100 轮、patience 15，依据已知验证集 Macro-F1 调度学习率和早停。Mamba selective block 强制 FP32；NetMamba 全模型关闭 AMP；其余模型使用 AMP。这样保留其他模型的混合精度加速，同时规避 selective scan 在 AMP 下的数值不稳定，精度设置会在结果中披露。

旧的五基线队列已停止，旧结果已移到仓库外归档；当前 `results/formal60` 为空，等待本轮公平性配置启动。新的后台队列将重新运行主比较、三路消融及效率实验。归档快照不作为本轮正式比较结论。

## 环境与入口

数据导出和审计由 Windows 原生入口执行；训练、Mamba 和 FlashAttention 使用 WSL `Ubuntu-22.04` 与 `/opt/traffic-mamba-venv`。项目工作目录为 `E:\AllProject\流量分析python项目\HSTA`。

```powershell
& .\scripts\run_formal_pipeline.ps1
```

该入口默认只导出并审计数据。实验命令和完整复现步骤见 [docs/reproducibility.md](docs/reproducibility.md)，固定实验范围见 [docs/experiment_scope.md](docs/experiment_scope.md)，开放集指标定义见 [docs/experiment_protocol.md](docs/experiment_protocol.md)。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/raw/` | 本地 H5 和应用映射 |
| `data/processed/` | 正式 CSV 及审计文件 |
| `models/` | HSTA-CM 与五个适配基线 |
| `configs/` | 主比较与消融配置 |
| `train.py`、`evaluate.py` | 训练、评估入口 |
| `scripts/` | 数据导出、审计、运行和汇总 |
| `results/` | 数值结果、历史、配置与本地 checkpoint |
| `logs/` | 本地运行日志和状态文件 |
| `docs/` | 架构、协议、范围和复现说明 |

Git 可保存代码、配置、测试、文档和轻量结果快照。数据、原始 H5、日志、checkpoint、预测明细和二进制产物不提交。运行中的快照必须标记未完成状态。论文和图表存放在仓库外的 `E:\AllProject\流量分析python项目\paper`。
