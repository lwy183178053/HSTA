# MVIF-Net

**MVIF-Net: A Multi-View Interactive Fusion Network for Encrypted Traffic Classification**

This repository contains the reproducible 60-known-class encrypted-traffic
classification experiments for MVIF-Net and five adapted comparison models.

## Model

MVIF-Net receives the first 30 packets of each flow as a `[B, 30, 3]` tensor
(packet length, direction, and inter-packet interval). It builds three views of
the same flow:

- two directly stacked Mamba blocks without residual shortcuts produce 30 packet tokens;
- two packet-graph blocks use adjacent and feature-similarity relations, with
  one bounded learnable residual from the graph embedding to the first block's
  output, added before the second block;
- a 30-point `rFFT` produces 16 frequency tokens; after a `1x1` projection,
  Conv1d blocks with kernels `1` and `3` use one bounded residual from the
  projected input to the first convolution's output, added before the second.

The Mamba and packet-graph views share a learned packet-position embedding; the
frequency view has a separate position embedding. Each view has its own type
embedding. After branch normalization, a learned gate weights the three views
before concatenation into `30 + 30 + 16 = 76` tokens. Token fusion feeds one
SDPA Transformer block with a key-padding mask and residual connections around
its attention and feed-forward sublayers. PyTorch selects a compatible SDPA
backend automatically. A global masked mean over valid tokens and one linear
classifier produce the prediction. Open-set runs use 61 outputs; closed-set
runs use 60. Auxiliary branch losses and exploratory time-domain CNN branches
are not part of MVIF-Net.

## Current results

`results/formal60` contains the five baseline result sets. The active MVIF-Net
open/closed results are written to `results/mvif_net_masked_global_pooling`.
The active queue has one open-set and one closed-set MVIF-Net configuration for
each of TLS and QUIC, each using seeds `599`, `5009`, and `813`.

The previous HSTA-CM implementation, its structure search, ablations, and
efficiency experiments are preserved outside the active repository at:

`E:\AllProject\流量分析python项目\HSTA_archive\pre_mvif_cleanup_2026-10-18`

## Reproduction

Use the validated Windows interpreter for checks:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

Training and CUDA checks use WSL Ubuntu 22.04:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

The active 42-run queue is resumable:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

To run only selected MVIF-Net seeds without retraining completed runs:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume --only mvif_net_open_tls60_seed599 mvif_net_open_tls60_seed5009 mvif_net_open_tls60_seed813 mvif_net_open_quic60_seed599 mvif_net_open_quic60_seed5009 mvif_net_open_quic60_seed813 mvif_net_closed_tls60_seed599 mvif_net_closed_tls60_seed5009 mvif_net_closed_tls60_seed813 mvif_net_closed_quic60_seed599 mvif_net_closed_quic60_seed5009 mvif_net_closed_quic60_seed813"
```

## Layout

- `models/`: MVIF-Net and the five adapted baselines
- `configs/`: the active formal comparison configuration
- `results/formal60/`: the five baseline result snapshots
- `results/mvif_net_masked_global_pooling/`: MVIF-Net open/closed results and aggregate
- `scripts/`: data audit, formal queue, smoke checks, and result summaries
- `docs/`: architecture, protocol, scope, and reproducibility notes

Datasets, checkpoints, logs, predictions, and other binary artifacts remain
local and are not part of the repository.
