"""HSTA-CM-DFT: temporal Mamba plus frequency-domain Conv1d branches.

The input remains a packet sequence ``[batch, sequence, feature]``.  The
frequency branch applies a one-sided real FFT along the packet axis and models
adjacent frequency bins with ordinary PyTorch ``Conv1d`` layers. Screening
variants can retain rectangular real/imaginary components, keep all frequency
bins as attention tokens, or add a raw-packet Conv1d stream.
"""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTACMDFT(nn.Module):
    """Open-set classifier with configurable DFT/Conv1d fusion.

    ``HSTACMDFT`` is the main model variant.  ``HSTACM`` is retained as the
    matched no-DFT ablation with the same residual branch depth and width.
    """

    layout = (
        "rfft_frequency_encoding",
        "magnitude_conv1d_x3_frequency_residual_kernel_3",
        "mamba_x2_residual",
        "fusion_fc",
        "flash_attention",
        "norm_head",
    )

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
        use_attention: bool = True,
        use_position: bool = True,
        frequency_representation: str = "magnitude",
        fusion_mode: str = "pooled",
        use_raw_conv: bool = False,
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0:
            raise ValueError("input_dim and num_classes must be positive")
        if depth <= 0:
            raise ValueError("depth must be positive")
        if max_len < 3:
            raise ValueError("max_len must be at least 3 for the frequency kernel")
        if pooling not in {"mean", "last", "temporal_mean"}:
            raise ValueError("pooling must be mean, last or temporal_mean")
        if frequency_representation not in {"magnitude", "real_imag"}:
            raise ValueError("frequency_representation must be magnitude or real_imag")
        if fusion_mode not in {"pooled", "tokens"}:
            raise ValueError("fusion_mode must be pooled or tokens")
        if use_raw_conv and fusion_mode != "tokens":
            raise ValueError("use_raw_conv requires fusion_mode='tokens'")

        self.input_dim = int(input_dim)
        self.dim = int(dim)
        self.max_len = int(max_len)
        self.pooling = pooling
        self.use_attention = bool(use_attention)
        self.use_position = bool(use_position)
        self.frequency_representation = str(frequency_representation)
        self.fusion_mode = str(fusion_mode)
        self.use_raw_conv = bool(use_raw_conv)
        frequency_input_dim = input_dim if self.frequency_representation == "magnitude" else input_dim * 2

        # The FFT magnitude keeps the three original packet feature channels;
        # no real/imaginary or amplitude/phase channel expansion is used.
        # Each of the three Conv1d layers has its own residual connection.
        self.frequency = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(dim, dim, kernel_size=3, padding=1),
                    nn.BatchNorm1d(dim),
                    nn.GELU(),
                    nn.Dropout1d(dropout),
                )
                for _ in range(3)
            ]
        )
        self.frequency_residual = nn.Conv1d(frequency_input_dim, dim, kernel_size=1)
        self.frequency_pool = nn.AdaptiveAvgPool1d(1)

        self.temporal_embed = nn.Linear(input_dim, dim)
        self.temporal = nn.ModuleList(
            [
                MambaBlock(
                    dim,
                    d_state=d_state,
                    d_conv=d_conv,
                    expand=expand,
                    dropout=dropout,
                )
                for _ in range(depth)
            ]
        )
        self.temporal_residual = nn.Identity()
        self.frequency_norm = nn.LayerNorm(dim)
        self.temporal_norm = nn.LayerNorm(dim)
        if self.use_raw_conv:
            self.raw_conv = nn.ModuleList(
                [
                    nn.Sequential(
                        nn.Conv1d(dim, dim, kernel_size=3, padding=1),
                        nn.BatchNorm1d(dim),
                        nn.GELU(),
                        nn.Dropout1d(dropout),
                    )
                    for _ in range(3)
                ]
            )
            self.raw_residual = nn.Conv1d(input_dim, dim, kernel_size=1)
            self.raw_norm = nn.LayerNorm(dim)
        else:
            self.raw_conv = None
            self.raw_residual = None
            self.raw_norm = None

        if self.fusion_mode == "pooled":
            self.fusion_fc = nn.Sequential(
                nn.Linear(dim * 2, dim),
                nn.GELU(),
                nn.Dropout(dropout),
            )
            self.gate = nn.Sequential(nn.Linear(dim * 2, dim), nn.Sigmoid())
        else:
            self.fusion_fc = None
            self.gate = None
        max_frequency_bins = self.max_len // 2 + 1
        token_capacity = self.max_len + max_frequency_bins + (self.max_len if self.use_raw_conv else 0)
        self.token_fusion = (
            nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
            if self.fusion_mode == "tokens"
            else None
        )
        stream_count = 3 if self.use_raw_conv else 2
        self.stream_type = nn.Parameter(torch.zeros(1, stream_count, dim)) if self.fusion_mode == "tokens" else None
        self.position = nn.Parameter(torch.zeros(1, token_capacity if self.fusion_mode == "tokens" else self.max_len, dim))
        layout = ["rfft_frequency_encoding", f"{self.frequency_representation}_conv1d_x3_residual_kernel_3"]
        if self.use_raw_conv:
            layout.append("raw_conv1d_x3_residual")
        layout.extend([f"mamba_x{depth}_residual", "token_fusion" if self.fusion_mode == "tokens" else "fusion_fc", "flash_attention", "norm_head"])
        self.layout = tuple(layout)
        self.attention = (
            FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
            if self.use_attention
            else nn.Identity()
        )
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        nn.init.normal_(self.position, std=0.02)

    def _frequency_features(self, x: torch.Tensor) -> torch.Tensor:
        """Return one learned frequency vector per flow, shaped ``[B, D]``."""

        # rFFT of a real sequence contains N//2 + 1 non-redundant bins.  Move
        # the original feature axis to Conv1d's channel dimension. Magnitude
        # mode stays [B, 3, F]; real_imag mode is [B, 6, F].
        # CUDA half-precision FFT kernels require power-of-two lengths.  The
        # 30-packet input is therefore transformed in FP32 and cast back
        # before the convolution branch.
        spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho").permute(0, 2, 1)
        if self.frequency_representation == "magnitude":
            frequency_input = torch.log1p(spectrum.abs())
        else:
            frequency_input = torch.cat((spectrum.real, spectrum.imag), dim=1)
        frequency_input = frequency_input.to(dtype=x.dtype)
        encoded = self.frequency_residual(frequency_input)
        for block in self.frequency:
            encoded = encoded + block(encoded)
        pooled = self.frequency_pool(encoded).flatten(1)
        return self.frequency_norm(pooled)

    def _frequency_tokens(self, x: torch.Tensor) -> torch.Tensor:
        spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho").permute(0, 2, 1)
        if self.frequency_representation == "magnitude":
            frequency_input = torch.log1p(spectrum.abs())
        else:
            frequency_input = torch.cat((spectrum.real, spectrum.imag), dim=1)
        encoded = self.frequency_residual(frequency_input.to(dtype=x.dtype))
        for block in self.frequency:
            encoded = encoded + block(encoded)
        return self.frequency_norm(encoded.transpose(1, 2))

    def _raw_tokens(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.raw_residual(x.transpose(1, 2))
        for block in self.raw_conv:
            encoded = encoded + block(encoded)
        return self.raw_norm(encoded.transpose(1, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(f"expected [batch, sequence, feature], got {tuple(x.shape)}")
        _, seq_len, feature_dim = x.shape
        if feature_dim != self.input_dim:
            raise ValueError(f"expected feature_dim={self.input_dim}, got {feature_dim}")
        if seq_len > self.max_len:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.max_len}")
        if seq_len < 3:
            raise ValueError("seq_len must be at least 3 for the frequency kernel")

        temporal_input = self.temporal_embed(x)
        temporal = temporal_input
        for block in self.temporal:
            temporal = block(temporal)
        temporal = temporal + self.temporal_residual(temporal_input)
        temporal = self.temporal_norm(temporal)

        if self.fusion_mode == "tokens":
            temporal_tokens = temporal + self.stream_type[:, 0:1]
            frequency_tokens = self._frequency_tokens(x) + self.stream_type[:, 1:2]
            streams = [temporal_tokens]
            if self.use_raw_conv:
                streams.append(self._raw_tokens(x) + self.stream_type[:, 2:3])
            streams.append(frequency_tokens)
            fused = self.token_fusion(torch.cat(streams, dim=1))
            if self.use_position:
                fused = fused + self.position[:, : fused.shape[1]]
        else:
            frequency = self._frequency_features(x)
            frequency = frequency.unsqueeze(1).expand(-1, seq_len, -1)
            joined = torch.cat([frequency, temporal], dim=-1)
            gate = self.gate(joined)
            fused = self.fusion_fc(joined)
            fused = fused + gate * temporal + (1.0 - gate) * frequency
            if self.use_position:
                fused = fused + self.position[:, :seq_len]
        fused = self.attention(fused)
        fused = self.norm(fused)
        if self.fusion_mode == "tokens" and self.pooling == "temporal_mean":
            # Frequency tokens remain in the attention context, while the
            # classifier reads the temporal stream only. This avoids giving
            # 16 frequency bins an arbitrary 16/46 share of the final mean.
            pooled = fused[:, :seq_len].mean(dim=1)
        elif self.pooling == "last":
            pooled = fused[:, seq_len - 1] if self.fusion_mode == "tokens" else fused[:, -1]
        else:
            pooled = fused.mean(dim=1)
        return self.head(pooled)


__all__ = ["HSTACMDFT"]
