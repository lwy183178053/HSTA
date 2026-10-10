from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .flash_attention import FlashSelfAttention


SRVIT_ADAPTED_NOTE = (
    "SRViT-adapted: multi-scale packet Conv1d front-end and FlashAttention "
    "under the shared [30, 3] packet representation; this is not the original image/byte pipeline."
)
TRAFFICAUDIO_ADAPTED_NOTE = (
    "TrafficAudio-adapted: MFCC-style encoding of the three standardized packet "
    "features under the shared [30, 3] packet representation; the input is not raw audio."
)
BPF_GNN_ADAPTED_NOTE = (
    "BPF-GNN-adapted: feature-to-packet-to-flow dense graph hierarchy under the "
    "shared [30, 3] packet representation; original side information and edge features are unavailable."
)


class FlashPositionSelfAttention(nn.Module):
    """FlashAttention wrapper used by the SRViT-adapted reconstruction.

    This project requires PyTorch FlashAttention only. Packet positions are
    injected by the learned embedding in ``SRViT`` before this module.
    """

    def __init__(self, dim: int, heads: int, max_len: int, dropout: float):
        super().__init__()
        if dim % heads != 0:
            raise ValueError(f"dim={dim} must be divisible by heads={heads}")
        self.heads = heads
        self.head_dim = dim // heads
        self.max_len = max_len
        self.flash = FlashSelfAttention(dim, heads=heads, dropout=dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, seq_len, _ = x.shape
        if seq_len > self.max_len:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.max_len}")
        return self.flash(x)


