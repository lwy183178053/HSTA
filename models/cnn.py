import torch
import torch.nn as nn


class CNN1DClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden: int = 128,
        depth: int = 5,
        kernel_size: int = 3,
        dropout: float = 0.15,
    ):
        super().__init__()
        padding = kernel_size // 2
        layers = []
        channels = input_dim
        for _ in range(depth):
            layers.extend(
                [
                    nn.Conv1d(channels, hidden, kernel_size=kernel_size, padding=padding),
                    nn.BatchNorm1d(hidden),
                    nn.GELU(),
                    nn.Dropout(dropout),
                ]
            )
            channels = hidden
        self.conv = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.pool(self.conv(x)).squeeze(-1)
        return self.head(x)
