"""Structural checks for HSTA-CM and the retained baseline registry."""

from __future__ import annotations

import importlib.util

import pytest
import torch

from models import build_model
from models.flash_attention import FlashAttentionBlock, FlashSelfAttention


def test_flash_attention_is_strict_and_has_no_manual_backend():
    attention = FlashSelfAttention(dim=32, heads=4, dropout=0.0)
    assert attention.attention_backend == "flash"
    assert attention.flash_attention_enforced is True
    with pytest.raises(RuntimeError, match="FlashAttention"):
        attention(torch.randn(2, 30, 32))


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
def test_hsta_cm_has_three_conv_two_mamba_position_and_flash_attention_components():
    model = build_model(
        "hsta-cm",
        input_dim=3,
        num_classes=41,
        seq_len=30,
        cfg={"dim": 256, "heads": 4, "dropout": 0.0, "depth": 2, "attention_backend": "flash"},
    )
    assert model.layout == (
        "conv1d_x3_residual", "mamba_x2_residual", "fusion_fc", "flash_attention", "norm_head"
    )
    assert model.position.shape == (1, 30, 256)
    assert len(model.spatial) == 3
    assert sum(isinstance(module, torch.nn.Conv1d) for module in model.spatial.modules()) == 3
    assert len(model.temporal) == 2
    assert all("Mamba" in block.mixer.__class__.__name__ for block in model.temporal)
    assert isinstance(model.attention, FlashAttentionBlock)
    assert any(isinstance(module, FlashSelfAttention) for module in model.modules())
    assert model.head.in_features == 256
    assert model.head.out_features == 41


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
def test_hsta_cm_ablation_flags_remove_only_requested_components():
    no_conv = build_model("hsta-cm", 3, 41, 30, {"dim": 256, "use_conv": False})
    no_mamba = build_model("hsta-cm", 3, 41, 30, {"dim": 256, "use_mamba": False})
    no_attention = build_model("hsta-cm", 3, 41, 30, {"dim": 256, "use_attention": False})
    assert no_conv.spatial is None and len(no_conv.temporal) == 2
    assert len(no_mamba.temporal) == 0 and len(no_mamba.spatial) == 3
    assert isinstance(no_attention.attention, torch.nn.Identity)


def test_legacy_hsta_registry_name_is_removed():
    with pytest.raises(ValueError):
        build_model("hsta", input_dim=3, num_classes=41, seq_len=30, cfg={})
