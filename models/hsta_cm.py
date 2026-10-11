"""三路 HSTA-CM：Mamba 时序、包域残差卷积和 DFT 频域残差卷积。"""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTACM(nn.Module):
    """30 + 30 + 16 个 token，三种编码；开关仅用于组件消融。"""

    def __init__(self, input_dim: int, num_classes: int, dim: int = 256,
                 depth: int = 2, heads: int = 4, mlp_ratio: int = 4,
                 dropout: float = 0.15, d_state: int = 16, d_conv: int = 4,
                 expand: int = 2, max_len: int = 30,
                 use_conv: bool = True, use_mamba: bool = True,
                 use_attention: bool = True):
        super().__init__()
        if input_dim != 3 or max_len != 30 or depth != 2:
            raise ValueError("HSTA-CM requires three input features, 30 packets and two Mamba layers")
        if not (use_conv or use_mamba):
            raise ValueError("at least one extraction component must remain")
        self.dim, self.input_max_len = dim, max_len
        self.use_conv, self.use_mamba, self.use_attention = use_conv, use_mamba, use_attention
        self.conv_kernel_schedule = self.dft_conv_kernel_schedule = (1, 3, 5)
        self.spatial_residual = nn.Conv1d(input_dim, dim, 1) if use_conv else None
        self.spatial = self._conv_blocks(dim, dropout) if use_conv else None
        self.spatial_norm = nn.LayerNorm(dim) if use_conv else None
        self.dft_input_norm = nn.LayerNorm(input_dim * 2) if use_conv else None
        self.dft_residual = nn.Conv1d(input_dim * 2, dim, 1) if use_conv else None
        self.dft_spatial = self._conv_blocks(dim, dropout) if use_conv else None
        self.temporal_embed = nn.Linear(input_dim, dim) if use_mamba else None
        self.temporal = nn.ModuleList([
            MambaBlock(dim, d_state=d_state, d_conv=d_conv, expand=expand, dropout=dropout)
            for _ in range(depth)
        ]) if use_mamba else nn.ModuleList()
        self.temporal_norm = nn.LayerNorm(dim) if use_mamba else None
        self.packet_position = nn.Parameter(torch.zeros(1, 30, dim))
        self.frequency_position = nn.Parameter(torch.zeros(1, 16, dim)) if use_conv else None
        # Stable semantic indices even when a branch is removed:
        # 0=Mamba, 1=raw Conv1d, 2=DFT Conv1d.
        self.branch_type = nn.Parameter(torch.zeros(3, dim))
        self.branch_names = tuple(name for enabled, name in (
            (use_mamba, "mamba"), (use_conv, "raw_conv"), (use_conv, "dft_conv")
        ) if enabled)
        self.token_count = (30 if use_mamba else 0) + (46 if use_conv else 0)
        self.token_fusion = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
        self.attention = FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout) if use_attention else nn.Identity()
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        self.layout = tuple(
            (["mamba_x2_residual"] if use_mamba else [])
            + (["raw_conv1d_1x3x5_residual", "dft_conv1d_1x3x5_residual"] if use_conv else [])
            + ["token_fusion"] + (["flash_attention"] if use_attention else []) + ["norm_head"]
        )
        for parameter in (self.packet_position, self.frequency_position, self.branch_type):
            if parameter is not None:
                nn.init.normal_(parameter, std=0.02)

    @staticmethod
    def _conv_blocks(dim: int, dropout: float) -> nn.ModuleList:
        return nn.ModuleList([
            nn.Sequential(nn.Conv1d(dim, dim, kernel, padding=kernel // 2),
                          nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout))
            for kernel in (1, 3, 5)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (30, 3):
            raise ValueError(f"expected [batch, 30, 3], got {tuple(x.shape)}")
        tokens, lengths = [], []
        if self.use_mamba:
            temporal_input = self.temporal_embed(x)
            temporal = temporal_input
            for block in self.temporal:
                temporal = block(temporal)
            temporal = self.temporal_norm(temporal + temporal_input)
            tokens.append(temporal + self.packet_position + self.branch_type[0])
            lengths.append(30)
        if self.use_conv:
            spatial = self.spatial_residual(x.transpose(1, 2))
            for block in self.spatial:
                spatial = spatial + block(spatial)
            spatial = self.spatial_norm(spatial.transpose(1, 2))
            tokens.append(spatial + self.packet_position + self.branch_type[1])
            lengths.append(30)
            spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
            features = self.dft_input_norm(torch.cat((spectrum.real, spectrum.imag), dim=-1))
            frequency = self.dft_residual(features.transpose(1, 2))
            for block in self.dft_spatial:
                frequency = frequency + block(frequency)
            tokens.append(frequency.transpose(1, 2) + self.frequency_position + self.branch_type[2])
            lengths.append(16)
        fused = self.norm(self.attention(self.token_fusion(torch.cat(tokens, dim=1))))
        # Match the selected full candidate: equal weight for each branch,
        # rather than overweighting 30-packet branches relative to 16 frequencies.
        pooled = torch.stack([chunk.mean(dim=1) for chunk in torch.split(fused, lengths, dim=1)]).mean(dim=0)
        return self.head(pooled)
