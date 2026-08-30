import torch
import torch.nn as nn

from .mamba_model import MambaBlock
from .transformer import AttentionBlock, FeedForwardBlock


class HSTA(nn.Module):
    """HSTA with configurable attention placement for controlled ablations.

    The canonical layout is Mamba -> Mamba -> Transition FFN -> Attention ->
    Refinement FFN. Ablation configs change only the order or replace the
    attention block with another FFN.
    """
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 128,
        layout: list[str] | None = None,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.1,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        max_len: int = 256,
        pooling: str = "mean",
        block_repeats: int = 1,
        attention_backend: str = "manual",
    ):
        super().__init__()
        if block_repeats < 1:
            raise ValueError("block_repeats must be >= 1")
        self.max_len = max_len
        self.pooling = pooling
        self.base_layout = layout or ["mamba", "mamba", "mlp", "attention", "mlp"]
        self.block_repeats = int(block_repeats)
        self.layout = self.base_layout * self.block_repeats
        self.embed = nn.Linear(input_dim, dim)
        self.pos = nn.Parameter(torch.zeros(1, max_len, dim))
        self.blocks = nn.ModuleList(
            [
                self._make_block(
                    name,
                    dim=dim,
                    heads=heads,
                    mlp_ratio=mlp_ratio,
                    dropout=dropout,
                    d_state=d_state,
                    d_conv=d_conv,
                    expand=expand,
                    attention_backend=attention_backend,
                )
                for name in self.layout
            ]
        )
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        nn.init.normal_(self.pos, std=0.02)

    @staticmethod
    def _make_block(name: str, **kwargs) -> nn.Module:
        name = name.lower()
        if name in {"mamba", "ssm"}:
            return MambaBlock(
                dim=kwargs["dim"],
                d_state=kwargs["d_state"],
                d_conv=kwargs["d_conv"],
                expand=kwargs["expand"],
                dropout=kwargs["dropout"],
            )
        if name in {"attention", "attn"}:
            return AttentionBlock(
                kwargs["dim"],
                heads=kwargs["heads"],
                dropout=kwargs["dropout"],
                attention_backend=kwargs["attention_backend"],
            )
        if name in {"mlp", "ffn"}:
            return FeedForwardBlock(
                kwargs["dim"],
                mlp_ratio=kwargs["mlp_ratio"],
                dropout=kwargs["dropout"],
            )
        raise ValueError(f"Unknown HSTA block: {name}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, seq_len, _ = x.shape
        if seq_len > self.max_len:
            raise ValueError(f"seq_len={seq_len} exceeds max_len={self.max_len}")
        x = self.embed(x) + self.pos[:, :seq_len]
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        feat = x[:, -1] if self.pooling == "last" else x.mean(dim=1)
        return self.head(feat)
