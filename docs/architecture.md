# Model Architecture

## Unified input

The data pipeline converts each encrypted flow into `[B, 30, 3]`:

```text
packet size | transmission direction | inter-arrival time
```

- `data/preprocess.py` creates task-specific CSV files from DataZoo-compatible source data.
- `data/dataset.py` reconstructs packet rows into fixed-length flow tensors, fits the scaler on training data, and creates data loaders.
- `data/sampler.py` handles dataset initialization, temporal splits, class selection, and feature extraction.

Splits are flow-level and time-aware so packets from one flow cannot appear in multiple sets.

## HSTA

`models/hsta.py` implements the main architecture:

```text
[B,30,3]
  -> Linear(3,128) + positional encoding
  -> Mamba block
  -> Mamba block
  -> Transition FFN: 128 -> 512 -> 128
  -> four-head self-attention
  -> Refinement FFN: 128 -> 512 -> 128
  -> LayerNorm + mean pooling
  -> Linear(128, number of classes)
```

Every sequence sublayer preserves `[B, 30, 128]`. Mamba blocks use pre-normalization, selective state-space mixing, dropout, and residual addition. FFN and attention blocks use the same pre-normalized residual pattern.

The final configuration uses PyTorch scaled dot-product attention with the FlashAttention CUDA backend. This is an implementation backend for the exact attention operation; it does not change the model definition.

## Comparison models

```text
models/gru.py                      GRU baseline
models/transformer.py              Transformer baseline and attention blocks
models/adapted_sota.py             30pktTCNET and NetMamba adaptations
models/recent_journal_baselines.py SRViT, TrafficAudio, and BPF-GNN
```

All models share the same training, evaluation, input length, and feature constraints.

## Execution flow

```text
configs/*.yaml
       |
       v
run_experiments.py -> train.py -> data.dataset + models.build_model
       |                              |
       v                              v
results/<group>/<run>/          best.pt / latest.pt / metrics.json
       |
       +-> evaluate.py
       +-> benchmark_efficiency.py
       +-> scripts/summarize_paper_main_results.py
```
