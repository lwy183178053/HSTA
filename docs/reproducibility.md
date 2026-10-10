# Reproducibility

Use `Ubuntu-22.04` and `/opt/traffic-mamba-venv` for all Mamba and FlashAttention runs. Install `requirements.txt`, then verify that `mamba_ssm` is at least 2.3.2 and that PyTorch reports CUDA and a FlashAttention kernel.

Use the existing CESNET-TLS22 S and CESNET-QUIC22 S files. The export caps each of the 100 known applications at 10,000 flows in each date split and keeps all samples for smaller classes. The exporter holds out a small set of applications as `unknown`, appends seeded synthetic noise flows, writes packet rows with `source`, and creates explicit date based `train`, `val`, and `test` splits.

For an initial comparison, create a balanced temporal subset with `scripts/sample_temporal_dataset.py`. The `tiny` profile keeps up to 100 flows per class for training and 20 per class for validation and testing; `small` and `medium` use 500/100/100 and 1000/200/200. These are dataset-size profiles, not model-size profiles: every profile runs the same HSTA-CM and retained comparison implementations with the same architecture and parameter settings. Sampling is performed separately within each temporal split and never moves a flow between weeks. The first quick run uses `tiny` and model seed `599`.

Run `bash scripts/run_wsl_experiments.sh main` for the compact matrix, which includes one HSTA-CM-DFT extension run per dataset, or `bash scripts/run_wsl_experiments.sh ablation` for the three HSTA-CM component checks. Results and checkpoints stay under ignored `results/` and `logs/` directories. Never add raw H5 files, checkpoints, credentials, or local environments to Git.

Every checkpoint records the class list, scaler, seed, exact model configuration, actual attention backend, and open-set metrics. The primary report should include macro-F1, known accuracy, unknown recall/F1, known-to-unknown false acceptance rate, parameter count, and runtime.
