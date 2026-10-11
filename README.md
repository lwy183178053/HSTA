# HSTA-CM：60 类加 unknown 的流量识别

项目在 CESNET-TLS22-S 和 CESNET-QUIC22-S 上运行固定的正式开放集实验。每个数据集独立选择训练日期内流量最多的 60 个应用作为已知类别。每条流使用前 30 个包的包长、方向和包间隔，输入为 [B,30,3]。HSTA-CM-open 输出 61 类；closed 和五个适配基线输出 60 类。

## 数据与主模型

两个最终文件为 data/processed/datazoo_tls60_s_protocol.csv 和 data/processed/datazoo_quic60_s_protocol.csv。每个已知类训练/验证/测试上限为 10000/2000/2000。真实 unknown 和噪声分别以同 split 的实际已知数量的 30% 和 10% 为目标；不是占最终混合数据的比例。全部满足时，混合数据中已知/真实 unknown/噪声约占 71.43%/21.43%/7.14%。严格按日期划分，unknown 应用身份与噪声生成族跨集合隔离；不足时报告 actual，不重复、不跨日期补采。直接扫描原始 H5，训练不使用 source 候选 CSV。

两个数据集采用同一三路、256 维主模型：

- 时序状态空间分支：两层残差 Mamba，30 个包 token。
- 包序列多尺度卷积分支：三层残差 Conv1d，核 1/3/5，30 个包 token。
- 频域多尺度卷积分支：rFFT 保留实部和虚部，三层残差 Conv1d，核 1/3/5，16 个频率 token。

加入包位置、频率位置和三种分支类型编码，76 个 token 经融合全连接和一层 PyTorch FlashAttention 块。注意力块包含 LayerNorm、残差和前馈网络，最终按分支等权池化并分类。DFT 是当前主模型的组成部分。

## 实验与运行

保留 HSTA-CM-open、HSTA-CM-closed、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN。五个基线是统一 PPI 输入下的适配实现；TrafficAudio 内部 BiGRU 保留。seed 为 599、5009、813，主比较共 42 次训练；no_conv、no_mamba、no_attention 共 18 次消融。训练目标有效优化器批次为 4096、验证/测试批次为 512；CUDA 显存不足时依次尝试较小微批次并累积梯度，每 4096 个样本执行一次优化器更新，记录实际微批次。若某模型含 BatchNorm，回退会改变其批次统计行为，因此结果中会标出实际微批次；主模型必须通过 4096 批次 CUDA smoke test。效率只测完整主模型推理 batch 1/8/32。所有训练从第 1 轮开始，最大 100 轮、patience 15，按已知验证 Macro-F1 调度和早停。raw argmax 与 threshold rejection 分开保存，阈值只用已知验证流量校准。

训练环境固定为 WSL Ubuntu-22.04 与 /opt/traffic-mamba-venv：

~~~powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && bash scripts/run_formal_pipeline.sh"
~~~

首次正式运行在该环境启动 bash scripts/run_formal_pipeline.sh；它会先做验收、导出并审计两份数据，然后依次运行主比较、消融、效率和汇总。完整后台队列成功启动后停止主动轮询，后续询问时再读取日志。

## 目录

| 路径 | 用途 |
| --- | --- |
| data/raw/ | 本地原始 H5、应用映射 |
| data/processed/ | 两份最终数据及 report、audit、sampling manifest |
| models/ | 三路 HSTA-CM、Mamba/FlashAttention 模块、五个适配基线 |
| configs/ | 当前正式主比较和消融配置 |
| train.py、evaluate.py | 训练、校准、评估 |
| run_experiments.py | 多模型、多数据集、多 seed 批量运行 |
| benchmark_efficiency.py | batch 1/8/32 推理测量 |
| scripts/ | 导出、审计、WSL 入口、汇总 |
| results/、logs/ | 本地结果、checkpoint、后台日志 |
| docs/ | 中文架构、协议、范围、复现说明 |

代码、配置、测试和文档提交 Git；数据、日志、结果和 checkpoint 保持忽略。论文存放在仓库外 E:\AllProject\流量分析python项目\paper。旧生成产物移到仓库外归档，原始 H5 保留。

详细规则见 [架构说明](docs/architecture.md)、[实验协议](docs/experiment_protocol.md)、[实验范围](docs/experiment_scope.md)、[复现说明](docs/reproducibility.md)。
