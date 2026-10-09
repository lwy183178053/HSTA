"""HSTA-CM: Conv1d spatial encoder, Mamba temporal encoder and FlashAttention."""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTACM(nn.Module):
    """Open-set classifier for fixed 30-packet, three-feature flows.

    ``use_conv``, ``use_mamba`` and ``use_attention`` disable one component
    at a time for controlled ablations. The default keeps the full HSTA-CM
    architecture used by the main experiments.
    """

    layout = ("conv1d_x3_residual", "mamba_x2_residual", "fusion_fc", "flash_attention", "norm_head")

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 128,
        depth: int = 2,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        max_len: int = 30,
        pooling: str = "mean",
        conv_kernel_size: int = 3,
        use_conv: bool = True,
        use_mamba: bool = True,
        use_attention: bool = True,
        use_position: bool = True,
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0:
            raise ValueError("input_dim and num_classes must be positive")
        if conv_kernel_size % 2 != 1:
            raise ValueError("conv_kernel_size must be odd")
        if pooling not in {"mean", "last"}:
            raise ValueError("pooling must be mean or last")
        self.max_len = int(max_len)
        self.pooling = pooling
        self.use_conv = bool(use_conv)
        self.use_mamba = bool(use_mamba)
        self.use_attention = bool(use_attention)
        self.use_position = bool(use_position)
        layout = []
        if self.use_conv:
            layout.append("conv1d_x3_residual")
        if self.use_mamba:
            layout.append("mamba_x2_residual")
        layout.append("fusion_fc")
        if self.use_attention:
            layout.append("flash_attention")
        layout.append("norm_head")
        self.layout = tuple(layout)
        if self.use_conv:
            self.spatial = nn.Sequential(
                nn.Conv1d(input_dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
                nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
                nn.Conv1d(dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
                nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
                nn.Conv1d(dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
                nn.GELU(),
            )
            self.spatial_residual = nn.Conv1d(input_dim, dim, kernel_size=1)
        else:
            # Keep the branch width fixed while removing all spatial
            # operators from the no-conv ablation.
            self.spatial = None
            self.spatial_residual = None
        self.temporal_embed = nn.Linear(input_dim, dim) if self.use_mamba else None
        self.temporal = nn.ModuleList(
            [MambaBlock(dim, d_state=d_state, d_conv=d_conv, expand=expand, dropout=dropout) for _ in range(depth)]
        ) if self.use_mamba else nn.ModuleList()
        self.temporal_residual = nn.Identity() if self.use_mamba else None
        self.fusion_fc = nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.Dropout(dropout))
        self.gate = nn.Sequential(nn.Linear(dim * 2, dim), nn.Sigmoid())
        self.position = nn.Parameter(torch.zeros(1, self.max_len, dim))
        self.attention = (
            FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
            if self.use_attention
            else nn.Identity()
        )
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        nn.init.normal_(self.position, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        _, seq_len, _ = x.shape
        if seq_len > self.max_len:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.max_len}")
        x_channels = x.transpose(1, 2)
        if self.use_conv:
            spatial = self.spatial(x_channels) + self.spatial_residual(x_channels)
            spatial = spatial.transpose(1, 2)
        else:
            spatial = x.new_zeros(x.shape[0], seq_len, self.fusion_fc[0].in_features // 2)
        if self.use_mamba:
            # Mamba is order-aware by construction. Absolute positions are
            # injected after branch fusion so FlashAttention also receives
            # packet positions and the no-Mamba ablation remains well-defined.
            temporal_input = self.temporal_embed(x)
            temporal = temporal_input
            for block in self.temporal:
                temporal = block(temporal)
            temporal = temporal + self.temporal_residual(temporal_input)
        else:
            temporal = x.new_zeros(x.shape[0], seq_len, self.fusion_fc[0].in_features // 2)
        joined = torch.cat([spatial, temporal], dim=-1)
        gate = self.gate(joined)
        fused = self.fusion_fc(joined)
        fused = fused + gate * temporal + (1.0 - gate) * spatial
        if self.use_position:
            fused = fused + self.position[:, :seq_len]
        fused = self.attention(fused)
        fused = self.norm(fused)
        pooled = fused[:, -1] if self.pooling == "last" else fused.mean(dim=1)
        return self.head(pooled)
