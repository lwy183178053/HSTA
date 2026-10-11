# 正式实验复现说明

## 环境

Windows 检查使用项目解释器：

~~~powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
~~~

训练、Mamba 和 FlashAttention 固定使用 Ubuntu-22.04 与 /opt/traffic-mamba-venv：

~~~powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
~~~

## 数据与正式队列

使用本地原始 H5、servicemap，直接导出唯一 TLS60/QUIC60 CSV，数据 seed 599。时间、类别选择、30% 真实 unknown、10% 噪声和身份隔离见实验协议。report、audit、sampling manifest 记录实际数量与来源。先归档旧产物，再重建，不使用旧 source 或 checkpoint。

正式训练目标有效优化器批次为 4096，验证/测试批次为 512。显存不足时以 2048、1024、512 微批次累积梯度，并记录实际微批次。回退可保持每次优化器更新所含样本数，但含 BatchNorm 的模型会按微批次计算统计量；主 HSTA-CM 需通过完整 4096 批次的 CUDA smoke test。

在指定 WSL 环境的项目根目录运行：

~~~bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
~~~

main 为 42 次主训练，ablation 为 18 次消融，efficiency 仅测完整主模型 batch 1/8/32。全部从第 1 轮开始，最多 100 轮、patience 15，以已知验证 Macro-F1 调度和早停。完整后台队列依次完成导出、审计、主训练、消融、效率及汇总，异常写失败状态和日志。

主比较配置为 configs/compact_s.yaml，结果写入 results/formal60；消融配置为 configs/hsta_cm_ablation_s.yaml，结果写入 results/hsta_cm_ablation_formal60；效率写入 results/efficiency_benchmark。配置文件名中的 s 表示 S 源数据集，不表示小规模。完整首次队列由 bash scripts/run_formal_pipeline.sh 启动；数据已经生成并通过审计后，可分别运行 scripts/run_wsl_experiments.sh main、ablation、efficiency，不会重新导出数据。

初次启动检查进程存活和首段日志；确认成功后不主动轮询。后续询问时读取日志/状态。导出预计 1–3 小时、单卡全套训练预计 2–5 天，只是初估；应结合实际每轮时间更新。

## 验收与保存

运行 pytest、编译、CUDA smoke test：完整模型 76 token，open 输出 61 类、closed 60 类，三种编码和 FlashAttention 后端启用。审计日期、flow ID、应用身份、噪声族、类别映射及实际数量。每个结果保留完整配置、seed、类别映射、scaler、阈值、训练历史、checkpoint、raw/threshold 及来源分层指标。

汇总三 seed 单次结果与 mean±std，不引用归档结构搜索或不同类别规模数据。样本不足在论文中说明。代码、配置、测试、文档提交 Git；数据、报告、日志、结果、checkpoint、本地环境文件忽略。提交前执行 git diff --check 并核对暂存文件。论文和图表放仓库外 E:\AllProject\流量分析python项目\paper。
