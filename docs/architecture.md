# HSTA-CM

HSTA-CM consumes the first 30 packets of each flow as a `[B, 30, 3]` tensor: packet size, direction, and inter-arrival time.

1. Three native PyTorch `Conv1d` layers encode local packet-position structure and add a projected residual from the input.
2. Two `mamba_ssm` Mamba blocks encode ordered temporal dependencies and add a residual from the temporal embedding.
3. Concatenated streams pass through a fully connected fusion layer and a sigmoid gate.
4. One `FlashSelfAttention` block calls PyTorch scaled dot-product attention with the Flash backend only. CPU, FP32, math, and memory-efficient fallbacks are rejected.
5. Layer normalization, mean pooling, and a 101-way head produce the 100 known classes plus `unknown`.

The open-set protocol maps held-out DataZoo applications and deterministic synthetic noise flows to `unknown`. The label encoder always keeps this class at index 100. Training, validation, and testing are disjoint date windows.

The comparison set is deliberately small: 30pktTCNET-adapted and NetMamba-adapted are the shared-input reference methods; SRViT, TrafficAudio, and BPF-GNN are the three retained recent baselines requested for the paper revision. GRU and the standalone Transformer are removed from the registry.
