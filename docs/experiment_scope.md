# Formal Experiment Scope

## Data protocol

The formal data are CESNET-TLS22-S and CESNET-QUIC22-S with 60 known
application classes. Each flow uses the first 30 packets and the three packet
features described in [architecture.md](architecture.md). The active formal
configuration uses fixed seeds `599`, `5009`, and `813`, a maximum of 100
epochs, patience 15, effective batch size 4096, and evaluation batch size 512.

## Active comparison matrix

The active `configs/compact_s.yaml` expands to 36 planned runs:

| Group | Models | Dataset | Seeds | Planned runs |
|---|---|---|---:|---:|
| Formal comparison | MVIF-Net plus five adapted baselines | TLS/QUIC open-set runs | 599/5009/813 | 36 |

The 30 baseline runs are already complete. The active results directory also
contains the completed MVIF-Net TLS open run for seed 599. The remaining two
TLS seeds and all three QUIC seeds are configured for the next resumable queue.

There are no active branch ablations, efficiency queues, time-domain CNN
searches, or auxiliary-loss experiments. Those artifacts are outside the
active repository in the dated cleanup archive.

## Capacity and precision

The five baselines retain their capacity-matched configurations and are marked
`adapted` in experiment names or model identifiers. MVIF-Net is reported with
its actual parameter count rather than being forced into the baseline capacity
range.

Mamba selective blocks run in FP32 outside autocast. NetMamba runs with AMP
disabled; other compatible operators use AMP. The actual backend and precision
are recorded in each `metrics.json`.

## Result status

`results/formal60/all_results.csv` currently contains 31 rows: 30 completed
baseline rows and one MVIF-Net TLS seed599 row. MVIF-Net TLS and QUIC results
must not be reported as final three-seed means or standard deviations until
their respective three seeds finish under the same protocol.
