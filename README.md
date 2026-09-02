# HSTA: Encrypted QUIC/TLS Traffic Classification

This repository contains the PyTorch implementation and reproducibility configuration for HSTA, a lightweight hybrid state-space and attention model for encrypted traffic classification. The public code repository intentionally contains code, configuration, tests, and experiment summaries only. Manuscript and submission files are maintained separately.

## Method scope

Every model receives the same privacy-preserving flow representation: the first 30 packets and three observable side-channel features (packet size, transmission direction, and inter-arrival time), with tensor shape `[B, 30, 3]`. HSTA applies two Mamba blocks, a Transition FFN, four-head attention, a Refinement FFN, mean pooling, and a linear classifier.

## Repository layout

```text
data/                         Data loading, preprocessing, and sampling
models/                       HSTA and comparison model implementations
configs/                      Reproducible YAML experiment configurations
scripts/                      Batch runners and result summarization
tests/                        Unit and configuration tests
docs/                         Architecture and reproducibility documentation
train.py                      Single-experiment training entry point
run_experiments.py            YAML-driven experiment entry point
evaluate.py                   Standalone checkpoint evaluation
benchmark_efficiency.py       Parameters, FLOPs, latency, and memory benchmark
```

Generated datasets, checkpoints, logs, and other large local artifacts are excluded from Git. See [docs/reproducibility.md](docs/reproducibility.md) for the complete protocol.

## Environment

Windows checks and CPU tests use the project Anaconda interpreter:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

Mamba/CUDA experiments use WSL `Ubuntu-22.04` with `/opt/traffic-mamba-venv`:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## Data preparation

CESNET-QUIC22 and CESNET-TLS-Year22 are obtained from their official public releases. Raw datasets are not redistributed here. After placing the source data in the expected local location, create a unified sequence CSV with:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --project-root . --topk 40
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --project-root . --topk 40
```

Use `--topk 60` for the TLS-60 and QUIC-60 tasks. The preprocessing pipeline performs flow-level temporal splitting, selects classes using training data, retains at most 30 packets, and fits standardization parameters on the training split only.

## Reproduce experiments

Run one configuration on Windows:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' run_experiments.py --config configs\tls40_s.yaml --resume
```

Run the validated WSL experiment groups:

```powershell
bash scripts/run_wsl_experiments.sh main_all
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh sota_all
bash scripts/run_wsl_experiments.sh ablation_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

All main experiments use seeds `42`, `2025`, and `3407`. Results are written below `results/`, which is intentionally ignored by Git.

## Evaluation and tests

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' evaluate.py --checkpoint results\hsta_flash\hsta_flash_tls40_s_seed42\best.pt --split test
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\summarize_paper_main_results.py
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
```

The fixed main comparison contains GRU, Transformer, 30pktTCNET, NetMamba, SRViT, TrafficAudio, BPF-GNN, and HSTA across QUIC-40, QUIC-60, TLS-40, and TLS-60. Recent baselines are controlled reimplementations under the shared input and training protocol; they are not claimed to be official reproductions.

## Attention backend

HSTA uses PyTorch scaled dot-product attention. The `flash` configuration selects the FlashAttention CUDA backend for efficiency while preserving the exact attention definition. If the requested backend is unavailable, the configuration fails explicitly instead of silently changing the experiment.

## Citation

If you use this code, cite the associated manuscript:

```text
W. Liu, N. Su, Y. Liu, D. Liu, Q. Zhang, and H. Zhao,
"HSTA: A Lightweight Hybrid State-Space and Attention Model for
Encrypted Traffic Classification," manuscript under review.
```

## License and data

This repository does not redistribute CESNET raw traffic. Users are responsible for following the dataset license and any institutional requirements. Add the project license before public release if a license has been selected by the authors.
