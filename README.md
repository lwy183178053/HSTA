# HSTA-CM: Encrypted Traffic Classification

This repository contains the open-set experiment code for HSTA-CM on CESNET-TLS22 and CESNET-QUIC22. Every flow is represented by its first 30 packets and three observable features: packet size, direction, and inter-arrival time. In this repository, “compact” describes the reduced experiment/data-sampling scope only; it does not describe a reduced-parameter model.

HSTA-CM-open uses native `Conv1d` for packet-position structure, the current `mamba_ssm` package for temporal modeling, gated fusion, and PyTorch FlashAttention. It predicts 100 known applications plus an explicitly trained `unknown` reject class. The retained comparison models are trained as ordinary 100-way known-class classifiers without unknown labels; they use a validation-calibrated confidence threshold only at open-set inference. Held-out applications and synthetic-noise flows are mapped to `unknown` for evaluation; the final protocol keeps the test noise generator separate from the training noise generator, and train, validation, and test are date-disjoint.

The retained comparison implementations are 30pktTCNET-adapted, NetMamba-adapted, SRViT-adapted, TrafficAudio-adapted, and BPF-GNN-adapted. They preserve each reference method's main modeling idea while using the common `[30, 3]` packet representation; they are not claimed to reproduce the original raw-byte, image, audio, or side-information pipelines. GRU and standalone Transformer remain absent as independent comparison models, although the TrafficAudio-adapted reference retains its internal BiGRU component.

`HSTA-CM-DFT` is an optional frequency-domain extension experiment. It applies a one-sided `rFFT` along the 30-packet axis, stacks real and imaginary parts as `[B, 2, 3, 16]`, encodes adjacent frequency bins with three residual PyTorch `Conv2d` layers using `(1, 3)` kernels, and fuses the pooled frequency vector with the two-layer Mamba temporal branch. It is reported separately from the primary HSTA-CM comparison.

## Layout

`data/` contains DataZoo export and temporal CSV loading code. `models/` contains HSTA-CM and the five retained adapted comparison implementations. `configs/` contains the compact S matrix and focused HSTA ablation. `train.py` and `evaluate.py` are the single-run entry points; `run_experiments.py` expands YAML matrices. `scripts/run_wsl_experiments.sh` runs the supported WSL groups. `docs/` records the architecture, scope, and reproducibility protocol.

Generated datasets, results, logs, and checkpoints are ignored by Git. Raw CESNET traffic is not redistributed.

## Setup

Windows checks use the project interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m pip install -r requirements.txt
```

Training uses the required WSL environment:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/HSTA && source /opt/traffic-mamba-venv/bin/activate && python -m pytest -q"
```

## Data and experiments

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset tls --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --datazoo-batch-size 2048 --datazoo-test-batch-size 2048
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m data.preprocess --dataset quic --size S --topk 100 --max-train-per-class 10000 --max-val-per-class 10000 --max-test-per-class 10000 --datazoo-batch-size 2048 --datazoo-test-batch-size 2048
```

The existing S H5 files are used directly. Each known class is capped at 10,000 flows per date split; classes with fewer flows keep all available samples. Held-out applications and synthetic noise share the `unknown` label. Then run:

```bash
bash scripts/run_wsl_experiments.sh main
bash scripts/run_wsl_experiments.sh ablation
```

For the first inexpensive comparison, sample a balanced temporal subset from the processed TLS S CSV, then run all retained models with seed `599`:

```bash
python scripts/sample_temporal_dataset.py --input-csv data/processed/datazoo_tls100_s_seq30.csv --output-csv data/processed/datazoo_tls100_s_seq30_tiny.csv --dataset tls --profile tiny --seed 599
bash scripts/run_wsl_experiments.sh quick_tls
```

The subset profiles use per-class caps of train/validation/test `100/20/20` (`tiny`), `500/100/100` (`small`), `1000/200/200` (`medium`), and `10000/1000/2000` (`paper`). The generated `data/processed/datazoo_tls100_s_seq30_<profile>.csv` and `data/processed/datazoo_quic100_s_seq30_<profile>.csv` files use the same class mapping and temporal windows. These profiles change only how many flows are sampled; they do not change the model architecture, hidden widths, layer counts, or parameter count. The split labels retain the DataZoo temporal windows: earlier days for training, the following validation window, and the later week for testing.

The revised matrix reports known-only accuracy/Macro-F1 separately from unknown recall/precision/F1, AUROC/AUPR, known false-reject rate, parameter count, and runtime. `scripts/summarize_compact_results.py` aggregates completed runs. The older `results/compact_s_tls_seed599` directory used a 101-way head for every model and is retained only as a pipeline check, not as evidence for the reject-class contribution.
