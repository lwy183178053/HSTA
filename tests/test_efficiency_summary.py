"""Smoke tests for the three-model compact comparison."""

from __future__ import annotations

import importlib.util

import pytest
import torch

pytest.importorskip("mamba_ssm")

from models import build_model


def test_tcnet_primary_baseline_accepts_shared_packet_tensor():
    model = build_model(
        "30pkttcnet-adapted",
        input_dim=3,
        num_classes=101,
        seq_len=30,
        cfg={"dim": 32, "hidden": 32, "depth": 2, "dropout": 0.0},
    )
    logits = model(torch.randn(2, 30, 3))
    assert tuple(logits.shape) == (2, 101)


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required for mamba_ssm")
@pytest.mark.parametrize("name", ["hsta", "netmamba-adapted"])
def test_mamba_primary_models_accept_shared_packet_tensor(name):
    model = build_model(
        name,
        input_dim=3,
        num_classes=101,
        seq_len=30,
        cfg={
            "dim": 32,
            "hidden": 32,
            "depth": 2,
            "heads": 4,
            "dropout": 0.0,
            "spatial_conv": True,
            "attention_backend": "flash",
        },
    ).cuda().eval()
    with torch.autocast(device_type="cuda", dtype=torch.float16):
        logits = model(torch.randn(2, 30, 3, device="cuda", dtype=torch.float16))
    assert tuple(logits.shape) == (2, 101)


@pytest.mark.parametrize("name", ["gru", "transformer"])
def test_removed_model_names_are_rejected(name):
    with pytest.raises((ValueError, ImportError)):
        build_model(name, input_dim=3, num_classes=101, seq_len=30, cfg={})
