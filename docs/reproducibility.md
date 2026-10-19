# Reproducibility

## Environment

Use the project Anaconda interpreter for Windows checks:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```

Use WSL Ubuntu 22.04 and `/opt/traffic-mamba-venv` for Mamba, SDPA, and CUDA
checks:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## Active formal queue

The only active configuration is `configs/compact_s.yaml`. It contains one
MVIF-Net open-set and one closed-set configuration for each of TLS and QUIC,
plus the five adapted baselines, all using seeds `599`, `5009`, and `813`.
MVIF-Net results are written to `results/mvif_net_masked_global_pooling`; the
completed baseline snapshots remain in `results/formal60`.

Resume the complete configured queue with:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

To resume selected MVIF-Net TLS and QUIC runs:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume --only mvif_net_open_tls60_seed599 mvif_net_open_tls60_seed5009 mvif_net_open_tls60_seed813 mvif_net_open_quic60_seed599 mvif_net_open_quic60_seed5009 mvif_net_open_quic60_seed813 mvif_net_closed_tls60_seed599 mvif_net_closed_tls60_seed5009 mvif_net_closed_tls60_seed813 mvif_net_closed_quic60_seed599 mvif_net_closed_quic60_seed5009 mvif_net_closed_quic60_seed813"
```

The runner treats `summary.csv` plus `metrics.json` as the completion marker,
so completed lightweight result snapshots are not retrained merely because a
local checkpoint was removed.

## Audits and reporting

Before training, audit both exported datasets. After each run, verify the
recorded seed, input shape, parameter count, AMP mode, SDPA backend policy,
stopping reason, and threshold calibration metadata. Run
`python scripts/summarize_compact_results.py` to write
`comparison_summary.csv` from available results in
`results/mvif_net_masked_global_pooling` and `results/formal60`. After all 42
runs have completed, add `--require-complete` to validate the full matrix and
write `comparison_source_groups.csv` beside the active aggregate.

The active aggregate contains 42 rows after the queue completes. Raw argmax
and threshold-rejection metrics remain separate; use the generated source
group snapshot for unknown-source results.

Datasets, logs, checkpoints, predictions, and binary artifacts remain local.
The former HSTA-CM and exploratory experiments are preserved outside the active
repository in `E:\AllProject\流量分析python项目\HSTA_archive\pre_mvif_cleanup_2026-10-18`.
