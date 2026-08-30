# Project Environment Notes

Use this file first when starting a new Codex session in this repository.

## Windows Python

Do not use bare `python` from PowerShell in this project. It currently resolves to:

```powershell
C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe
```

That is the Microsoft Store launcher stub and may fail silently.

Use the project Anaconda interpreter instead:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <script-or-module>
```

Known version:

```text
Python 3.13.5
```

## WSL For Mamba/CUDA

Use `Ubuntu-22.04` for WSL training and Mamba/CUDA work.

Known good WSL Python:

```bash
/opt/traffic-mamba-venv/bin/python
```

Known good checks:

```text
torch 2.11.0+cu128
cuda True
mamba_ssm ok
```

Project path inside WSL:

```bash
/mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP
```

Recommended PowerShell pattern:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/tls40_s.yaml --resume"
```

Notes:

- `docker-desktop` is not a usable project shell.
- `traffic-ubuntu-22.04` can see the project path but does not have `/opt/traffic-mamba-venv`.
- The WSL default distro has been set to `Ubuntu-22.04`, but explicit `wsl -d Ubuntu-22.04 -- ...` is still preferred in scripts and one-off commands.

## Quick Check

Run this from PowerShell when unsure:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

## Results Layout

`paper/` is an archival directory for manuscript files. Do not delete, move,
rename, or rewrite anything under `paper/` while changing the codebase.

Main task results stay under:

- `results/tls40_s`
- `results/quic40_s`
- `results/tls60_s`
- `results/quic60_s`

Adapted SOTA comparisons are configured separately in `configs/sota_adapted.yaml` and should stay under:

- `results/sota_adapted/all_results.csv`
- `results/sota_adapted/<exp_name>`

HSTA no-attention ablation comparisons are configured separately in `configs/hsta_no_attention.yaml` and should stay under:

- `results/hsta_no_attention/all_results.csv`
- `results/hsta_no_attention/<exp_name>`

Recent journal baselines and HSTA FlashAttention experiments stay under:

- `results/recent_journal_baselines`
- `results/hsta_flash`
- `results/hsta_flash_ablation`

Efficiency benchmark results, including adapted SOTA rows, should stay in `results/efficiency_benchmark`.

Use `bash scripts/run_wsl_experiments.sh main_all` for the GRU and Transformer baselines across all four tasks and three seeds.
Use `bash scripts/run_wsl_experiments.sh sota_all` for the two adapted SOTA models across all four tasks and three seeds.
Use `bash scripts/run_wsl_experiments.sh recent_all` for SRViT, TrafficAudio, and BPF-GNN across all four tasks and three seeds.
Use `bash scripts/run_wsl_experiments.sh ablation_all` for HSTA no-attention and attention-position ablations.
Use `bash scripts/run_wsl_experiments.sh hsta_flash_all` for HSTA FlashAttention main and position experiments.
