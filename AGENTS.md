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
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python <command>"
```

`docker-desktop` and `traffic-ubuntu-22.04` are not supported project environments. Always specify `wsl -d Ubuntu-22.04` explicitly.

## Directory conventions

- `results/`, `logs/`, and local datasets are generated artifacts and are ignored by Git.
- Manuscript, figures, source documents, and submission materials are stored in the sibling directory `E:\AllProject\流量分析python项目\paper`, outside this code repository. Code changes must not recreate a manuscript directory inside the repository.
- Do not commit checkpoints, raw traffic, credentials, or local environment files.

## Experiment groups

- Main tasks: `results/tls40_s`, `results/quic40_s`, `results/tls60_s`, `results/quic60_s`
- Adapted methods: `results/sota_adapted`
- HSTA ablations: `results/hsta_no_attention`, `results/hsta_flash_ablation`
- Recent baselines: `results/recent_journal_baselines`
- HSTA main experiments: `results/hsta_flash`
- Efficiency tests: `results/efficiency_benchmark`

## Common entry points

```bash
bash scripts/run_wsl_experiments.sh main_all
bash scripts/run_wsl_experiments.sh sota_all
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh ablation_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

Windows environment check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```
