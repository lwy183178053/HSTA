# 60-Class Open-Set Experiment Protocol

This protocol covers the active MVIF-Net and baseline comparison on
CESNET-TLS22-S and CESNET-QUIC22-S.

## Data and labels

Each flow is represented by the first 30 packets and three standardized packet
features. Known application identities, date windows, flow IDs, unknown source
identities, and generated noise families are isolated across splits. Dataset
export and audit are performed before training.

Open-set MVIF-Net training uses 60 known classes plus an unknown output. The
five adapted baselines use the same known-class protocol and input shape, with
their original training behavior preserved in the active configuration.

## Metrics

Every completed run writes raw argmax metrics and threshold-rejection metrics.
The formal comparison reports:

- open-set accuracy and Macro-F1;
- known-class accuracy and Macro-F1;
- unknown precision, recall, F1, AUROC, and AUPR;
- known-as-unknown and unknown-as-known rates;
- parameter count, runtime, stopping reason, AMP mode, and attention backend.

The rejection threshold is calibrated on the validation split only. Test data
are not used to select the threshold.

## Training controls

The active configuration uses 100 maximum epochs, patience 15, validation
known-class Macro-F1 for scheduling and early stopping, effective batch size
4096, evaluation batch size 512, and seeds `599`, `5009`, and `813`. CUDA OOM
fallbacks use gradient accumulation and are recorded in the result metadata.

Mamba selective blocks run in FP32 outside autocast. NetMamba disables AMP for
the complete model. Other compatible operators use AMP. FlashAttention is
required for the formal MVIF-Net path and its actual backend is recorded.

## Current status

The five adapted baselines have completed all TLS/QUIC runs for the three
seeds. MVIF-Net currently has one completed TLS open-set run at seed 599. The
remaining two TLS seeds and all three QUIC open-set seeds are now configured
for the resumable queue. Until those runs finish, the existing MVIF-Net result
must remain explicit as a partial state and must not be summarized as a final
three-seed mean or standard deviation.

The former HSTA-CM structure matrix, gate/auxiliary-loss search, residual
search, time-domain CNN search, and efficiency benchmark are historical
artifacts in the external cleanup archive and are excluded from active result
aggregation.
