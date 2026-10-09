"""HSTA-CM-DFT: temporal Mamba plus a frequency-domain Conv2d branch.

The input remains a packet sequence ``[batch, sequence, feature]``.  The
frequency branch applies a one-sided real FFT along the packet axis, keeps
real and imaginary parts as two Conv2d channels, and pools its learned
frequency representation to a vector.  That vector is broadcast over packet
positions before the same gated fusion and FlashAttention head used by
HSTA-CM.
"""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


class HSTACMDFT(nn.Module):
    """Open-set classifier with a DFT/Conv2d frequency encoder.

    ``HSTACMDFT`` is a separate model variant.  The original ``HSTACM``
    implementation is intentionally unchanged so the main benchmark remains
    a direct time-domain reference.
    """

    layout = (
        "rfft_frequency_encoding",
        "conv2d_x3_frequency_residual_kernel_1x3",
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
    ):
        super().__init__()
        if input_dim <= 0 or num_classes <= 0:
            raise ValueError("input_dim and num_classes must be positive")
        if depth <= 0:
            raise ValueError("depth must be positive")
        if max_len < 3:
            raise ValueError("max_len must be at least 3 for the frequency kernel")
        if pooling not in {"mean", "last"}:
            raise ValueError("pooling must be mean or last")

        self.input_dim = int(input_dim)
        self.dim = int(dim)
        self.max_len = int(max_len)
        self.pooling = pooling
        self.use_attention = bool(use_attention)
        self.use_position = bool(use_position)

        # Real and imaginary FFT parts are two input channels.  Three residual
        # (1, 3) convolutions model adjacent frequencies while keeping feature
        # rows independent until the learned global pooling step.
        self.frequency = nn.Sequential(
            nn.Conv2d(2, dim, kernel_size=(1, 3), padding=(0, 1)),
            nn.BatchNorm2d(dim),
            nn.GELU(),
            nn.Dropout2d(dropout),
            nn.Conv2d(dim, dim, kernel_size=(1, 3), padding=(0, 1)),
            nn.BatchNorm2d(dim),
            nn.GELU(),
            nn.Dropout2d(dropout),
            nn.Conv2d(dim, dim, kernel_size=(1, 3), padding=(0, 1)),
            nn.GELU(),
        )
        self.frequency_residual = nn.Conv2d(2, dim, kernel_size=1)
        self.frequency_pool = nn.AdaptiveAvgPool2d((1, 1))

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

        self.fusion_fc = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
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

    def _frequency_features(self, x: torch.Tensor) -> torch.Tensor:
        """Return one learned frequency vector per flow, shaped ``[B, D]``."""

        # rFFT of a real sequence contains N//2 + 1 non-redundant bins.  The
        # feature axis is moved next to the complex channel before splitting
        # real/imaginary parts into the Conv2d input layout [B, 2, C, F].
        # CUDA half-precision FFT kernels require power-of-two lengths.  The
        # 30-packet input is therefore transformed in FP32 and cast back
        # before the convolution branch (autocast still handles Conv2d).
        spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho").permute(0, 2, 1)
        frequency_input = torch.stack((spectrum.real, spectrum.imag), dim=1).to(dtype=x.dtype)
        encoded = self.frequency(frequency_input) + self.frequency_residual(frequency_input)
        return self.frequency_pool(encoded).flatten(1)

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

        frequency = self._frequency_features(x)
        temporal_input = self.temporal_embed(x)
        temporal = temporal_input
        for block in self.temporal:
            temporal = block(temporal)
        temporal = temporal + self.temporal_residual(temporal_input)

        # The DFT branch summarizes the whole flow, then conditions every
        # packet token in the same gated fusion space as the temporal branch.
        frequency = frequency.unsqueeze(1).expand(-1, seq_len, -1)
        joined = torch.cat([frequency, temporal], dim=-1)
        gate = self.gate(joined)
        fused = self.fusion_fc(joined)
        fused = fused + gate * temporal + (1.0 - gate) * frequency
        if self.use_position:
            fused = fused + self.position[:, :seq_len]
        fused = self.attention(fused)
        fused = self.norm(fused)
        pooled = fused[:, -1] if self.pooling == "last" else fused.mean(dim=1)
        return self.head(pooled)


__all__ = ["HSTACMDFT"]
