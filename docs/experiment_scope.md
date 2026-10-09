# Experiment Scope

The revised study uses the existing CESNET-TLS22 S and CESNET-QUIC22 S subsets. Each task has 100 known applications and one explicit `unknown` output. Flow dates determine train, validation, and test membership.

The compact comparison has six primary model families: HSTA-CM, 30pktTCNET-adapted, NetMamba-adapted, SRViT-adapted, TrafficAudio-adapted, and BPF-GNN-adapted. HSTA-CM uses three seeds on each dataset; each adapted comparison family uses seed 42 in the compact rerun. All models receive the same `[30, 3]` packet representation and class mapping. `HSTA-CM-DFT` is included as one additional seed42 extension run per dataset and is reported separately from the primary comparison rows.

The focused ablation compares the full HSTA-CM against three component removals on both datasets: no convolution branch, no Mamba branch, and no FlashAttention block. The replacement projection in the no-convolution branch keeps the tensor width fixed, while the no-Mamba branch keeps the input projection and positional embedding. There are no depth or width sweeps in the compact protocol. GRU, standalone Transformer, 40-class, 60-class, placement, ratio, and evidence-pack experiments are removed from the active project.

The efficiency protocol evaluates the retained model checkpoints with batch sizes 1, 8, and 32 only. It reports parameter count, analytical MACs/FLOPs, latency, throughput, and CUDA peak memory; data loading time is excluded.

The DFT extension transforms the 30 packet positions with a one-sided real FFT, producing 16 non-redundant frequency bins. It keeps real and imaginary components and applies three residual `(1, 3)` `Conv2d` layers along frequency. It is an exploratory frequency-domain result, so it does not expand the baseline or component-ablation matrix.

The final paper tables should report the mean and standard deviation of the three HSTA seeds. The compact adapted baselines currently use one seed and must be reported as single-run values until their three-seed reruns are completed; they must not be given a fabricated standard deviation. Open-set metrics are reported beside closed-set accuracy so unknown rejection is not hidden by known-class performance.
