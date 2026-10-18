# MVIF-Net Architecture

## Input and depth convention

Each flow is represented by the first 30 packets and three standardized
features per packet: packet length, direction, and inter-packet interval. The
model input is `[B, 30, 3]` and the hidden width is 256.

Depth is reported as the number of serial feature blocks on a branch. Input
projections, normalization, pooling, residual sub-operators, and the final
classifier are not counted as additional backbone blocks. The three parallel
branches are reported separately.

## MVIF-Net: three interactive views

| View | Main blocks | Tokens | Role |
|---|---:|---:|---|
| Mamba | 2 residual Mamba blocks | 30 | packet order and state dependency |
| Packet graph | 2 residual message-passing blocks | 30 | adjacent and feature-similarity packet relations |
| DFT-CNN | residual Conv1d with kernels 1 and 3 | 16 | local structure over rFFT frequency bins |
| Fusion | 1 FlashAttention block | 76 total | cross-view token interaction |

The Mamba path keeps its internal residuals and an outer residual around the
two blocks. The graph path has separate local and nonlocal message projections;
each block adds its update through a learnable scale constrained to `(0, 0.5)`.
The DFT path keeps real and imaginary parts of the 16-point one-sided rFFT,
projects six channels to 256 dimensions, and applies two residual convolution
blocks with the same bounded scale mechanism.

Each branch receives its own position encoding and branch-type embedding. A
LayerNorm plus masked mean produces one summary per branch. The three summaries
are passed through a small MLP and Softmax to obtain branch weights, which
reweight the branch tokens before concatenation.

The resulting 76 tokens pass through token fusion, one FlashAttention block
with four heads, and LayerNorm. The output is split back into 30/30/16 token
groups, pooled with the corresponding masks, averaged across views, and sent
to a single linear classifier. Open-set experiments use 61 outputs (60 known
classes plus unknown); closed-set variants, when run, use 60 outputs.

## Packet graph

The graph is built independently for each flow from standardized packet
features. Self-loops and adjacent packet positions form the sequential graph.
For nonlocal structure, direct neighbors are excluded and the four nearest
packets by feature distance are connected symmetrically. No labels, source
metadata, or cross-flow edges are used. Padding packets are excluded from
messages and masked pooling.

## Adapted comparison models

The five comparison models use the same `[30, 3]` input and class protocol.
They are adapted implementations rather than complete reproductions of the
original papers' data pipelines or pretraining procedures.

| Model | Main configuration | Approx. parameters |
|---|---|---:|
| 30pktTCNET-adapted | `channels=300`, classifier width 300, depth 4 | 2.278M |
| NetMamba-adapted | `dim=292`, depth 4, AMP disabled | 2.294M |
| SRViT-adapted | `dim=192`, `mlp_ratio=3`, depth 4 | 2.204M |
| TrafficAudio-adapted | `dim=416`, CNN/BiGRU parallel paths | 2.211M |
| BPF-GNN-adapted | `dim=664`, graph depths `(1,2,1)` | 2.259M |

MVIF-Net has a larger parameter count because its branch gate, bounded residual
scales, and three-view fusion are part of the selected final structure. Actual
parameter counts are recorded in every result file.

## Numerical precision

Mamba selective blocks run in FP32 outside autocast. The surrounding MVIF-Net
operators and the adapted baselines use AMP where supported. NetMamba keeps
AMP disabled for its complete model.
