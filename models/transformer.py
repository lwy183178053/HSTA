import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiHeadSelfAttention(nn.Module):
    def __init__(
        self,
        dim: int,
        heads: int = 4,
        dropout: float = 0.1,
        attention_backend: str = "manual",
    ):
        super().__init__()
        if dim % heads != 0:
            raise ValueError(f"dim={dim} must be divisible by heads={heads}")
        self.dim = dim
        self.heads = heads
        self.head_dim = dim // heads
        self.attention_backend = str(attention_backend).lower()
        if self.attention_backend not in {"manual", "flash"}:
            raise ValueError("attention_backend must be 'manual' or 'flash'")
        self.actual_attention_backend = "uninitialized"
        self.flash_attention_enforced = self.attention_backend == "flash"
        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(dim, dim)
        self.v_proj = nn.Linear(dim, dim)
        self.out_proj = nn.Linear(dim, dim)
        self.attn_drop = nn.Dropout(dropout)
        self.proj_drop = nn.Dropout(dropout)

    def _shape(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = x.shape
        return x.view(batch, seq_len, self.heads, self.head_dim).transpose(1, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q = self._shape(self.q_proj(x))
        k = self._shape(self.k_proj(x))
        v = self._shape(self.v_proj(x))
        if self.attention_backend == "flash":
            if not q.is_cuda or q.dtype not in {torch.float16, torch.bfloat16}:
                raise RuntimeError(
                    "FlashAttention requires CUDA tensors with FP16 or BF16 autocast; "
                    "strict flash mode does not silently fall back."
                )
            from torch.nn.attention import SDPBackend, sdpa_kernel

            dropout_p = self.attn_drop.p if self.training else 0.0
            with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
                y = F.scaled_dot_product_attention(q, k, v, dropout_p=dropout_p)
            self.actual_attention_backend = "flash"
        else:
            attn = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
            attn = attn.softmax(dim=-1)
            y = self.attn_drop(attn) @ v
            self.actual_attention_backend = "manual"
        y = y.transpose(1, 2).contiguous().view(x.shape[0], x.shape[1], self.dim)
        return self.proj_drop(self.out_proj(y))


class AttentionBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        heads: int = 4,
        dropout: float = 0.1,
        attention_backend: str = "manual",
    ):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.attn = MultiHeadSelfAttention(
            dim,
            heads=heads,
            dropout=dropout,
            attention_backend=attention_backend,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.attn(self.norm(x))


class FeedForwardBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        hidden = dim * mlp_ratio
        self.norm = nn.LayerNorm(dim)
        self.net = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(self.norm(x))


class TransformerEncoderBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.attention = AttentionBlock(dim, heads=heads, dropout=dropout)
        self.ffn = FeedForwardBlock(dim, mlp_ratio=mlp_ratio, dropout=dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.attention(x)
        return self.ffn(x)


class TrafficTransformer(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 128,
        depth: int = 5,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
        max_len: int = 256,
    ):
        super().__init__()
        self.max_len = max_len
        self.embed = nn.Linear(input_dim, dim)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, dim))
        self.pos = nn.Parameter(torch.zeros(1, max_len + 1, dim))
        self.blocks = nn.ModuleList(
            [
                TransformerEncoderBlock(
                    dim,
                    heads=heads,
                    mlp_ratio=mlp_ratio,
                    dropout=dropout,
                )
                for _ in range(depth)
            ]
        )
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        nn.init.normal_(self.cls_token, std=0.02)
        nn.init.normal_(self.pos, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = x.shape
        if seq_len > self.max_len:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.max_len}")
        x = self.embed(x)
        cls = self.cls_token.expand(batch, -1, -1)
        x = torch.cat([cls, x], dim=1) + self.pos[:, : seq_len + 1]
        for block in self.blocks:
            x = block(x)
        return self.head(self.norm(x[:, 0]))
