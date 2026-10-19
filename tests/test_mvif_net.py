"""Focused MVIF-Net contract checks."""

import importlib
import sys
from types import SimpleNamespace

import torch
from torch import nn

from models import build_model


class _IdentityMamba(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.residual = kwargs["residual"]

    def forward(self, x):
        return x


class _ZeroMamba(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.residual = kwargs["residual"]

    def forward(self, x):
        return torch.zeros_like(x)


class _OnesPacketProjection(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        return torch.ones(x.shape[0], x.shape[1], self.dim, device=x.device)


class _OnesFrequencyProjection(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        return torch.ones(x.shape[0], self.dim, x.shape[-1], device=x.device)


class _ScaleAndRecord(nn.Module):
    def __init__(self, scale):
        super().__init__()
        self.scale = scale
        self.seen = None

    def forward(self, x, *args):
        self.seen = x.detach().clone()
        return self.scale * x


class _RecordIdentity(nn.Module):
    def __init__(self):
        super().__init__()
        self.seen = None

    def forward(self, x):
        self.seen = x.detach().clone()
        return x


class _IdentityAttention(nn.Module):
    def forward(self, x, key_padding_mask=None):
        return x


class _CaptureAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.key_padding_mask = None

    def forward(self, x, key_padding_mask=None):
        self.key_padding_mask = key_padding_mask.detach().clone()
        return x


class _PositionAttention(nn.Module):
    def forward(self, x, key_padding_mask=None):
        values = torch.arange(x.shape[1], device=x.device, dtype=x.dtype)
        return values.view(1, -1, 1).expand_as(x)


class _CaptureHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.seen = None

    def forward(self, x):
        self.seen = x.detach().clone()
        return x[:, :1]


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
    model.attention = _IdentityAttention()
    return model


def test_fixed_three_view_contract(monkeypatch):
    model = _build_cpu(monkeypatch)
    assert model.token_count == 76
    assert model.branch_count == 3
    assert model.branch_keys == ["mamba", "packet_graph", "dft_conv"]
    assert len(model.temporal) == len(model.graph_blocks) == 2
    assert all(not block.residual for block in model.temporal)
    assert [block.conv.kernel_size for block in model.dft_spatial] == [(1,), (3,)]
    assert model.graph_residual_logit.numel() == model.dft_residual_logit.numel() == 1
    assert 0.0 < model.effective_graph_residual_scale().item() < 0.5
    assert 0.0 < model.effective_dft_residual_scale().item() < 0.5
    assert all(not hasattr(block, "residual_scale") for block in model.graph_blocks)
    assert all(not hasattr(block, "residual_scale") for block in model.dft_spatial)
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


def test_mvif_net_passes_concatenated_padding_mask_to_attention(monkeypatch):
    model = _build_cpu(monkeypatch).eval()
    capture = _CaptureAttention()
    model.attention = capture
    x = torch.randn(2, 30, 3)
    x[0, 27:] = 0.0
    x[1, 24:] = 0.0

    model(x)

    expected_padding = torch.zeros(2, 76, dtype=torch.bool)
    expected_padding[0, 27:30] = True
    expected_padding[0, 57:60] = True
    expected_padding[1, 24:30] = True
    expected_padding[1, 54:60] = True
    assert capture.key_padding_mask.shape == (2, 76)
    assert torch.equal(capture.key_padding_mask, expected_padding)


def test_post_attention_readout_is_global_masked_mean(monkeypatch):
    model = _build_cpu(monkeypatch).eval()
    model.attention = _PositionAttention()
    model.norm = nn.Identity()
    capture_head = _CaptureHead()
    model.head = capture_head
    x = torch.randn(1, 30, 3)
    x[:, 28:] = 0.0

    model(x)

    valid_positions = torch.cat((torch.arange(28), torch.arange(30, 58), torch.arange(60, 76)))
    expected = valid_positions.float().mean()
    torch.testing.assert_close(capture_head.seen, torch.full((1, 32), expected))


def test_mamba_block_can_run_without_residual(monkeypatch):
    class _ConstantMixer(nn.Module):
        def __init__(self, **kwargs):
            super().__init__()

        def forward(self, x):
            return torch.full_like(x, 2.0)

    monkeypatch.setitem(sys.modules, "mamba_ssm", SimpleNamespace(Mamba=_ConstantMixer))
    from models.mamba_model import MambaBlock

    x = torch.ones(1, 2, 4)
    block = MambaBlock(dim=4, dropout=0.0, residual=False).eval()
    block.norm = nn.Identity()
    assert torch.equal(block(x), torch.full_like(x, 2.0))

    baseline_block = MambaBlock(dim=4, dropout=0.0, residual=True).eval()
    baseline_block.norm = nn.Identity()
    assert torch.equal(baseline_block(x), torch.full_like(x, 3.0))


def test_mamba_branch_has_no_outer_residual(monkeypatch):
    module = importlib.import_module("models.mvif_net")
    monkeypatch.setattr(module, "MambaBlock", _ZeroMamba)
    model = build_model(
        "mvif-net",
        3,
        61,
        30,
        {"dim": 32, "dropout": 0.0, "graph_k": 4},
    ).eval()
    model.attention = _IdentityAttention()
    model.temporal_embed = _OnesPacketProjection(32)
    model.temporal_norm = nn.Identity()
    model.packet_position.data.zero_()
    model.branch_type.data[0].zero_()
    temporal_capture = _RecordIdentity()
    model.branch_norms[0] = temporal_capture

    model(torch.ones(1, 30, 3))

    assert all(not block.residual for block in model.temporal)
    assert torch.equal(temporal_capture.seen, torch.zeros_like(temporal_capture.seen))


def test_graph_and_dft_have_one_interlayer_residual(monkeypatch):
    model = _build_cpu(monkeypatch).eval()
    model.graph_embed = _OnesPacketProjection(32)
    graph_second = _ScaleAndRecord(3.0)
    model.graph_blocks = nn.ModuleList([_ScaleAndRecord(2.0), graph_second])
    graph_output = _RecordIdentity()
    model.graph_norm = graph_output

    model.dft_input_proj = _OnesFrequencyProjection(32)
    dft_second = _ScaleAndRecord(3.0)
    model.dft_spatial = nn.ModuleList([_ScaleAndRecord(2.0), dft_second])
    dft_output = _RecordIdentity()
    model.dft_norm = dft_output

    def fixed_adjacency(x, valid):
        identity = torch.eye(30, device=x.device).expand(x.shape[0], -1, -1)
        return identity, torch.zeros_like(identity)

    model._graph_adjacency = fixed_adjacency
    model(torch.ones(1, 30, 3))

    graph_scale = model.effective_graph_residual_scale().detach()
    dft_scale = model.effective_dft_residual_scale().detach()
    torch.testing.assert_close(graph_second.seen, torch.full_like(graph_second.seen, 2.0) + graph_scale)
    torch.testing.assert_close(graph_output.seen, torch.full_like(graph_output.seen, 6.0) + 3.0 * graph_scale)
    torch.testing.assert_close(dft_second.seen, torch.full_like(dft_second.seen, 2.0) + dft_scale)
    torch.testing.assert_close(dft_output.seen, torch.full_like(dft_output.seen, 6.0) + 3.0 * dft_scale)


def test_open_and_closed_classifier_sizes(monkeypatch):
    open_model = _build_cpu(monkeypatch, classes=61)
    closed_model = _build_cpu(monkeypatch, classes=60)
    assert open_model(torch.randn(2, 30, 3)).shape == (2, 61)
    assert closed_model(torch.randn(2, 30, 3)).shape == (2, 60)
