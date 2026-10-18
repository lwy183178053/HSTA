# Project Environment and Directory Conventions

Read this file before running experiments or reorganizing the repository.

## Windows Python

Do not invoke `python` directly from PowerShell. Use the project interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <script or module>
```

The validated Windows environment uses Python 3.13.5.

## WSL and CUDA

Training and Mamba/FlashAttention checks use `Ubuntu-22.04` and
`/opt/traffic-mamba-venv`:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python <command>"
```

Do not use `docker-desktop` or `traffic-ubuntu-22.04` for this project.

## Directory conventions

- Lightweight result snapshots, histories, configurations, and Markdown under
  `results/` may be committed.
- Logs, datasets, checkpoints, prediction dumps, and binary artifacts remain
  local and must not be committed.
- Manuscripts and figures live in the sibling directory
  `E:\AllProject\流量分析python项目\paper`.
- Historical HSTA-CM and structure-search artifacts are outside the active
  repository at
  `E:\AllProject\流量分析python项目\HSTA_archive\pre_mvif_cleanup_2026-10-18`.

## Active experiment scope

- Formal comparisons: `results/formal60`
- Active configuration: `configs/compact_s.yaml`
- Model: `MVIF-Net` (`mvif-net`), plus five adapted baselines
- Current results: 30 completed baseline runs and MVIF-Net TLS open seed599
- Pending results: MVIF-Net TLS open seeds 5009/813 and QUIC open seeds 599/5009/813

MVIF-Net uses two Mamba blocks, two packet-graph blocks, two bounded residual
DFT convolutions with kernels `1/3`, branch normalization and gate, one
FlashAttention block, and `30+30+16=76` tokens. Do not reintroduce the archived
auxiliary-loss, time-CNN, residual-mode, or branch-removal switches into the
active model.

The user has authorized the next queue to run the five pending MVIF-Net TLS and
QUIC seeds. Keep the queue resumable and do not rerun completed results.

## Common entry points

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

The `--only` option on `run_experiments.py` is the supported way to launch only
the missing MVIF-Net seeds.
