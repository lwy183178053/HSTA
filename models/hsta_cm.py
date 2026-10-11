"""HSTA-CM multi-view model: Mamba, packet graph, and DFT convolution."""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class PacketGraphBlock(nn.Module):
    """Residual message passing over local and feature-similarity relations."""

    def __init__(self, dim: int, dropout: float = 0.15):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.local_proj = nn.Linear(dim, dim)
        self.nonlocal_proj = nn.Linear(dim, dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, local_adj: torch.Tensor, nonlocal_adj: torch.Tensor) -> torch.Tensor:
        h = self.norm(x)
        local = torch.bmm(local_adj, h)
        nonlocal_msg = torch.bmm(nonlocal_adj, h)
        mixed = self.local_proj(local) + self.nonlocal_proj(nonlocal_msg)
        return x + self.drop(self.activation(mixed))


class HSTACM(nn.Module):
    """Three-view HSTA-CM with 30 + 30 + 16 = 76 tokens.

    The graph is built independently for each flow from its standardized
    packet features. It combines sequence-neighbour edges with four symmetric
    non-neighbour similarity edges per packet; no labels or cross-flow data are
    used. Separate switches support one-view-at-a-time ablations.
    """

    def __init__(
        self, input_dim: int, num_classes: int, dim: int = 256,
        depth: int = 2, heads: int = 4, mlp_ratio: int = 4,
        dropout: float = 0.15, d_state: int = 16, d_conv: int = 4,
        expand: int = 2, max_len: int = 30, use_mamba: bool = True,
        use_gnn: bool = True, use_dft: bool = True,
        use_attention: bool = True, graph_k: int = 4,
    ):
        super().__init__()
        if input_dim != 3 or max_len != 30 or depth != 2:
            raise ValueError("HSTA-CM requires three input features, 30 packets and two residual blocks")
        if not (use_mamba or use_gnn or use_dft):
            raise ValueError("at least one extraction view must remain")
        if graph_k <= 0 or graph_k >= max_len - 1:
            raise ValueError("graph_k must be between 1 and max_len - 2")
        self.dim, self.input_max_len = dim, max_len
        self.use_mamba, self.use_gnn, self.use_dft, self.use_attention = use_mamba, use_gnn, use_dft, use_attention
        self.graph_k = int(graph_k)
        self.register_buffer("padding_value", torch.zeros(input_dim))

        self.temporal_embed = nn.Linear(input_dim, dim) if use_mamba else None
        self.temporal = nn.ModuleList([
            MambaBlock(dim, d_state=d_state, d_conv=d_conv, expand=expand, dropout=dropout)
            for _ in range(depth)
        ]) if use_mamba else nn.ModuleList()
        self.temporal_norm = nn.LayerNorm(dim) if use_mamba else None

        self.graph_embed = nn.Linear(input_dim, dim) if use_gnn else None
        self.graph_blocks = nn.ModuleList(
            [PacketGraphBlock(dim, dropout=dropout) for _ in range(depth)]
        ) if use_gnn else nn.ModuleList()
        self.graph_norm = nn.LayerNorm(dim) if use_gnn else None

        self.dft_input_norm = nn.LayerNorm(input_dim * 2) if use_dft else None
        self.dft_residual = nn.Conv1d(input_dim * 2, dim, 1) if use_dft else None
        self.dft_spatial = self._conv_blocks(dim, dropout) if use_dft else None
        self.dft_norm = nn.LayerNorm(dim) if use_dft else None

        self.packet_position = nn.Parameter(torch.zeros(1, 30, dim))
        self.frequency_position = nn.Parameter(torch.zeros(1, 16, dim)) if use_dft else None
        # Stable semantic indices: 0=Mamba, 1=packet graph, 2=DFT Conv.
        self.branch_type = nn.Parameter(torch.zeros(3, dim))
        self.branch_names = tuple(name for enabled, name in (
            (use_mamba, "mamba"), (use_gnn, "packet_graph"), (use_dft, "dft_conv")
        ) if enabled)
        self.token_count = (30 if use_mamba else 0) + (30 if use_gnn else 0) + (16 if use_dft else 0)
        self.token_fusion = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
        self.attention = FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout) if use_attention else nn.Identity()
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        self.layout = tuple(
            (["mamba_x2_residual"] if use_mamba else [])
            + (["packet_graph_x2_residual_local_nonlocal"] if use_gnn else [])
            + (["dft_conv1d_1x3_residual"] if use_dft else [])
            + ["token_fusion"] + (["flash_attention"] if use_attention else []) + ["norm_head"]
        )
        for parameter in (self.packet_position, self.frequency_position, self.branch_type):
            if parameter is not None:
                nn.init.normal_(parameter, std=0.02)

    @staticmethod
    def _conv_blocks(dim: int, dropout: float) -> nn.ModuleList:
        return nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(dim, dim, kernel, padding=kernel // 2),
                nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
            ) for kernel in (1, 3)
        ])

    @torch.no_grad()
    def set_input_scaler(self, mean, scale) -> None:
        """Set the standardized raw-zero packet used for padding detection."""
        mean = torch.as_tensor(mean, dtype=torch.float32, device=self.padding_value.device)
        scale = torch.as_tensor(scale, dtype=torch.float32, device=self.padding_value.device)
        if mean.shape != (3,) or scale.shape != (3,) or not torch.isfinite(mean).all() or not torch.isfinite(scale).all() or (scale <= 0).any():
            raise ValueError("expected three finite means and positive scales")
        self.padding_value.copy_(-mean / scale)

    def _packet_mask(self, x: torch.Tensor) -> torch.Tensor:
        return ~torch.isclose(x.float(), self.padding_value, atol=1e-6, rtol=1e-5).all(dim=-1)

    @torch.no_grad()
    def _graph_adjacency(self, x: torch.Tensor, valid_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch, length, _ = x.shape
        with torch.autocast(device_type=x.device.type, enabled=False):
            idx = torch.arange(length, device=x.device)
            separation = (idx[:, None] - idx[None, :]).abs()
            valid_pairs = valid_mask.unsqueeze(-1) & valid_mask.unsqueeze(-2)
            local = ((separation <= 1).unsqueeze(0) & valid_pairs).float()
            distances = (x.float().unsqueeze(2) - x.float().unsqueeze(1)).square().sum(-1)
            allowed = (separation > 1).unsqueeze(0) & valid_pairs
            distances = distances.masked_fill(~allowed, float("inf"))
            nearest = distances.argsort(dim=-1, stable=True)[..., :self.graph_k]
            weights = 1.0 / (1.0 + distances.gather(-1, nearest))
            nonlocal_adj = torch.zeros_like(distances).scatter_(-1, nearest, weights)
            nonlocal_adj = torch.maximum(nonlocal_adj, nonlocal_adj.transpose(1, 2))
            return self._normalize_adjacency(local), self._normalize_adjacency(nonlocal_adj)

    @staticmethod
    def _normalize_adjacency(adjacency: torch.Tensor) -> torch.Tensor:
        degree = adjacency.sum(dim=-1).clamp_min(1e-6)
        inv_sqrt = degree.rsqrt()
        return inv_sqrt.unsqueeze(-1) * adjacency * inv_sqrt.unsqueeze(-2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (30, 3):
            raise ValueError(f"expected [batch, 30, 3], got {tuple(x.shape)}")
        valid = self._packet_mask(x)
        packet_weight = valid.unsqueeze(-1)
        x = x.masked_fill(~packet_weight, 0)
        tokens, lengths, masks = [], [], []
        if self.use_mamba:
            temporal_input = self.temporal_embed(x) * packet_weight
            temporal = temporal_input
            for block in self.temporal:
                temporal = block(temporal) * packet_weight
            temporal = self.temporal_norm(temporal + temporal_input)
            tokens.append((temporal + self.packet_position + self.branch_type[0]) * packet_weight)
            lengths.append(30)
            masks.append(valid)
        if self.use_gnn:
            local_adj, nonlocal_adj = self._graph_adjacency(x, valid)
            graph = self.graph_embed(x) * packet_weight
            local_adj = local_adj.to(dtype=graph.dtype)
            nonlocal_adj = nonlocal_adj.to(dtype=graph.dtype)
            for block in self.graph_blocks:
                graph = block(graph, local_adj, nonlocal_adj) * packet_weight
            graph = self.graph_norm(graph)
            tokens.append((graph + self.packet_position + self.branch_type[1]) * packet_weight)
            lengths.append(30)
            masks.append(valid)
        if self.use_dft:
            spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
            features = self.dft_input_norm(torch.cat((spectrum.real, spectrum.imag), dim=-1))
            frequency = self.dft_residual(features.transpose(1, 2))
            for block in self.dft_spatial:
                frequency = frequency + block(frequency)
            frequency = self.dft_norm(frequency.transpose(1, 2))
            tokens.append(frequency + self.frequency_position + self.branch_type[2])
            lengths.append(16)
            masks.append(torch.ones(x.shape[0], 16, dtype=torch.bool, device=x.device))
        token_mask = torch.cat(masks, dim=1).unsqueeze(-1)
        projected = self.token_fusion(torch.cat(tokens, dim=1)) * token_mask
        fused = self.norm(self.attention(projected))
        pooled = torch.stack([
            (chunk * mask.unsqueeze(-1)).sum(dim=1) / mask.sum(dim=1, keepdim=True).clamp_min(1)
            for chunk, mask in zip(torch.split(fused, lengths, dim=1), masks)
        ]).mean(dim=0)
        return self.head(pooled)
