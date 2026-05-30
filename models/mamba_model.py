import torch
import torch.nn as nn

try:
    from mamba_ssm import Mamba as OfficialMamba
except Exception:
    OfficialMamba = None


class MambaBlock(nn.Module):
    """Official mamba-ssm block with LayerNorm, residual, and dropout."""

    def __init__(
        self,
        dim: int = 128,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        dropout: float = 0.1,
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        if OfficialMamba is None:
            raise ImportError(
                "mamba-ssm is required for Mamba models. "
                "Install it in WSL/Linux CUDA, for example: pip install mamba-ssm"
            )
        self.norm = nn.LayerNorm(dim)
        self.mixer = OfficialMamba(d_model=dim, d_state=d_state, d_conv=d_conv, expand=expand)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.drop(self.mixer(self.norm(x)))


class MambaClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 128,
        depth: int = 5,
        dropout: float = 0.1,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        max_len: int = 256,
        pooling: str = "mean",
        lora: bool = False,
        r: int = 8,
        alpha: int = 16,
    ):
        super().__init__()
        self.max_len = max_len
        self.pooling = pooling
        self.embed = nn.Linear(input_dim, dim)
        self.pos = nn.Parameter(torch.zeros(1, max_len, dim))
        self.blocks = nn.ModuleList(
            [
                MambaBlock(
                    dim=dim,
                    d_state=d_state,
                    d_conv=d_conv,
                    expand=expand,
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
        nn.init.normal_(self.pos, std=0.02)

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
