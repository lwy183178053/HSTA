"""Structural checks for the HSTA-CM-DFT main model."""

from __future__ import annotations

import importlib.util

import pytest
import torch

pytest.importorskip("mamba_ssm")

from models import build_model
from models.hsta_cm_dft import HSTACMDFT


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
def test_hsta_cm_dft_registry_and_frequency_layout():
    model = build_model(
        "hsta-cm-dft",
        input_dim=3,
        num_classes=101,
        seq_len=30,
        cfg={"dim": 32, "heads": 4, "dropout": 0.0},
    )
    assert isinstance(model, HSTACMDFT)
    conv_layers = [module for module in model.frequency.modules() if isinstance(module, torch.nn.Conv1d)]
    assert len(conv_layers) == 3
    assert all(module.kernel_size == (3,) for module in conv_layers)
    assert model.frequency_residual.kernel_size == (1,)
    assert model.frequency_residual.in_channels == 3
    assert all(module.in_channels == 32 for module in conv_layers)
    assert not any(isinstance(module, torch.nn.Conv2d) for module in model.modules())

    frequency = model._frequency_features(torch.randn(2, 30, 3))
    assert frequency.shape == (2, 32)


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm is required")
def test_hsta_cm_dft_accepts_shorter_sequence_with_one_sided_fft():
    model = build_model(
        "hsta_cm_dft",
        input_dim=3,
        num_classes=101,
        seq_len=12,
        cfg={"dim": 32, "heads": 4, "dropout": 0.0, "max_len": 12},
    )
    frequency = model._frequency_features(torch.randn(2, 12, 3))
    assert frequency.shape == (2, 32)
