# Experiment Scope

The revised study uses the existing CESNET-TLS22 S and CESNET-QUIC22 S subsets. Each task has 100 known applications and one explicit `unknown` output. Flow dates determine train, validation, and test membership.

The compact comparison has six model families: HSTA-CM, 30pktTCNET-adapted, NetMamba-adapted, SRViT, TrafficAudio, and BPF-GNN. HSTA-CM uses three seeds on each dataset; each comparison family uses seed 42. All models receive the same `[30, 3]` packet representation and class mapping.

The focused ablation compares the full HSTA-CM against three component removals on both datasets: no convolution branch, no Mamba branch, and no FlashAttention block. The replacement projection in the no-convolution branch keeps the tensor width fixed, while the no-Mamba branch keeps the input projection and positional embedding. There are no depth or width sweeps in the compact protocol. GRU, standalone Transformer, 40-class, 60-class, placement, ratio, and evidence-pack experiments are removed from the active project.

The efficiency protocol evaluates the retained model checkpoints with batch sizes 1, 8, and 32 only. It reports parameter count, analytical MACs/FLOPs, latency, throughput, and CUDA peak memory; data loading time is excluded.

The final paper tables should report the mean and standard deviation of the three HSTA seeds, then one row per retained comparison family. Open-set metrics are reported beside closed-set accuracy so unknown rejection is not hidden by known-class performance.
