import torch
import torch.nn as nn


class RNNClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden: int = 128,
        depth: int = 5,
        dropout: float = 0.15,
        rnn_type: str = "lstm",
        bidirectional: bool = False,
        pooling: str = "last",
    ):
        super().__init__()
        rnn_type = rnn_type.lower()
        rnn_cls = {"lstm": nn.LSTM, "gru": nn.GRU}.get(rnn_type)
        if rnn_cls is None:
            raise ValueError(f"Unsupported rnn_type: {rnn_type}")
        self.pooling = pooling
        self.rnn = rnn_cls(
            input_dim,
            hidden,
            num_layers=depth,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if depth > 1 else 0.0,
        )
        out_dim = hidden * (2 if bidirectional else 1)
        self.norm = nn.LayerNorm(out_dim)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(out_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y, _ = self.rnn(x)
        feat = y.mean(dim=1) if self.pooling == "mean" else y[:, -1]
        return self.head(self.drop(self.norm(feat)))
