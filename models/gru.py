from __future__ import annotations

import torch
import torch.nn as nn


class GRUClassifier(nn.Module):
    """Five-layer GRU baseline used by the unified sequence benchmark."""

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden: int = 128,
        depth: int = 5,
        dropout: float = 0.15,
        pooling: str = "last",
    ):
        super().__init__()
        self.pooling = pooling
        self.rnn = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden,
            num_layers=depth,
            dropout=dropout if depth > 1 else 0.0,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(hidden)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x, _ = self.rnn(x)
        pooled = x[:, -1] if self.pooling == "last" else x.mean(dim=1)
        return self.head(self.norm(pooled))
