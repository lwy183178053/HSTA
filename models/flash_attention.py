"""Strict PyTorch FlashAttention components used by the compact benchmark.

The project deliberately requires the CUDA FlashAttention backend.  Falling
back to a hand-written softmax implementation would make results incomparable,
so an unsupported device or dtype raises a clear error.
"""

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
        self.attention_backend = "flash"
        self.actual_attention_backend = "flash"
        self.flash_attention_enforced = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not x.is_cuda:
            raise RuntimeError(
                "PyTorch FlashAttention requires a CUDA tensor with FP16 or BF16; "
                "run the experiment in the supported WSL CUDA environment."
            )
        if x.dtype not in (torch.float16, torch.bfloat16):
            autocast_cuda = torch.is_autocast_enabled("cuda")
            if autocast_cuda:
                x = x.to(torch.get_autocast_dtype("cuda"))
            else:
                raise RuntimeError(
                    "PyTorch FlashAttention requires a CUDA tensor with FP16 or BF16; "
                    "enable CUDA autocast for the model forward."
                )
        if not hasattr(torch.backends.cuda, "is_flash_attention_available") or not torch.backends.cuda.is_flash_attention_available():
            raise RuntimeError("This PyTorch build does not provide the FlashAttention backend")
        batch, seq_len, _ = x.shape
        qkv = self.qkv(x).reshape(batch, seq_len, 3, self.heads, self.head_dim)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        # The explicit backend context prevents SDPA from silently selecting
        # the math or memory-efficient implementation.
        try:
            from torch.nn.attention import SDPBackend, sdpa_kernel

            with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
                y = F.scaled_dot_product_attention(
                    q, k, v,
                    dropout_p=self.dropout if self.training else 0.0,
                    is_causal=False,
                )
        except ImportError:  # PyTorch 2.0/2.1 spelling
            with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
                y = F.scaled_dot_product_attention(
                    q, k, v,
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        return x + self.ffn(self.norm2(x))
