# Figure Reproduction Guide

This document maps the implementation to the two core diagrams used with the manuscript. Editable artwork is maintained outside the public code repository; this guide documents the code-derived content needed to reproduce or audit the figures.

## HSTA architecture diagram

Read these files in order:

1. `configs/hsta_flash.yaml` for `dim: 128`, `heads: 4`, the `[mamba, mamba, mlp, attention, mlp]` layout, and the `flash` backend.
2. `models/hsta.py` for module assembly and ordering.
3. `models/mamba_model.py` for the residual Mamba block.
4. `models/transformer.py` for multi-head attention and the feed-forward block.

The diagram should show:

```text
[B,30,3] packet side channels
        |
Linear(3 -> 128) + positional encoding
        |
Mamba -> Mamba
        |
Transition FFN (128 -> 512 -> 128)
        |
Four-head attention with Q/K/V projections and SDPA FlashAttention
        |
Refinement FFN (128 -> 512 -> 128)
        |
LayerNorm -> mean pooling -> Linear(128 -> classes)
```

All sequence modules output `[B,30,128]`; pooling produces `[B,128]`; the classifier produces `[B,num_classes]`.

## Data-processing diagram

Read `data/preprocess.py`, `data/sampler.py`, and `data/dataset.py` in that order. The flow is:

```text
DataZoo records
  -> temporal train/validation/test split
  -> training-only Top-K class selection
  -> size/direction/inter-arrival extraction
  -> first 30 packets per flow, zero padding when needed
  -> CSV export and flow reconstruction
  -> training-only standardization
  -> DataLoaders
```

The model input is `[size, direction, delta_time]`. Metadata fields such as `flow_id`, `label`, `pkt_index`, and `split` are not model features. The implementation does not recompute timing values during diagram construction; it uses the exported DataZoo PPI field definition.

## Controlled variants

The ablation configuration supports:

```text
full HSTA:       Mamba -> Mamba -> FFN -> Attention -> FFN
front attention: Attention -> Mamba -> Mamba -> FFN -> FFN
middle attention: Mamba -> Attention -> Mamba -> FFN -> FFN
no attention:    Mamba -> Mamba -> FFN -> FFN -> FFN
```
