# Formal Experiment Scope

## Data protocol

The formal data are CESNET-TLS22-S and CESNET-QUIC22-S with 60 known
application classes. Each flow uses the first 30 packets and the three packet
features described in [architecture.md](architecture.md). The active formal
configuration uses fixed seeds `599`, `5009`, and `813`, a maximum of 100
epochs, patience 15, effective batch size 4096, and evaluation batch size 512.

## Active comparison matrix

The active `configs/compact_s.yaml` expands to 42 planned runs:

| Group | Models | Dataset | Seeds | Planned runs |
|---|---|---|---:|---:|
| MVIF-Net | one open-set and one closed-set configuration per protocol | TLS/QUIC | 599/5009/813 | 12 |
| Baselines | five adapted comparison models | TLS/QUIC closed-set runs | 599/5009/813 | 30 |

The five baseline result sets remain in `results/formal60`. The active MVIF-Net
results are isolated in `results/mvif_net_masked_global_pooling` so superseded
MVIF-Net rows cannot be mistaken for the corrected topology.

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

The formal matrix is 42 runs: 30 baselines plus twelve MVIF-Net runs. Open-set
and closed-set results must be reported separately; closed-set runs use a
60-class head, while open-set runs use a 61-class head with threshold metrics.
