"""Focused model tests for HSTA-CM and its retained baselines."""

from __future__ import annotations

import importlib.util

import pytest
import torch

pytest.importorskip("mamba_ssm")

from models import build_model
from models.flash_attention import FlashSelfAttention


def test_flash_attention_is_strict_and_has_no_manual_backend():
    attention = FlashSelfAttention(dim=32, heads=4, dropout=0.0)
    assert attention.attention_backend == "flash"
    assert attention.flash_attention_enforced is True
    with pytest.raises(RuntimeError, match="FlashAttention"):
        attention(torch.randn(2, 30, 32))


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required for mamba_ssm")
def test_hsta_cm_has_conv_mamba_and_flash_attention_components():
    model = build_model(
        "hsta",
        input_dim=3,
        num_classes=101,
        seq_len=30,
        cfg={
            "dim": 32,
            "heads": 4,
            "dropout": 0.0,
            "spatial_conv": True,
            "temporal_mamba": True,
            "spatial_branch": True,
            "use_attention": True,
            "attention_backend": "flash",
        },
    ).cuda().eval()
    assert any(isinstance(module, torch.nn.Conv1d) for module in model.modules())
    assert any("Mamba" in module.__class__.__name__ for module in model.modules())
    assert any(isinstance(module, FlashSelfAttention) for module in model.modules())
