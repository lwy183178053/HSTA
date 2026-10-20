# Project Environment and Directory Conventions

Read this file before running experiments or reorganizing the repository.

## Windows Python

Do not invoke `python` directly from PowerShell. Use the project interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <script or module>
```

The validated Windows environment uses Python 3.13.5.

## WSL and CUDA

Training and Mamba/SDPA CUDA checks use `Ubuntu-22.04` and
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

- Formal comparisons: `results/mvif_net_masked_global_pooling` for MVIF-Net and `results/formal60` for baselines
- Active configuration: `configs/compact_s.yaml`
- Model: `MVIF-Net` (`mvif-net`), plus five adapted baselines
- Current results: 30 completed baseline runs plus the resumable MVIF-Net open/closed queue
- MVIF-Net queue: TLS/QUIC open and closed, each with seeds 599/5009/813

Every model-structure change must be reflected in `docs/architecture.md`.
Keep the formal MVIF-Net diagram and active experiment-variant diagrams
consistent with the implementation.

MVIF-Net uses two directly stacked Mamba blocks without branch residuals, two
packet-graph blocks with one bounded inter-layer residual, and DFT-CNN blocks
with kernels `1/3` and one bounded inter-layer residual. The two learnable
branch residual scales start at `0.1` and are bounded to `(0, 0.5)`. A
pre-concatenation branch gate weights the normalized views; the model then uses
`30+30+16=76` tokens and one masked SDPA Transformer block. That block has
residual connections around self-attention and its feed-forward sublayer.
PyTorch selects a compatible attention backend automatically. Post-attention
readout is a global masked mean over valid tokens. Do not reintroduce the archived
auxiliary-loss, time-CNN, residual-mode, or branch-removal switches into the
active model.

The user has authorized the MVIF-Net TLS/QUIC open and closed queue. Keep the
queue resumable and do not rerun completed results.

## Common entry points

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/compact_s.yaml --resume"
```

The `--only` option on `run_experiments.py` is the supported way to launch a
selected subset of the MVIF-Net open/closed seeds.
