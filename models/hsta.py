"""HSTA-CM: Conv1d spatial encoder, Mamba temporal encoder and FlashAttention."""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTA(nn.Module):
    """Open-set classifier for fixed 30-packet, three-feature flows."""

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
        self.spatial = nn.Sequential(
            nn.Conv1d(input_dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
            nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
            nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(dim, dim, kernel_size=conv_kernel_size, padding=conv_kernel_size // 2),
            nn.GELU(),
        )
        self.spatial_residual = nn.Conv1d(input_dim, dim, kernel_size=1)
        self.temporal_embed = nn.Linear(input_dim, dim)
        self.temporal = nn.ModuleList(
            [MambaBlock(dim, d_state=d_state, d_conv=d_conv, expand=expand, dropout=dropout) for _ in range(depth)]
        )
        self.temporal_residual = nn.Identity()
        self.fusion_fc = nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.Dropout(dropout))
        self.gate = nn.Sequential(nn.Linear(dim * 2, dim), nn.Sigmoid())
        self.position = nn.Parameter(torch.zeros(1, self.max_len, dim))
        self.attention = FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
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
        spatial = self.spatial(x_channels) + self.spatial_residual(x_channels)
        spatial = spatial.transpose(1, 2)
        temporal_input = self.temporal_embed(x) + self.position[:, :seq_len]
        temporal = temporal_input
        for block in self.temporal:
            temporal = block(temporal)
        temporal = temporal + self.temporal_residual(temporal_input)
        joined = torch.cat([spatial, temporal], dim=-1)
        gate = self.gate(joined)
        fused = self.fusion_fc(joined)
        fused = fused + gate * temporal + (1.0 - gate) * spatial
        fused = self.attention(fused)
        fused = self.norm(fused)
        pooled = fused[:, -1] if self.pooling == "last" else fused.mean(dim=1)
        return self.head(pooled)
