# HSTA-CM

HSTA-CM consumes the first 30 packets of each flow as a `[B, 30, 3]` tensor: packet size, direction, and inter-arrival time.

1. The time-domain convolution branch uses three native PyTorch `Conv1d` layers to encode local packet-position patterns and adds a projected residual from the input. It is a packet-local feature encoder, rather than a geometric image-space encoder.
2. The temporal state-space branch uses two `mamba_ssm` Mamba blocks to encode ordered dependencies and adds a residual from the temporal embedding.
3. Concatenated streams pass through a fully connected fusion layer and a sigmoid gate. A learned packet-position embedding is added to the fused sequence before attention so packet order remains explicit even when the Mamba branch is ablated.
4. One `FlashSelfAttention` block calls PyTorch scaled dot-product attention with the Flash backend only. CPU, FP32, math, and memory-efficient fallbacks are rejected. The attention ablation replaces this block with an identity path and keeps the same fusion and classification head.
5. Layer normalization, mean pooling, and a 101-way head produce the 100 known classes plus `unknown` for HSTA-CM-open. The closed HSTA control and adapted baselines use the same representation but a 100-way head and no unknown training target.

The component ablations disable the Conv1d branch or Mamba branch by replacing the removed branch with a zero tensor of the same hidden width. This isolates the contribution of each branch without changing the fusion head shape.

The open-set protocol maps held-out DataZoo applications and synthetic noise flows to `unknown`. HSTA-CM-open receives only the declared training unknown-support source; held-out applications and an unseen test noise family are never used for training. A closed-set model has no unknown output and uses a threshold on `1 - max(softmax)` calibrated from known validation flows. The label encoder keeps the explicit class at index 100 when it is present. Training, validation, and testing are disjoint date windows.

The comparison set is deliberately small: 30pktTCNET-adapted and NetMamba-adapted are shared-input reference methods; SRViT-adapted, TrafficAudio-adapted, and BPF-GNN-adapted are the three retained recent baselines requested for the paper revision. These are structural adaptations under the common `[30, 3]` input, not full reproductions of the original raw-byte, image, audio, or side-information pipelines. TrafficAudio's internal BiGRU remains part of that reference architecture; only the independent GRU baseline is removed.

## HSTA-CM-DFT extension

`HSTA-CM-DFT` is an additional frequency-domain experiment, not a replacement for the primary HSTA-CM result. It keeps the temporal state-space branch and replaces the time-domain `Conv1d` branch with a frequency-domain convolution branch:

1. `torch.fft.rfft(..., dim=1, norm="ortho")` transforms each of the three standardized packet features along the 30-packet axis.
2. The real and imaginary parts are stacked as `[B, 2, 3, 16]`. The first dimension after the batch is the real/imaginary channel, the height is the three feature rows, and the width is the one-sided frequency axis.
3. Three PyTorch `Conv2d` layers with a projected residual path use `(1, 3)` kernels, so they model adjacent frequency bins without pretending that packet size, direction, and inter-arrival time are image pixels with spatial adjacency.
4. Adaptive pooling produces one frequency summary vector per flow. It is broadcast over the 30 temporal tokens and combined with the Mamba sequence by the same learned gate, position embedding, FlashAttention block, and classification head.

For a real sequence of length `N`, the full DFT has `N` complex coefficients. The coefficients satisfy conjugate symmetry, so `rFFT` keeps only the non-redundant bins `0` through `floor(N/2)`. With `N=30`, that is `30//2+1=16` bins; the omitted 14 bins can be reconstructed from the kept values and do not contain independent information. The FFT is computed in FP32 before the Conv2d branch so the non-power-of-two length is safe under CUDA mixed precision.
