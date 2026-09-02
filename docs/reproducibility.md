# Reproducibility Protocol

This document records the fixed protocol used for the public experiment code.

## Tasks and inputs

The evaluation contains four tasks: QUIC-40, QUIC-60, TLS-40, and TLS-60. Each flow is represented by at most the first 30 packets and the three side-channel features `size`, `direction`, and `delta_time`. Short flows are zero-padded. Payloads, plaintext fields, domain names, and DPI-derived content are excluded.

## Splits and preprocessing

- Use the DataZoo-compatible CESNET-QUIC22 and CESNET-TLS-Year22 releases.
- Preserve the temporal train/validation/test intervals supplied by the dataset pipeline.
- Select Top-K classes from training data only.
- Fit `StandardScaler` parameters on training flows only, then transform validation and test flows.
- Reconstruct packet rows by `flow_id` before batching.

The raw datasets are not included because of size and distribution terms. Users must obtain them from the official releases and follow their licenses.

## Training protocol

- Random seeds: `42`, `2025`, and `3407`.
- Maximum epochs: 100, with validation Macro-F1 model selection and early stopping.
- Optimizer: AdamW with learning rate `5e-4` and weight decay `1e-4`.
- Input length: 30 packets; default training batch size: 512.
- Report mean and standard deviation over the three seeds.

## Model groups

The main comparison contains GRU, Transformer, 30pktTCNET, NetMamba, SRViT, TrafficAudio, BPF-GNN, and HSTA. Ablations evaluate attention placement and the no-attention variant. Efficiency measurements use batch sizes 1, 32, and 512, 20 warm-up iterations, 100 timed iterations, and five repeats.

## Reproduction commands

```bash
bash scripts/run_wsl_experiments.sh main_all
bash scripts/run_wsl_experiments.sh sota_all
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh ablation_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

Summarize completed runs with:

```bash
python scripts/summarize_paper_main_results.py
```

The generated results remain local and are ignored by Git. Record the GPU model, CUDA version, PyTorch version, commit ID, and configuration file alongside any reported result.
