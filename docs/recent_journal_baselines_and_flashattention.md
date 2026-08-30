# 2026 期刊基线与 HSTA FlashAttention 实验

## 实验范围

近期基线配置位于 `configs/recent_journal_baselines.yaml`，包含 SRViT、TrafficAudio 和 BPF-GNN 在 QUIC-40、QUIC-60、TLS-40、TLS-60 上的三随机种子实验。三者统一接收 `[B, 30, 3]` 输入，即前 30 个包的包大小、方向与相邻到达时间间隔。

这些模型是论文核心结构在统一输入和训练协议下的重实现，不是官方代码或原始数据管线的完整复现：

- SRViT 使用 3/5/7 多尺度时间 patch、四层相对位置 ViT 和均值池化；不包含在线增量更新。
- TrafficAudio 在模型内执行 STFT、Mel 滤波与 DCT，再融合三层 1D-CNN 和两层双向 GRU。
- BPF-GNN 构建 Feature-Packet-Flow 三级图，使用相邻边、top-k 动态相似边和五个连续子流；不依赖 PyG。

## HSTA FlashAttention

HSTA 保留原 Q/K/V/输出投影、四头配置、残差连接和转换后注意力位置，仅将显式 `softmax(QK^T)V` 替换为 PyTorch `scaled_dot_product_attention`。`attention_backend: flash` 在 CUDA FP16/BF16 下强制 `SDPBackend.FLASH_ATTENTION`，不支持时直接失败，不静默回退。

FlashAttention 是实现效率与显存优化特性，不是本文原创注意力算法。Transformer 保持手工注意力实现，因此跨模型效率表必须披露后端差异；同一 HSTA checkpoint 的 manual/flash 对照用于单独衡量内核影响。

## 运行命令

```bash
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

所有入口使用 `--resume`。近期基线写入 `results/recent_journal_baselines`，HSTA 主实验写入 `results/hsta_flash`，位置消融写入 `results/hsta_flash_ablation`，效率结果写入 `results/efficiency_benchmark`。

## 论文主表

完整实验后运行：

```bash
python scripts/summarize_paper_main_results.py
```

生成的主表固定保留 GRU、Transformer、30pktTCNET、NetMamba、SRViT、TrafficAudio、BPF-GNN、HSTA，要求每个模型在每项任务上均有 42、2025、3407 三个有效种子。只有最终配置和有效结果会进入新表。
