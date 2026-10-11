# Project Environment and Directory Conventions

Read this file before running experiments or reorganizing the code repository.

## Windows Python

Do not invoke `python` directly from PowerShell. Use the project Anaconda interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <script or module>
```

The validated Windows environment uses Python 3.13.5.

## WSL and CUDA

Training and Mamba/CUDA experiments use `Ubuntu-22.04` and `/opt/traffic-mamba-venv`:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python <command>"
```

`docker-desktop` and `traffic-ubuntu-22.04` are not supported project environments. Always specify `wsl -d Ubuntu-22.04` explicitly.

## Directory conventions

- Lightweight numeric results, training histories, run configurations, and result documentation (CSV/JSON/YAML/Markdown) under `results/` may be committed for backup. Mark snapshots from unfinished runs as partial; do not present them as final comparisons.
- Logs, local datasets, checkpoints, prediction dumps, and binary experiment artifacts remain local and must not be committed.
- Manuscript, figures, source documents, and submission materials are stored in the sibling directory `E:\AllProject\流量分析python项目\paper`, outside this code repository. Code changes must not recreate a manuscript directory inside the repository.
- Do not commit checkpoints, raw traffic, credentials, or local environment files.

## Experiment groups

- Formal 60-class comparisons: `results/formal60`
- HSTA-CM ablations: `results/hsta_cm_ablation_formal60`
- Efficiency tests: `results/efficiency_benchmark`

## Current model and execution scope

- HSTA-CM uses two residual Mamba layers, two residual packet graph layers, and a two-layer DFT-CNN with kernels `1/3`; hidden dimension is 256 and the full layout is `30+30+16=76` tokens.
- The graph uses only within-flow sequential and feature-similarity relations. Packet/frequency positions and three branch-type embeddings precede a single FlashAttention block.
- Formal branch ablations are `no_mamba`, `no_gnn`, and `no_dft`. `no_attention` is optional and excluded from the formal 18-run ablation matrix.
- Currently only the five baselines across two datasets and three seeds (30 runs) are authorized to continue. Do not start the revised HSTA-CM, ablations, or efficiency experiments until the user asks. Code checks and smoke tests are allowed; do not interrupt the existing baseline queue.

## Common entry points

```bash
bash scripts/run_formal_pipeline.sh
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
bash scripts/run_wsl_experiments.sh efficiency
```

The Windows `scripts/run_formal_pipeline.ps1` entry defaults to export and audit only; `-RunTraining` explicitly opts into training. The shell full pipeline includes training. Individual experiment commands assume the final CSVs already exist and passed audit. Respect the current execution scope above before invoking any training entry point.

Windows environment check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```
