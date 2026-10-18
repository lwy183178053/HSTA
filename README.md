# MVIF-Net

**MVIF-Net: A Multi-View Interactive Fusion Network for Encrypted Traffic Classification**

This repository contains the reproducible 60-class encrypted-traffic
classification experiments for MVIF-Net and five adapted comparison models.

## Model

MVIF-Net receives the first 30 packets of each flow as a `[B, 30, 3]` tensor
(packet length, direction, and inter-packet interval). It builds three views of
the same flow:

- two residual Mamba blocks produce 30 packet tokens;
- two packet-graph blocks use adjacent and feature-similarity relations and
  bounded learnable residual scales, producing 30 packet tokens;
- an `rFFT` branch keeps 16 frequency tokens, applies a `1x1` projection and
  two bounded residual convolutions with kernels `1` and `3`.

The three branches receive view-specific position/type embeddings, are
normalized and reweighted by a learned branch gate, and form `30 + 30 + 16 =
76` tokens. Token fusion, one FlashAttention block, branch-wise masked pooling,
and a single linear classifier produce the final prediction. Auxiliary branch
losses and exploratory time-domain CNN branches are not part of MVIF-Net.

## Current results

`results/formal60` currently contains 30 completed runs for the five adapted
baselines across TLS and QUIC with seeds `599`, `5009`, and `813`, plus the
completed MVIF-Net TLS open-set run with seed `599`. The remaining two TLS
seeds and three QUIC open-set seeds are configured for the resumable queue. The
current MVIF-Net results are therefore still a partial snapshot, not final
three-seed means and standard deviations.

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

The formal queue is resumable:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

To run only the remaining MVIF-Net TLS and QUIC seeds:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume --only mvif_net_open_tls60_seed5009 mvif_net_open_tls60_seed813 mvif_net_open_quic60_seed599 mvif_net_open_quic60_seed5009 mvif_net_open_quic60_seed813"
```

## Layout

- `models/`: MVIF-Net and the five adapted baselines
- `configs/`: the active formal comparison configuration
- `results/formal60/`: lightweight formal result snapshots
- `scripts/`: data audit, formal queue, smoke checks, and result summaries
- `docs/`: architecture, protocol, scope, and reproducibility notes

Datasets, checkpoints, logs, predictions, and other binary artifacts remain
local and are not part of the repository.
