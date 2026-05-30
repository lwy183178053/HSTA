import torch
import torch.nn as nn


class MLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        seq_len: int,
        hidden: int = 128,
        depth: int = 5,
        dropout: float = 0.2,
    ):
        super().__init__()
        layers = []
        in_features = input_dim * seq_len
        for layer_idx in range(depth):
            layers.extend(
                [
                    nn.Linear(in_features if layer_idx == 0 else hidden, hidden),
                    nn.LayerNorm(hidden),
                    nn.GELU(),
                    nn.Dropout(dropout),
                ]
            )
        self.features = nn.Sequential(*layers)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.flatten(start_dim=1)
        return self.head(self.features(x))
