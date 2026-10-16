import importlib

import torch
from torch import nn

from models import build_model


class _IdentityMamba(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def forward(self, x):
        return x


ARMS = (
    {"use_gate": True, "use_aux": False, "graph_residual_mode": "full", "dft_residual_mode": "full"},
    {"use_gate": True, "use_aux": False, "graph_residual_mode": "scaled", "dft_residual_mode": "scaled"},
    {"use_gate": True, "use_aux": True, "graph_residual_mode": "full", "dft_residual_mode": "full"},
    {"use_gate": True, "use_aux": True, "graph_residual_mode": "scaled", "dft_residual_mode": "scaled"},
    {"use_gate": True, "use_aux": True, "graph_residual_mode": "none", "dft_residual_mode": "scaled"},
    {"use_gate": True, "use_aux": True, "graph_residual_mode": "scaled", "dft_residual_mode": "none"},
)


def _build(monkeypatch, **model_cfg):
    module = importlib.import_module("models.hsta_cm")
    monkeypatch.setattr(module, "MambaBlock", _IdentityMamba)
    model = build_model("hsta-cm-gated", 3, 7, 30, {"dim": 32, "dropout": 0.0, **model_cfg}).train()
    model.attention = nn.Identity()
    return model


def test_arms_keep_76_tokens_and_match_parameter_count(monkeypatch):
    counts = set()
    for cfg in ARMS:
        model = _build(monkeypatch, **cfg)
        counts.add(sum(p.numel() for p in model.parameters()))
        x = torch.randn(4, 30, 3)
        y = torch.tensor([0, 1, 2, 3])
        logits = model(x)
        assert model.token_count == 76
        assert logits.shape == (4, 7)
        loss = nn.functional.cross_entropy(logits, y)
        auxiliary = model.auxiliary_loss(y)
        if cfg["use_aux"]:
            assert auxiliary is not None
            loss = loss + auxiliary
        else:
            assert auxiliary is None
        loss.backward()
        assert torch.isfinite(loss)
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    assert len(counts) == 1, "all ablation arms must keep the same parameter count"


def test_no_residual_modes_still_forward(monkeypatch):
    model = _build(
        monkeypatch,
        use_gate=True, use_aux=True,
        graph_residual_mode="none", dft_residual_mode="none",
    )
    logits = model(torch.randn(2, 30, 3))
    assert logits.shape == (2, 7) and torch.isfinite(logits).all()


def test_followup_branch_layouts_forward(monkeypatch):
    arms = (
        ({"residual_scale_mode": "bounded"}, 76),
        ({"residual_scale_mode": "bounded", "mamba_outer_residual": False}, 76),
        ({"residual_scale_mode": "bounded", "use_dft": False}, 60),
        ({"residual_scale_mode": "bounded", "graph_use_local": False}, 76),
        ({"residual_scale_mode": "bounded", "use_dft": False, "use_time_cnn": True}, 90),
    )
    for cfg, expected_tokens in arms:
        model = _build(monkeypatch, use_gate=True, use_aux=False, **cfg)
        model.attention = nn.Identity()
        logits = model(torch.randn(3, 30, 3))
        assert model.token_count == expected_tokens
        assert logits.shape == (3, 7) and torch.isfinite(logits).all()
        assert model.last_branch_gate is not None
        assert model.last_branch_gate.shape == (3, len(model.branch_keys))
        if cfg.get("residual_scale_mode") == "bounded":
            for block in list(model.graph_blocks) + list(model.dft_spatial) + list(model.time_cnn_blocks):
                if block.mode == "scaled":
                    scale = float(block.effective_scale().detach())
                    assert 0.0 < scale < block.scale_max
