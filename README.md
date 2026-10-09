# HSTA: Encrypted Traffic Classification

This repository contains the compact open-set experiment code for HSTA-CM on CESNET-TLS22 and CESNET-QUIC22. Every flow is represented by its first 30 packets and three observable features: packet size, direction, and inter-arrival time.

HSTA-CM uses native `Conv1d` for packet-position structure, the current `mamba_ssm` package for temporal modeling, gated fusion, and PyTorch FlashAttention. The model predicts 100 known applications plus `unknown`. Held-out applications and seeded synthetic noise are mapped to `unknown`; train, validation, and test are date-disjoint.

The retained comparison families are 30pktTCNET-adapted, NetMamba-adapted, SRViT, TrafficAudio, and BPF-GNN. GRU, standalone Transformer, 40/60-class tasks, and old evidence scripts are removed from the active registry.

## Layout

`data/` contains DataZoo export and temporal CSV loading code. `models/` contains HSTA-CM and the five retained comparison implementations. `configs/` contains the compact S matrix and focused HSTA ablation. `train.py` and `evaluate.py` are the single-run entry points; `run_experiments.py` expands YAML matrices. `scripts/run_wsl_experiments.sh` runs the supported WSL groups. `docs/` records the architecture, scope, and reproducibility protocol.

Generated datasets, results, logs, and checkpoints are ignored by Git. Raw CESNET traffic is not redistributed.

## Setup

Windows checks use the project interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

Training uses the required WSL environment:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## Data and experiments

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --topk 100 --max-train-per-class 1000 --max-val-per-class 1000 --max-test-per-class 1000 --datazoo-batch-size 2048 --max-export-batches 500
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --topk 100 --max-train-per-class 1000 --max-val-per-class 1000 --max-test-per-class 1000 --datazoo-batch-size 2048 --max-export-batches 500
```

The existing S H5 files are used directly. The checked-in local export keeps up to 1,000 flows per known class in each date split so it remains small; smaller classes are retained in full. For the full balanced export, use 10,000 for all three caps and omit `--max-export-batches`. Held-out applications and synthetic noise share the `unknown` label. Then run:

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
```

The compact matrix reports macro-F1, known accuracy, unknown recall/precision/F1, known-to-unknown false acceptance rate, parameter count, and runtime. `scripts/summarize_compact_results.py` aggregates completed runs.
