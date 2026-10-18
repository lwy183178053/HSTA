"""CPU checks for MVIF-Net's per-flow packet graph construction."""

import importlib

import torch
from torch import nn

from models import build_model


class _IdentityMamba(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def forward(self, x):
        return x


def _graph_model(monkeypatch):
    module = importlib.import_module("models.mvif_net")
    monkeypatch.setattr(module, "MambaBlock", _IdentityMamba)
    model = build_model(
        "mvif-net",
        3,
        61,
        30,
        {"dim": 32, "graph_k": 4, "dropout": 0.0},
    ).eval()
    model.attention = nn.Identity()
    return model


def test_packet_mask_uses_standardized_zero_padding(monkeypatch):
    model = _graph_model(monkeypatch)
    model.set_input_scaler(torch.tensor([10.0, 20.0, 30.0]), torch.tensor([2.0, 4.0, 5.0]))
    padding = model.padding_value
    x = padding.view(1, 1, 3).expand(2, 30, 3).clone()
    x[0, :3] = torch.tensor([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [-2.0, 3.0, 4.0]])
    mask = model._packet_mask(x)
    assert mask.dtype == torch.bool and mask.shape == (2, 30)
    assert mask[0, :3].tolist() == [True, True, True]
    assert not mask[0, 3:].any() and not mask[1].any()


def test_graph_is_per_flow_masked_symmetric_and_normalized(monkeypatch):
    model = _graph_model(monkeypatch)
    x = torch.randn(2, 30, 3)
    valid = torch.zeros(2, 30, dtype=torch.bool)
    valid[0, :5] = True
    valid[1, :2] = True
    local, nonlocal_adj = model._graph_adjacency(x, valid)
    assert local.shape == nonlocal_adj.shape == (2, 30, 30)
    assert not local.requires_grad and not nonlocal_adj.requires_grad
    assert torch.allclose(local, local.transpose(1, 2), atol=1e-6)
    assert torch.allclose(nonlocal_adj, nonlocal_adj.transpose(1, 2), atol=1e-6)
    assert torch.count_nonzero(local[0, 5:]) == 0
    assert torch.count_nonzero(local[0, :, 5:]) == 0
    assert torch.count_nonzero(nonlocal_adj[1, 2:]) == 0
    assert torch.count_nonzero(nonlocal_adj[1, :, 2:]) == 0
    assert torch.all(local.diagonal(dim1=1, dim2=2)[0, :5] > 0)
    assert torch.all(local.diagonal(dim1=1, dim2=2)[0, 5:] == 0)
    assert torch.isfinite(local).all() and torch.isfinite(nonlocal_adj).all()


def test_graph_edges_keep_sequence_local_and_feature_nonlocal_relations(monkeypatch):
    model = _graph_model(monkeypatch)
    x = torch.randn(1, 30, 3)
    valid = torch.zeros(1, 30, dtype=torch.bool)
    valid[0, :6] = True
    local, nonlocal_adj = model._graph_adjacency(x, valid)
    assert local[0, 0, 1] > 0 and local[0, 1, 2] > 0
    assert nonlocal_adj[0, 0, 1] == 0 and nonlocal_adj[0, 1, 2] == 0
    assert torch.count_nonzero(nonlocal_adj[0, :6, :6]) > 0
    assert torch.count_nonzero(nonlocal_adj[0, 6:]) == 0
    assert torch.count_nonzero(nonlocal_adj[0, :, 6:]) == 0


def test_graph_handles_empty_and_singleton_valid_sets(monkeypatch):
    model = _graph_model(monkeypatch)
    x = torch.randn(2, 30, 3)
    valid = torch.zeros(2, 30, dtype=torch.bool)
    valid[1, 7] = True
    local, nonlocal_adj = model._graph_adjacency(x, valid)
    assert torch.count_nonzero(local[0]) == 0
    assert torch.count_nonzero(nonlocal_adj[0]) == 0
    assert local[1, 7, 7] > 0 and torch.count_nonzero(local[1]) == 1
    assert torch.count_nonzero(nonlocal_adj[1]) == 0


def test_graph_residual_blocks_have_finite_gradients(monkeypatch):
    model = _graph_model(monkeypatch).train()
    x = torch.randn(2, 30, 3, requires_grad=True)
    valid = torch.ones(2, 30, dtype=torch.bool)
    local, nonlocal_adj = model._graph_adjacency(x, valid)
    graph = model.graph_embed(x)
    for block in model.graph_blocks:
        graph = block(graph, local, nonlocal_adj)
    loss = graph.square().mean()
    loss.backward()
    assert torch.isfinite(loss)
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert all(parameter.grad is not None and torch.isfinite(parameter.grad).all() for parameter in model.graph_blocks.parameters())


def test_graph_batch_entries_are_independent(monkeypatch):
    model = _graph_model(monkeypatch)
    x = torch.randn(2, 30, 3)
    valid = torch.ones(2, 30, dtype=torch.bool)
    first, _ = model._graph_adjacency(x, valid)
    changed = x.clone()
    changed[1] += 100.0
    second, _ = model._graph_adjacency(changed, valid)
    assert torch.allclose(first[0], second[0], atol=1e-6)
