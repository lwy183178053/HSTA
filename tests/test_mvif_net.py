"""Focused MVIF-Net contract checks."""

import importlib

import torch
from torch import nn

from models import build_model


class _IdentityMamba(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def forward(self, x):
        return x


def _build_cpu(monkeypatch, classes=61):
    module = importlib.import_module("models.mvif_net")
    monkeypatch.setattr(module, "MambaBlock", _IdentityMamba)
    model = build_model(
        "mvif-net",
        3,
        classes,
        30,
        {
            "dim": 32,
            "dropout": 0.0,
            "graph_k": 4,
            "branch_residual_init": 0.1,
            "residual_scale_max": 0.5,
        },
    )
    model.attention = nn.Identity()
    return model


def test_fixed_three_view_contract(monkeypatch):
    model = _build_cpu(monkeypatch)
    assert model.token_count == 76
    assert model.branch_count == 3
    assert model.branch_keys == ["mamba", "packet_graph", "dft_conv"]
    assert len(model.temporal) == len(model.graph_blocks) == 2
    assert [block.conv.kernel_size for block in model.dft_spatial] == [(1,), (3,)]
    assert not hasattr(model, "auxiliary_loss")
    assert not hasattr(model, "use_time_cnn")
    assert not hasattr(model, "graph_residual_mode")
    assert not hasattr(model, "dft_residual_mode")


def test_gate_and_classifier_contract(monkeypatch):
    model = _build_cpu(monkeypatch, classes=61).train()
    logits = model(torch.randn(3, 30, 3))
    assert logits.shape == (3, 61)
    assert model.last_branch_gate is not None
    assert model.last_branch_gate.shape == (3, 3)
    assert torch.allclose(model.last_branch_gate.sum(dim=-1), torch.ones(3), atol=1e-6)

    loss = nn.functional.cross_entropy(logits, torch.tensor([0, 1, 2]))
    loss.backward()
    assert torch.isfinite(loss)
    assert model.head.weight.grad is not None
    assert all(torch.isfinite(parameter.grad).all() for parameter in model.parameters() if parameter.grad is not None)


def test_open_and_closed_classifier_sizes(monkeypatch):
    open_model = _build_cpu(monkeypatch, classes=61)
    closed_model = _build_cpu(monkeypatch, classes=60)
    assert open_model(torch.randn(2, 30, 3)).shape == (2, 61)
    assert closed_model(torch.randn(2, 30, 3)).shape == (2, 60)
