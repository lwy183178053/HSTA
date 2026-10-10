"""HSTA-CM and configurable multi-branch candidates.

The default constructor remains the two-branch HSTA-CM used by the current
benchmark.  Candidate configurations can add progressive convolution kernels
and a frequency-token branch without changing the default model contract.
"""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTACM(nn.Module):
    """Open-set classifier for fixed 30-packet, three-feature flows.

    ``use_conv``, ``use_mamba`` and ``use_attention`` disable one component
    at a time for controlled ablations. ``fusion_mode="tokens"`` is used by
    the DFT candidates: packet and frequency tokens are kept at their native
    lengths and receive separate position and branch-type embeddings before
    FlashAttention.
    """

    layout = ("conv1d_x3_residual", "mamba_x2_residual", "fusion_fc", "flash_attention", "norm_head")

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 256,
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
        conv_kernel_schedule: tuple[int, ...] | list[int] | None = None,
        dft_conv_kernel_schedule: tuple[int, ...] | list[int] | None = None,
        use_dft: bool = False,
        fusion_mode: str = "aligned",
        use_packet_position: bool = False,
        use_frequency_position: bool = False,
        use_branch_type: bool = False,
        input_max_len: int | None = None,
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0:
            raise ValueError("input_dim and num_classes must be positive")
        if conv_kernel_size % 2 != 1:
            raise ValueError("conv_kernel_size must be odd")
        if pooling not in {"mean", "last", "branch_mean"}:
            raise ValueError("pooling must be mean, last, or branch_mean")
        if fusion_mode not in {"aligned", "tokens"}:
            raise ValueError("fusion_mode must be aligned or tokens")
        if use_dft and fusion_mode != "tokens":
            raise ValueError("use_dft requires fusion_mode='tokens'")
        self.max_len = int(max_len)
        self.input_max_len = int(input_max_len or (30 if use_dft else max_len))
        self.dim = int(dim)
        self.pooling = pooling
        self.use_conv = bool(use_conv)
        self.use_mamba = bool(use_mamba)
        self.use_attention = bool(use_attention)
        self.use_position = bool(use_position)
        self.use_dft = bool(use_dft)
        self.fusion_mode = str(fusion_mode)
        self.use_packet_position = bool(use_packet_position)
        self.use_frequency_position = bool(use_frequency_position or use_dft)
        self.use_branch_type = bool(use_branch_type or use_dft)
        self.conv_kernel_schedule = self._validate_kernel_schedule(conv_kernel_schedule, conv_kernel_size)
        self.dft_conv_kernel_schedule = self._validate_kernel_schedule(
            dft_conv_kernel_schedule,
            conv_kernel_size,
        )
        layout = []
        if self.use_conv:
            conv_layout = "conv1d_x3_residual" if self.conv_kernel_schedule == (3, 3, 3) else (
                "conv1d_" + "x".join(str(k) for k in self.conv_kernel_schedule) + "_residual"
            )
            layout.append(conv_layout)
        if self.use_mamba:
            layout.append("mamba_x2_residual")
        if self.use_dft:
            layout.append("dft_rfft_" + "x".join(str(k) for k in self.dft_conv_kernel_schedule) + "_residual")
        layout.append("fusion_fc" if self.fusion_mode == "aligned" else "token_fusion")
        if self.use_attention:
            layout.append("flash_attention")
        layout.append("norm_head")
        self.layout = tuple(layout)
        if self.use_conv:
            self.spatial = self._make_conv_blocks(dim, self.conv_kernel_schedule, dropout)
            self.spatial_residual = nn.Conv1d(input_dim, dim, kernel_size=1)
        else:
            # Keep the branch width fixed while removing all spatial
            # operators from the no-conv ablation.
            self.spatial = None
            self.spatial_residual = None
        if self.use_dft:
            self.dft_input_norm = nn.LayerNorm(input_dim * 2)
            self.dft_spatial = self._make_conv_blocks(dim, self.dft_conv_kernel_schedule, dropout)
            self.dft_residual = nn.Conv1d(input_dim * 2, dim, kernel_size=1)
        else:
            self.dft_input_norm = None
            self.dft_spatial = None
            self.dft_residual = None
        self.temporal_embed = nn.Linear(input_dim, dim) if self.use_mamba else None
        self.temporal = nn.ModuleList(
            [MambaBlock(dim, d_state=d_state, d_conv=d_conv, expand=expand, dropout=dropout) for _ in range(depth)]
        ) if self.use_mamba else nn.ModuleList()
        self.temporal_residual = nn.Identity() if self.use_mamba else None
        self.spatial_norm = nn.LayerNorm(dim) if self.use_conv else None
        self.temporal_norm = nn.LayerNorm(dim) if self.use_mamba else None
        self.fusion_fc = (
            nn.Sequential(nn.Linear(dim * 2, dim), nn.GELU(), nn.Dropout(dropout))
            if self.fusion_mode == "aligned" else None
        )
        self.gate = (
            nn.Sequential(nn.Linear(dim * 2, dim), nn.Sigmoid())
            if self.fusion_mode == "aligned" else None
        )
        self.token_fusion = (
            nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
            if self.fusion_mode == "tokens" else None
        )
        self.position = (
            nn.Parameter(torch.zeros(1, self.max_len, dim))
            if not self.use_packet_position else None
        )
        self.packet_position = (
            nn.Parameter(torch.zeros(1, self.input_max_len, dim))
            if self.use_packet_position else None
        )
        self.frequency_position = (
            nn.Parameter(torch.zeros(1, self.input_max_len // 2 + 1, dim))
            if self.use_frequency_position else None
        )
        self.branch_names = tuple(
            name for enabled, name in (
                (self.use_mamba, "mamba"),
                (self.use_conv, "raw_conv"),
                (self.use_dft, "dft_conv"),
            ) if enabled
        )
        self.branch_type = (
            nn.Parameter(torch.zeros(len(self.branch_names), dim))
            if self.use_branch_type else None
        )
        self.attention = (
            FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
            if self.use_attention
            else nn.Identity()
        )
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        for parameter in (self.position, self.packet_position, self.frequency_position, self.branch_type):
            if parameter is not None:
                nn.init.normal_(parameter, std=0.02)

    @staticmethod
    def _validate_kernel_schedule(schedule, fallback: int) -> tuple[int, ...]:
        values = (fallback,) * 3 if schedule is None else tuple(int(value) for value in schedule)
        if not values or any(value <= 0 or value % 2 == 0 for value in values):
            raise ValueError("convolution kernel schedule must contain positive odd values")
        return values

    @staticmethod
    def _make_conv_blocks(dim: int, schedule: tuple[int, ...], dropout: float) -> nn.ModuleList:
        return nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(dim, dim, kernel_size=kernel, padding=kernel // 2),
                    nn.BatchNorm1d(dim), nn.GELU(), nn.Dropout(dropout),
                )
                for kernel in schedule
            ]
        )

    def _add_branch_encoding(self, tokens: torch.Tensor, branch_name: str, position: torch.Tensor | None):
        if position is not None:
            tokens = tokens + position[:, :tokens.shape[1]]
        if self.branch_type is not None:
            branch_index = self.branch_names.index(branch_name)
            tokens = tokens + self.branch_type[branch_index].view(1, 1, -1)
        return tokens

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        _, seq_len, _ = x.shape
        if seq_len > self.input_max_len:
            raise ValueError(f"seq_len={seq_len} exceeds input_max_len={self.input_max_len}")
        x_channels = x.transpose(1, 2)
        if self.use_conv:
            spatial = self.spatial_residual(x_channels)
            for block in self.spatial:
                spatial = spatial + block(spatial)
            spatial = spatial.transpose(1, 2)
            spatial = self.spatial_norm(spatial)
        else:
            spatial = x.new_zeros(x.shape[0], seq_len, self.dim)
        if self.use_mamba:
            # Mamba is order-aware by construction. Absolute positions are
            # injected after branch fusion so FlashAttention also receives
            # packet positions and the no-Mamba ablation remains well-defined.
            temporal_input = self.temporal_embed(x)
            temporal = temporal_input
            for block in self.temporal:
                temporal = block(temporal)
            temporal = temporal + self.temporal_residual(temporal_input)
            temporal = self.temporal_norm(temporal)
        else:
            temporal = x.new_zeros(x.shape[0], seq_len, self.dim)
        dft = None
        if self.use_dft:
            spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
            dft_features = torch.cat((spectrum.real, spectrum.imag), dim=-1)
            dft_features = self.dft_input_norm(dft_features)
            dft = self.dft_residual(dft_features.transpose(1, 2))
            for block in self.dft_spatial:
                dft = dft + block(dft)
            dft = dft.transpose(1, 2)
            dft = self._add_branch_encoding(dft, "dft_conv", self.frequency_position)

        if self.fusion_mode == "tokens":
            tokens = []
            if self.use_mamba:
                tokens.append(self._add_branch_encoding(temporal, "mamba", self.packet_position))
            if self.use_conv:
                tokens.append(self._add_branch_encoding(spatial, "raw_conv", self.packet_position))
            if dft is not None:
                tokens.append(dft)
            if not tokens:
                raise ValueError("token fusion requires at least one active branch")
            fused = self.token_fusion(torch.cat(tokens, dim=1))
        else:
            if self.use_packet_position:
                if self.use_conv:
                    spatial = self._add_branch_encoding(spatial, "raw_conv", self.packet_position)
                if self.use_mamba:
                    temporal = self._add_branch_encoding(temporal, "mamba", self.packet_position)
            joined = torch.cat([spatial, temporal], dim=-1)
            gate = self.gate(joined)
            fused = self.fusion_fc(joined)
            fused = fused + gate * temporal + (1.0 - gate) * spatial
            if self.use_position and self.position is not None:
                fused = fused + self.position[:, :seq_len]
        fused = self.attention(fused)
        fused = self.norm(fused)
        if self.fusion_mode == "tokens" and self.pooling == "branch_mean":
            lengths = []
            if self.use_mamba:
                lengths.append(seq_len)
            if self.use_conv:
                lengths.append(seq_len)
            if self.use_dft:
                lengths.append(seq_len // 2 + 1)
            chunks = torch.split(fused, lengths, dim=1)
            pooled = torch.stack([chunk.mean(dim=1) for chunk in chunks], dim=1).mean(dim=1)
        else:
            pooled = fused[:, -1] if self.pooling == "last" else fused.mean(dim=1)
        return self.head(pooled)
