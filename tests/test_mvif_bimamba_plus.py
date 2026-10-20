import torch
from torch import nn

from models import build_model
from models.mvif_bimamba_plus import BiMambaPlusEncoder, MambaPlusMixer


def _build(classes=61):
    return build_model(
        "mvif-bimamba-plus",
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


def test_single_bimamba_plus_layer_and_no_graph_residual():
    model = _build()
    assert isinstance(model.temporal, BiMambaPlusEncoder)
    assert isinstance(model.temporal.forward_mixer, MambaPlusMixer)
    assert isinstance(model.temporal.backward_mixer, MambaPlusMixer)
    assert len(model.graph_blocks) == 2
    assert all(isinstance(norm, nn.Identity) for norm in [model.branch_norms[0]])
    assert not hasattr(model, "temporal_norm")
    assert not hasattr(model, "graph_residual_logit")
    assert all(not hasattr(block, "residual") for block in model.graph_blocks)
    assert model.token_count == 76
    assert [block.conv.kernel_size for block in model.dft_spatial] == [(1,), (3,)]


def test_bimamba_reverse_path_respects_each_valid_length():
    torch.manual_seed(7)
    encoder = BiMambaPlusEncoder(16, d_state=4, d_conv=3, expand=2, dropout=0.0, mlp_ratio=2).eval()
    batch = torch.randn(2, 12, 16)
    mask = torch.arange(12).unsqueeze(0) < torch.tensor([[7], [11]])
    batch = batch * mask.unsqueeze(-1)

    together = encoder(batch, mask)
    alone = encoder(batch[:1, :7], mask[:1, :7])
    torch.testing.assert_close(together[0, :7], alone[0])
    assert torch.count_nonzero(together[0, 7:]) == 0


def test_dynamic_edges_and_learnable_dft_receive_gradients():
    torch.manual_seed(11)
    model = _build(classes=61).train()
    x = torch.randn(3, 30, 3)
    x[0, 26:] = 0.0
    x[1, 28:] = 0.0
    labels = torch.tensor([0, 1, 2])
    logits = model(x)
    loss = nn.functional.cross_entropy(logits, labels)
    loss.backward()

    assert logits.shape == (3, 61)
    assert torch.isfinite(logits).all() and torch.isfinite(loss)
    assert model.last_branch_gate.shape == (3, 3)
    assert model.frequency_response.grad is not None
    assert torch.isfinite(model.frequency_response.grad).all()
    for block in model.graph_blocks:
        assert block.query.weight.grad is not None
        assert torch.isfinite(block.query.weight.grad).all()
        adjacency = block.last_similarity_adjacency
        assert adjacency is not None and torch.isfinite(adjacency).all()
        assert torch.count_nonzero(adjacency[0, 26:, :]) == 0


def test_variant_supports_closed_set_output():
    model = _build(classes=60).eval()
    with torch.no_grad():
        assert model(torch.randn(2, 30, 3)).shape == (2, 60)
