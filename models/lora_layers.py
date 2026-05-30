import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class LoRALinear(nn.Module):
    def __init__(self, linear: nn.Linear, r: int = 8, alpha: int = 16, dropout: float = 0.0):
        super().__init__()
        if r < 0:
            raise ValueError("LoRA rank r must be non-negative")
        self.linear = linear
        self.r = int(r)
        self.scaling = float(alpha) / max(self.r, 1)
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

        for param in self.linear.parameters():
            param.requires_grad = False

        if self.r > 0:
            self.lora_A = nn.Parameter(torch.empty(self.r, linear.in_features))
            self.lora_B = nn.Parameter(torch.empty(linear.out_features, self.r))
            nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
            nn.init.zeros_(self.lora_B)
        else:
            self.register_parameter("lora_A", None)
            self.register_parameter("lora_B", None)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.linear(x)
        if self.r == 0:
            return y
        update = F.linear(F.linear(self.dropout(x), self.lora_A), self.lora_B)
        return y + update * self.scaling


def make_linear(
    in_features: int,
    out_features: int,
    bias: bool = True,
    lora: bool = False,
    r: int = 8,
    alpha: int = 16,
    dropout: float = 0.0,
) -> nn.Module:
    linear = nn.Linear(in_features, out_features, bias=bias)
    if not lora:
        return linear
    return LoRALinear(linear, r=r, alpha=alpha, dropout=dropout)


def mark_only_lora_and_head_trainable(model: nn.Module, train_head: bool = True) -> None:
    for name, param in model.named_parameters():
        param.requires_grad = ("lora_" in name) or (train_head and name.startswith("head."))
