# 近期基线与 HSTA FlashAttention 实验

## 实验范围

`configs/recent_journal_baselines.yaml` 包含 SRViT、TrafficAudio 和 BPF-GNN 在 QUIC-40、QUIC-60、TLS-40、TLS-60 上的三种子实验。三者统一接收 `[B,30,3]` 输入，即前 30 个包的包大小、方向和包间隔时间。

这些模型是在统一输入和训练协议下，根据论文核心结构进行的重实现，不是官方代码或原始数据管线的完整复现：

- SRViT：3/5/7 多尺度时间 patch、四层相对位置 ViT 和均值池化。
- TrafficAudio：STFT、Mel 滤波、DCT，结合三层 1D-CNN 和两层双向 GRU。
- BPF-GNN：Feature-Packet-Flow 三级图，包含相邻边、top-k 动态相似边和五个连续子流；不依赖 PyG。

## HSTA FlashAttention

HSTA 保留 Q/K/V 投影、输出投影、四头配置、残差连接和转换后注意力位置，只把显式 `softmax(QK^T)V` 替换为 PyTorch `scaled_dot_product_attention`。配置 `attention_backend: flash` 时，在 CUDA FP16/BF16 下强制使用 `SDPBackend.FLASH_ATTENTION`；不支持时直接报错，不静默回退。

FlashAttention 只用于效率和显存优化，不是论文新增的注意力定义。Transformer 仍使用手工注意力，因此效率表必须记录后端差异；同一 HSTA checkpoint 的 manual/flash 对照用于单独评估内核影响。

## 运行命令

```bash
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

输出目录分别为 `results/recent_journal_baselines`、`results/hsta_flash`、`results/hsta_flash_ablation` 和 `results/efficiency_benchmark`。所有实验默认使用断点续训。

## 主表

实验完成后运行：

```bash
python scripts/summarize_paper_main_results.py
```

主表固定保留 GRU、Transformer、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN 和 HSTA，并要求每个模型在每个任务上都有 `42`、`2025`、`3407` 三个有效种子。
