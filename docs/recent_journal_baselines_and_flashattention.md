# Recent Baselines and FlashAttention

## Controlled baseline scope

`configs/recent_journal_baselines.yaml` evaluates SRViT, TrafficAudio, and BPF-GNN on QUIC-40, QUIC-60, TLS-40, and TLS-60 with the shared `[B,30,3]` input and training protocol.

These models are controlled reimplementations of the core structures described in their papers, not official source-code or data-pipeline reproductions:

- SRViT uses multi-scale temporal patches, relative-position Vision Transformer layers, and mean pooling.
- TrafficAudio uses STFT, Mel filtering, DCT, 1D CNN layers, and bidirectional GRU layers.
- BPF-GNN builds a feature-packet-flow hierarchy with adjacent and top-k similarity edges and continuous subflows.

## HSTA FlashAttention

HSTA keeps the Q/K/V projections, output projection, four-head layout, residual connection, and post-transition attention position. The `flash` backend replaces explicit `softmax(QK^T)V` materialization with PyTorch `scaled_dot_product_attention`.

When `attention_backend: flash` is selected, CUDA FP16/BF16 experiments request `SDPBackend.FLASH_ATTENTION`. Unsupported hardware or data types cause an explicit error instead of a silent fallback.

FlashAttention is an efficiency backend, not a separate attention algorithm. Efficiency comparisons must record the backend used, and manual-versus-flash evaluation should use the same checkpoint when measuring kernel effects.

## Commands

```bash
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

Outputs are written to `results/recent_journal_baselines`, `results/hsta_flash`, `results/hsta_flash_ablation`, and `results/efficiency_benchmark`.
