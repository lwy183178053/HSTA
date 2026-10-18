# Reproducibility

## Environment

Use the project Anaconda interpreter for Windows checks:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

Use WSL Ubuntu 22.04 and `/opt/traffic-mamba-venv` for Mamba, FlashAttention,
and CUDA checks:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## Active formal queue

The only active configuration is `configs/compact_s.yaml`. It contains the
five completed adapted baselines and MVIF-Net open-set runs on TLS and QUIC for
seeds `599`, `5009`, and `813`. The existing TLS seed599 MVIF-Net result is
retained; the other five MVIF-Net runs are pending or running in the current
queue.

Resume the complete configured queue with:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

To run only the missing MVIF-Net TLS and QUIC seeds:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume --only mvif_net_open_tls60_seed5009 mvif_net_open_tls60_seed813 mvif_net_open_quic60_seed599 mvif_net_open_quic60_seed5009 mvif_net_open_quic60_seed813"
```

The runner treats `summary.csv` plus `metrics.json` as the completion marker,
so completed lightweight result snapshots are not retrained merely because a
local checkpoint was removed.

## Audits and reporting

Before training, audit both exported datasets. After each run, verify the
recorded seed, input shape, parameter count, AMP mode, FlashAttention backend,
stopping reason, and threshold calibration metadata. Run
`scripts/summarize_compact_results.py` only against `results/formal60`.

The current aggregate has 30 baseline rows and one MVIF-Net TLS seed599 row. It
is a partial snapshot until the remaining TLS and QUIC seeds complete. Raw and
threshold metrics must remain separate in reports.

Datasets, logs, checkpoints, predictions, and binary artifacts remain local.
The former HSTA-CM and exploratory experiments are preserved outside the active
repository in `E:\AllProject\流量分析python项目\HSTA_archive\pre_mvif_cleanup_2026-10-18`.
