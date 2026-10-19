# 60-Class MVIF-Net Experiment Protocol

This protocol covers the active MVIF-Net open/closed comparison and five
baseline models on CESNET-TLS22-S and CESNET-QUIC22-S.

## Data and labels

Each flow is represented by the first 30 packets and three standardized packet
features. Known application identities, date windows, flow IDs, unknown source
identities, and generated noise families are isolated across splits. Dataset
export and audit are performed before training.

Open-set MVIF-Net training uses 60 known classes plus an unknown output. The
closed-set MVIF-Net head has 60 outputs and trains only on known classes.
Unknown flows remain in validation and test for measuring threshold-based
rejection, so this is a closed-set training head under the shared open-world
evaluation protocol, not a test split with unknown examples removed. The five
adapted baselines use the same known-class training protocol and input shape,
with their original behavior preserved in the active configuration. Each
protocol has one MVIF-Net open-set and one MVIF-Net closed-set configuration.

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
the complete model. Other compatible operators use AMP. Attention uses PyTorch
scaled dot-product attention with a key-padding mask; PyTorch selects a
compatible backend automatically.

## Current status

The 30 adapted-baseline runs remain valid. The active MVIF-Net results are
stored separately from those baseline snapshots. Generate the final 42-run
summary only after verifying all twelve MVIF-Net and thirty baseline
`summary.csv` and `metrics.json` files.

The former HSTA-CM structure matrix, gate/auxiliary-loss search, residual
search, time-domain CNN search, and efficiency benchmark are historical
artifacts in the external cleanup archive and are excluded from active result
aggregation.