class SRViTBlock(nn.Module):
    def __init__(self, dim: int, heads: int, max_len: int, mlp_ratio: int, dropout: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = FlashPositionSelfAttention(dim, heads, max_len, dropout)
        self.norm2 = nn.LayerNorm(dim)
        hidden = dim * mlp_ratio
        self.ffn = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        return x + self.ffn(self.norm2(x))


class SRViT(nn.Module):
    """Unified-input reconstruction of SRViT's multi-scale ViT backbone."""

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 256,
        depth: int = 4,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.15,
        max_len: int = 30,
        patch_kernel_sizes: tuple[int, ...] = (3, 5, 7),
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0 or dim <= 0 or max_len <= 0:
            raise ValueError("input_dim, num_classes, dim, and max_len must be positive")
        self.patch_kernel_sizes = tuple(int(k) for k in patch_kernel_sizes)
        if any(k <= 0 or k % 2 == 0 for k in self.patch_kernel_sizes):
            raise ValueError("SRViT patch kernels must be positive odd integers")
        self.adapted_note = SRVIT_ADAPTED_NOTE
        self.embed = nn.Linear(input_dim, dim)
        self.patch_branches = nn.ModuleList(
            [nn.Conv1d(dim, dim, kernel_size=k, padding=k // 2) for k in self.patch_kernel_sizes]
        )
        self.patch_fusion = nn.Sequential(
            nn.Conv1d(dim * len(self.patch_kernel_sizes), dim, kernel_size=1),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.blocks = nn.ModuleList(
            [SRViTBlock(dim, heads, max_len, mlp_ratio, dropout) for _ in range(depth)]
        )
        self.position = nn.Parameter(torch.zeros(1, max_len, dim))
        nn.init.normal_(self.position, std=0.02)
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Sequential(
            nn.Linear(dim, dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        _, seq_len, feature_dim = x.shape
        if feature_dim != self.embed.in_features:
            raise ValueError(f"expected feature_dim={self.embed.in_features}, got {feature_dim}")
        if seq_len > self.position.shape[1]:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.position.shape[1]}")
        x = self.embed(x).transpose(1, 2)
        x = self.patch_fusion(torch.cat([branch(x) for branch in self.patch_branches], dim=1))
        x = x.transpose(1, 2) + self.position[:, :seq_len]
        for block in self.blocks:
            x = block(x)
        return self.head(self.norm(x).mean(dim=1))


def _triangular_filterbank(n_filters: int, n_bins: int) -> torch.Tensor:
    coordinates = torch.arange(n_bins, dtype=torch.float32)
    centers = torch.linspace(0, n_bins - 1, n_filters + 2)
    filters = []
    for index in range(n_filters):
        left, center, right = centers[index : index + 3]
        rising = (coordinates - left) / (center - left).clamp_min(1e-6)
        falling = (right - coordinates) / (right - center).clamp_min(1e-6)
        filters.append(torch.minimum(rising, falling).clamp_min(0.0))
    matrix = torch.stack(filters)
    return matrix / matrix.sum(dim=1, keepdim=True).clamp_min(1e-6)


def _dct_matrix(n_mfcc: int, n_mels: int) -> torch.Tensor:
    mel = torch.arange(n_mels, dtype=torch.float32) + 0.5
    cepstral = torch.arange(n_mfcc, dtype=torch.float32).unsqueeze(1)
    matrix = torch.cos(math.pi * cepstral * mel / n_mels)
    matrix[0] *= math.sqrt(1.0 / n_mels)
    if n_mfcc > 1:
        matrix[1:] *= math.sqrt(2.0 / n_mels)
    return matrix


class PacketMFCC(nn.Module):
    def __init__(
        self,
        n_fft: int = 32,
        win_length: int = 32,
        hop_length: int = 8,
        n_mels: int = 16,
        n_mfcc: int = 8,
    ):
        super().__init__()
        if n_fft <= 0 or win_length <= 0 or hop_length <= 0:
            raise ValueError("n_fft, win_length, and hop_length must be positive")
        if win_length > n_fft:
            raise ValueError("win_length must not exceed n_fft")
        if n_mels <= 0 or n_mfcc <= 0 or n_mels > n_fft // 2 + 1:
            raise ValueError("n_mels must be in [1, n_fft // 2 + 1] and n_mfcc must be positive")
        self.n_fft = n_fft
        self.win_length = win_length
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.n_mfcc = n_mfcc
        self.register_buffer("window", torch.hann_window(win_length), persistent=False)
        self.register_buffer(
            "mel_filterbank",
            _triangular_filterbank(n_mels, n_fft // 2 + 1),
            persistent=False,
        )
        self.register_buffer("dct", _dct_matrix(n_mfcc, n_mels), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        # This is an explicit lightweight adaptation: the three standardized
        # packet features are serialized as a pseudo-waveform.  It is not raw
        # audio and is reported as TrafficAudio-adapted.
        waveform = x.reshape(x.shape[0], -1).float()
        waveform = waveform - waveform.mean(dim=1, keepdim=True)
        waveform = waveform / waveform.std(dim=1, keepdim=True, unbiased=False).clamp_min(1e-5)
        spectrum = torch.stft(
            waveform,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            win_length=self.win_length,
            window=self.window.to(device=waveform.device, dtype=waveform.dtype),
            center=True,
            return_complex=True,
        )
        power = spectrum.abs().square()
        mel = torch.einsum("mf,bft->bmt", self.mel_filterbank.to(power), power)
        features = torch.einsum("cm,bmt->bct", self.dct.to(mel), mel.clamp_min(1e-6).log())
        return features.to(dtype=x.dtype)


class TrafficAudio(nn.Module):
    """Unified-input reconstruction of TrafficAudio's MFCC CNN-BiGRU path."""

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 256,
        dropout: float = 0.15,
        n_fft: int = 32,
        win_length: int = 32,
        hop_length: int = 8,
        n_mels: int = 16,
        n_mfcc: int = 8,
    ):
        super().__init__()
        if input_dim != 3:
            raise ValueError("TrafficAudio-adapted expects the shared three-feature packet input")
        if num_classes <= 0 or dim <= 0:
            raise ValueError("num_classes and dim must be positive")
        self.adapted_note = TRAFFICAUDIO_ADAPTED_NOTE
        self.input_dim = input_dim
        self.mfcc = PacketMFCC(n_fft, win_length, hop_length, n_mels, n_mfcc)
        mid = max(dim // 2, 16)
        self.cnn = nn.Sequential(
            nn.Conv1d(n_mfcc, mid, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv1d(mid, dim, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv1d(dim, dim, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.gru = nn.GRU(
            input_size=n_mfcc,
            hidden_size=max(dim // 2, 1),
            num_layers=2,
            dropout=dropout,
            bidirectional=True,
            batch_first=True,
        )
        recurrent_dim = 2 * max(dim // 2, 1)
        self.head = nn.Sequential(
            nn.Linear(dim + recurrent_dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[-1] != self.input_dim:
            raise ValueError(
                f"expected [batch, sequence, {self.input_dim}], got {tuple(x.shape)}"
            )
        mfcc = self.mfcc(x)
        local = self.cnn(mfcc).mean(dim=-1)
        temporal, _ = self.gru(mfcc.transpose(1, 2))
        return self.head(torch.cat([local, temporal.mean(dim=1)], dim=-1))


class DenseGraphConv(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.proj = nn.Linear(dim, dim)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        degree = adjacency.sum(dim=-1).clamp_min(1.0)
        scale = degree.rsqrt()
        normalized = scale.unsqueeze(-1) * adjacency * scale.unsqueeze(-2)
        return self.proj(torch.bmm(normalized, x))


class ResidualGraphBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.conv = DenseGraphConv(dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        return x + self.dropout(F.gelu(self.conv(self.norm(x), adjacency)))


class BPFGNN(nn.Module):
    """Feature-Packet-Flow reconstruction of BPF-GNN for side-channel inputs."""

    hierarchy = ("feature", "packet", "flow")

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 256,
        dropout: float = 0.15,
        top_k: int = 4,
        num_subflows: int = 5,
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0 or dim <= 0:
            raise ValueError("input_dim, num_classes, and dim must be positive")
        if top_k < 0 or num_subflows <= 0:
            raise ValueError("top_k must be non-negative and num_subflows must be positive")
        self.input_dim = input_dim
        self.top_k = int(top_k)
        self.num_subflows = int(num_subflows)
        self.adapted_note = BPF_GNN_ADAPTED_NOTE
        self.scalar_proj = nn.Linear(1, dim)
        self.feature_type = nn.Parameter(torch.zeros(1, 1, input_dim, dim))
        self.feature_blocks = nn.ModuleList([ResidualGraphBlock(dim, dropout) for _ in range(2)])
        self.packet_blocks = nn.ModuleList([ResidualGraphBlock(dim, dropout) for _ in range(2)])
        self.flow_blocks = nn.ModuleList([ResidualGraphBlock(dim, dropout) for _ in range(2)])
        self.pool_score = nn.Linear(dim, 1)
        self.head = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, num_classes),
        )
        nn.init.normal_(self.feature_type, std=0.02)

    @staticmethod
    def _chain_adjacency(batch: int, nodes: int, device, dtype) -> torch.Tensor:
        adjacency = torch.eye(nodes, device=device, dtype=dtype)
        if nodes > 1:
            idx = torch.arange(nodes - 1, device=device)
            adjacency[idx, idx + 1] = 1
            adjacency[idx + 1, idx] = 1
        return adjacency.unsqueeze(0).expand(batch, -1, -1).clone()

    def build_packet_adjacency(self, packet_features: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = packet_features.shape
        adjacency = self._chain_adjacency(
            batch, seq_len, packet_features.device, packet_features.dtype
        )
        if seq_len <= 1 or self.top_k <= 0:
            return adjacency
        similarity = torch.bmm(
            F.normalize(packet_features, dim=-1),
            F.normalize(packet_features, dim=-1).transpose(1, 2),
        )
        similarity = similarity.masked_fill(
            torch.eye(seq_len, device=similarity.device, dtype=torch.bool).unsqueeze(0),
            float("-inf"),
        )
        neighbors = similarity.topk(min(self.top_k, seq_len - 1), dim=-1).indices
        dynamic = torch.zeros_like(adjacency).scatter(-1, neighbors, 1.0)
        return torch.maximum(adjacency, torch.maximum(dynamic, dynamic.transpose(1, 2)))

    def _subflow_pool(self, packet_features: torch.Tensor) -> torch.Tensor:
        sections = min(self.num_subflows, packet_features.shape[1])
        chunks = torch.tensor_split(packet_features, sections, dim=1)
        return torch.stack([chunk.mean(dim=1) for chunk in chunks], dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        batch, seq_len, feature_dim = x.shape
        if feature_dim != self.input_dim:
            raise ValueError(f"expected feature_dim={self.input_dim}, got {feature_dim}")
        if seq_len <= 0:
            raise ValueError("sequence length must be positive")
        features = self.scalar_proj(x.unsqueeze(-1)) + self.feature_type
        features = features.view(batch * seq_len, self.input_dim, -1)
        feature_adj = torch.ones(
            batch * seq_len, self.input_dim, self.input_dim, device=x.device, dtype=x.dtype
        )
        for block in self.feature_blocks:
            features = block(features, feature_adj)
        packets = features.mean(dim=1).view(batch, seq_len, -1)
        packet_adj = self.build_packet_adjacency(packets)
        for block in self.packet_blocks:
            packets = block(packets, packet_adj)
        flows = self._subflow_pool(packets)
        flow_adj = self._chain_adjacency(batch, flows.shape[1], x.device, x.dtype)
        for block in self.flow_blocks:
            flows = block(flows, flow_adj)
        weights = self.pool_score(flows).softmax(dim=1)
        return self.head((weights * flows).sum(dim=1))
