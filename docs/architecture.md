# Architecture Map

## Shared Input

The data pipeline turns each encrypted flow into a tensor with shape `[B, 30, 3]`:

```text
packet size | transmission direction | packet inter-arrival time
```

`data/dataset.py` owns CSV loading, flow-level splitting, standardization, and PyTorch dataloaders. `data/preprocess.py` and `data/sampler.py` create the four DataZoo CSV files used by the experiments.

## HSTA

The implementation in `models/hsta.py` follows the Revision 10 sequence:

```text
[B, 30, 3]
  -> Linear(3, 128) + positional encoding
  -> MambaBlock
  -> MambaBlock
  -> FeedForwardBlock: 128 -> 512 -> 128  (Transition)
  -> AttentionBlock: four heads             (FlashAttention in final HSTA)
  -> FeedForwardBlock: 128 -> 512 -> 128  (Refinement)
  -> LayerNorm + mean pooling
  -> Linear(128, classes)
```

Every sequence block keeps the `[B, 30, 128]` shape. `models/mamba_model.py` supplies the residual Mamba block; `models/transformer.py` supplies the residual attention and feed-forward blocks. The same HSTA factory supports the controlled `No Attention`, `Front Attention`, and `Middle Attention` layouts in the ablation configurations.

## Comparison Models

```text
models/gru.py                      five-layer GRU
models/transformer.py              five-layer Transformer
models/adapted_sota.py             30pktTCNET-adapted and NetMamba-adapted
models/recent_journal_baselines.py SRViT, TrafficAudio, and BPF-GNN
```

All comparison models consume the same packet-level input and use the same training/evaluation entry points. The recent baselines keep their paper-specific internal operations, such as TrafficAudio's MFCC/CNN path and BPF-GNN's hierarchical graph construction.

## Runtime Flow

```text
configs/*.yaml
       |
       v
run_experiments.py -> train.py -> data.dataset + models.build_model
       |                              |
       v                              v
results/<group>/<exp_name>/     best.pt / latest.pt / metrics.json
       |
       +-> evaluate.py
       +-> benchmark_efficiency.py
       +-> summarize_paper_main_results.py
```
