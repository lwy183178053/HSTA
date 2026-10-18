"""Model registry, MVIF-Net layout, and baseline capacity checks."""

import importlib
import importlib.util

import pytest
import torch

from models import build_model
from models.flash_attention import FlashAttentionBlock, FlashSelfAttention


class _IdentityMamba(torch.nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def forward(self, x):
        return x


def test_flash_attention_is_strict():
    attention = FlashSelfAttention(32, heads=4)
    with pytest.raises(RuntimeError, match="FlashAttention"):
        attention(torch.randn(2, 30, 32))


def test_mvif_net_cpu_forward_and_bounded_scales(monkeypatch):
    module = importlib.import_module("models.mvif_net")
    monkeypatch.setattr(module, "MambaBlock", _IdentityMamba)
    model = build_model(
        "mvif-net",
        3,
        7,
        30,
        {
            "dim": 32,
            "dropout": 0.0,
            "graph_k": 4,
            "branch_residual_init": 0.1,
            "residual_scale_max": 0.5,
        },
    ).train()
    model.attention = torch.nn.Identity()

    assert model.token_count == 76
    assert model.branch_names == ("mamba", "packet_graph", "dft_conv")
    assert model.packet_position.shape == (1, 30, 32)
    assert model.frequency_position.shape == (1, 16, 32)
    assert model.branch_type.shape == (3, 32)
    assert len(model.temporal) == len(model.graph_blocks) == 2
    assert [block.conv.kernel_size for block in model.dft_spatial] == [(1,), (3,)]
    assert isinstance(model.attention, torch.nn.Identity)
    assert not hasattr(model, "use_aux")

    x = torch.randn(4, 30, 3)
    y = torch.tensor([0, 1, 2, 3])
    logits = model(x)
    assert logits.shape == (4, 7) and torch.isfinite(logits).all()
    assert model.last_branch_gate is not None
    assert model.last_branch_gate.shape == (4, 3)
    assert torch.allclose(model.last_branch_gate.sum(dim=-1), torch.ones(4), atol=1e-6)
    for block in list(model.graph_blocks) + list(model.dft_spatial):
        scale = block.effective_scale().detach()
        assert 0.0 < float(scale) < 0.5

    loss = torch.nn.functional.cross_entropy(logits, y)
    loss.backward()
    assert torch.isfinite(loss)
    assert model.head.weight.grad is not None
    assert all(torch.isfinite(parameter.grad).all() for parameter in model.parameters() if parameter.grad is not None)


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm required")
def test_mvif_net_formal_layout_and_attention():
    model = build_model(
        "mvif-net",
        3,
        61,
        30,
        {"dim": 256, "graph_k": 4, "branch_residual_init": 0.1, "residual_scale_max": 0.5},
    )
    assert model.token_count == 76
    assert isinstance(model.attention, FlashAttentionBlock)
    assert model.head.out_features == 61
    assert model.layout[3:6] == ("bounded_residual_scale", "branch_norm_gate", "no_aux")
    assert sum(parameter.numel() for parameter in model.parameters()) == 2_441_479


@pytest.mark.parametrize("name", ["legacy_model", "gru", "transformer", "unsupported_branch"])
def test_obsolete_registry_names_rejected(name):
    with pytest.raises(ValueError):
        build_model(name, 3, 61, 30)


def test_bpf_graph_depths_can_be_bounded_for_capacity_matched_run():
    model = build_model(
        "bpf-gnn", 3, 61, 30,
        {"dim": 664, "graph_depths": [1, 2, 1]},
    )
    assert model.graph_depths == (1, 2, 1)
    assert len(model.feature_blocks) + len(model.packet_blocks) + len(model.flow_blocks) == 4


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm required")
def test_baseline_configs_remain_capacity_matched():
    candidates = [
        ("30pkttcnet-adapted", {"channels": 300, "depth": 4, "classifier_hidden": 300}, 2_278_261),
        ("netmamba-adapted", {"dim": 292, "depth": 4, "max_len": 30}, 2_294_305),
        ("srvit", {"dim": 192, "depth": 4, "mlp_ratio": 3}, 2_203_837),
        ("trafficaudio", {"dim": 416}, 2_210_893),
        ("bpf-gnn", {"dim": 664, "graph_depths": [1, 2, 1]}, 2_258_990),
    ]
    counts = []
    for name, cfg, expected in candidates:
        actual = sum(parameter.numel() for parameter in build_model(name, 3, 61, 30, cfg).parameters())
        assert actual == expected
        counts.append(actual)
    assert max(counts) / min(counts) < 1.05
