"""Transformer attention components built on PyTorch scaled dot-product attention."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class FlashSelfAttention(nn.Module):
    def __init__(self, dim: int, heads: int = 4, dropout: float = 0.0):
        super().__init__()
        if dim <= 0 or heads <= 0 or dim % heads:
            raise ValueError("dim must be positive and divisible by heads")
        self.dim = dim
        self.heads = heads
        self.head_dim = dim // heads
        self.dropout = float(dropout)
        self.qkv = nn.Linear(dim, 3 * dim)
        self.out_proj = nn.Linear(dim, dim)
        self.attention_backend = "sdpa_auto"

    def forward(
        self,
        x: torch.Tensor,
        key_padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        batch, seq_len, _ = x.shape
        attn_mask = None
        if key_padding_mask is not None:
            if key_padding_mask.shape != (batch, seq_len):
                raise ValueError(
                    "key_padding_mask must have shape "
                    f"({batch}, {seq_len}), got {tuple(key_padding_mask.shape)}"
                )
            if key_padding_mask.dtype != torch.bool:
                raise TypeError("key_padding_mask must have dtype torch.bool")
            if key_padding_mask.device != x.device:
                raise ValueError("key_padding_mask and x must be on the same device")
            # SDPA uses True for allowed keys; key_padding_mask uses True for padding.
            attn_mask = (~key_padding_mask)[:, None, None, :]

        qkv = self.qkv(x).reshape(batch, seq_len, 3, self.heads, self.head_dim)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        y = F.scaled_dot_product_attention(
            q,
            k,
            v,
            attn_mask=attn_mask,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=False,
        )
        y = y.transpose(1, 2).reshape(batch, seq_len, self.dim)
        return self.out_proj(y)


class FlashAttentionBlock(nn.Module):
    def __init__(self, dim: int, heads: int = 4, mlp_ratio: int = 4, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = FlashSelfAttention(dim, heads=heads, dropout=dropout)
        self.norm2 = nn.LayerNorm(dim)
        hidden = dim * mlp_ratio
        self.ffn = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, dim),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        x: torch.Tensor,
        key_padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), key_padding_mask=key_padding_mask)
        return x + self.ffn(self.norm2(x))
