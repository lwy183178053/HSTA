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
| Mamba | 2 directly stacked blocks; no branch residual | 30 | packet order and state dependency |
| Packet graph | 2 message-passing blocks; 1 bounded inter-layer residual | 30 | adjacent and feature-similarity packet relations |
| DFT-CNN | 1x1 projection, Conv1d kernels 1 and 3; 1 bounded inter-layer residual | 16 | local structure over rFFT frequency bins |
| Fusion | branch gate, token fusion, 1 masked SDPA Transformer block | 76 total | cross-view token interaction |

The Mamba path directly stacks two normalized Mamba mixers. Neither Mamba block
nor the Mamba branch has an added shortcut. The graph path has separate local
and nonlocal message projections. If `h0` is the graph embedding and `G1` and
`G2` are its message-passing blocks, the path is `G2(G1(h0) + alpha_g * h0)`.
This is the graph branch's only added residual; it is applied between the two
blocks. The learnable `alpha_g` starts at `0.1` and is bounded to `(0, 0.5)`.

The DFT path applies a 30-point rFFT along the packet axis, keeps the real and
imaginary parts of its 16 one-sided frequency bins, normalizes the resulting
six channels, and projects them to 256 dimensions with a `1x1` convolution. If
`f0` is that projected frequency input and `C1` and `C3` are the convolution
blocks, the path is `C3(C1(f0) + alpha_d * f0)`. This is the DFT-CNN branch's
only added residual; it is applied after the kernel-1 block and before the
kernel-3 block. Its independent learnable `alpha_d` also starts at `0.1` and is
bounded to `(0, 0.5)`. Neither branch adds another shortcut after its second
block.

The Mamba and packet-graph branches share a learned packet-position embedding;
the DFT branch uses a separate frequency-position embedding. Each branch gets
its own branch-type embedding. After adding these embeddings, each branch is
normalized. A masked mean of each branch produces its summary; an MLP and
Softmax produce three gate weights. Each branch's tokens are scaled by three
times its gate weight, then concatenated. The gate therefore acts before
concatenation and before cross-view attention.

The resulting `30 + 30 + 16 = 76` tokens pass through token fusion and one
four-head Transformer block implemented with PyTorch SDPA. The block uses
pre-normalization and has two residual additions:

```text
x1 = x + SelfAttention(LayerNorm(x), key_padding_mask)
x2 = x1 + FeedForward(LayerNorm(x1))
```

The attention key-padding mask prevents padded packet tokens from contributing
as keys. PyTorch selects the compatible SDPA backend automatically; the model
does not require a forced FlashAttention backend. Since attention mixes all
three views, the output is one contextual token sequence. A final LayerNorm
and one global masked mean pool all valid tokens together before the linear
classifier. The active configuration includes both open-set runs (61 outputs:
60 known classes plus unknown) and closed-set runs (60 outputs).

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
