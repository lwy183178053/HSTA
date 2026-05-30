import math

import torch
import torch.nn as nn

from .lora_layers import make_linear


class MultiHeadSelfAttention(nn.Module):
    def __init__(
        self,
        dim: int,
        heads: int = 4,
        dropout: float = 0.1,
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        if dim % heads != 0:
            raise ValueError(f"dim={dim} must be divisible by heads={heads}")
        self.dim = dim
        self.heads = heads
        self.head_dim = dim // heads
        self.q_proj = make_linear(dim, dim, lora=lora, r=r, alpha=alpha, dropout=dropout)
        self.k_proj = make_linear(dim, dim, lora=lora, r=r, alpha=alpha, dropout=dropout)
        self.v_proj = make_linear(dim, dim, lora=lora, r=r, alpha=alpha, dropout=dropout)
        self.out_proj = make_linear(dim, dim, lora=lora, r=r, alpha=alpha, dropout=dropout)
        self.attn_drop = nn.Dropout(dropout)
        self.proj_drop = nn.Dropout(dropout)

    def _shape(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = x.shape
        return x.view(batch, seq_len, self.heads, self.head_dim).transpose(1, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q = self._shape(self.q_proj(x))
        k = self._shape(self.k_proj(x))
        v = self._shape(self.v_proj(x))
        attn = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        attn = attn.softmax(dim=-1)
        y = self.attn_drop(attn) @ v
        y = y.transpose(1, 2).contiguous().view(x.shape[0], x.shape[1], self.dim)
        return self.proj_drop(self.out_proj(y))


class AttentionBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        heads: int = 4,
        dropout: float = 0.1,
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.attn = MultiHeadSelfAttention(dim, heads=heads, dropout=dropout, lora=lora, r=r, alpha=alpha)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.attn(self.norm(x))


class FeedForwardBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        hidden = dim * mlp_ratio
        self.norm = nn.LayerNorm(dim)
        self.net = nn.Sequential(
            make_linear(dim, hidden, lora=lora, r=r, alpha=alpha, dropout=dropout),
            nn.GELU(),
            nn.Dropout(dropout),
            make_linear(hidden, dim, lora=lora, r=r, alpha=alpha, dropout=dropout),
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
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        self.attention = AttentionBlock(dim, heads=heads, dropout=dropout, lora=lora, r=r, alpha=alpha)
        self.ffn = FeedForwardBlock(dim, mlp_ratio=mlp_ratio, dropout=dropout, lora=lora, r=r, alpha=alpha)

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
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
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
                    lora=lora,
                    r=r,
                    alpha=alpha,
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
