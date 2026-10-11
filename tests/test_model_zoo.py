"""三路模型及组件消融的结构和 CUDA 前后向检查。"""
import importlib.util
import pytest
import torch
from models import build_model
from models.flash_attention import FlashAttentionBlock, FlashSelfAttention


def test_flash_attention_is_strict():
    attention = FlashSelfAttention(32, heads=4)
    with pytest.raises(RuntimeError, match="FlashAttention"):
        attention(torch.randn(2, 30, 32))


@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="mamba_ssm required")
def test_full_model_and_ablation_token_layouts():
    full = build_model("hsta-cm", 3, 61, 30)
    assert full.token_count == 76
    assert full.branch_names == ("mamba", "packet_graph", "dft_conv")
    assert full.packet_position.shape == (1, 30, 256)
    assert full.frequency_position.shape == (1, 16, 256)
    assert full.branch_type.shape == (3, 256)
    assert len(full.graph_blocks) == 2
    assert full.graph_k == 4
    assert [b[0].kernel_size for b in full.dft_spatial] == [(1,), (3,)]
    assert isinstance(full.dft_norm, torch.nn.LayerNorm)
    assert len(full.temporal) == 2
    assert isinstance(full.attention, FlashAttentionBlock)
    assert full.head.out_features == 61
    no_gnn = build_model("hsta-cm", 3, 61, 30, {"use_gnn": False})
    assert no_gnn.token_count == 46 and len(no_gnn.graph_blocks) == 0
    assert no_gnn.branch_names == ("mamba", "dft_conv")
    no_dft = build_model("hsta-cm", 3, 61, 30, {"use_dft": False})
    assert no_dft.token_count == 60 and no_dft.dft_spatial is None
    assert no_dft.branch_names == ("mamba", "packet_graph")
    no_mamba = build_model("hsta-cm", 3, 61, 30, {"use_mamba": False})
    assert no_mamba.token_count == 46 and len(no_mamba.temporal) == 0
    assert no_mamba.branch_names == ("packet_graph", "dft_conv")
    assert isinstance(build_model("hsta-cm", 3, 61, 30, {"use_attention": False}).attention, torch.nn.Identity)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="supported WSL mamba_ssm environment required")
@pytest.mark.parametrize("flags,tokens", [({}, 76), ({"use_gnn": False}, 46), ({"use_mamba": False}, 46), ({"use_dft": False}, 60), ({"use_attention": False}, 76)])
@pytest.mark.parametrize("classes", [60, 61])
def test_256_dim_cuda_forward_backward(flags, tokens, classes):
    model = build_model("hsta-cm", 3, classes, 30, flags).cuda().train()
    seen = []
    hook = model.token_fusion.register_forward_pre_hook(lambda module, args: seen.append(args[0].shape[1]))
    with torch.autocast("cuda", dtype=torch.float16):
        logits = model(torch.randn(2, 30, 3, device="cuda"))
        loss = torch.nn.functional.cross_entropy(logits, torch.tensor([0, classes - 1], device="cuda"))
    assert logits.shape == (2, classes) and torch.isfinite(loss)
    loss.backward()
    hook.remove()
    assert seen == [tokens]
    assert model.head.weight.grad is not None
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    for branch in (model.temporal, model.graph_blocks, model.dft_spatial):
        if branch is not None and len(branch):
            assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in branch.parameters())
    for module in model.modules():
        if isinstance(module, FlashSelfAttention):
            assert module.actual_attention_backend == "flash"


@pytest.mark.parametrize("name", ["hsta", "gru", "transformer", "hsta_cm_dft"])
def test_obsolete_registry_names_rejected(name):
    with pytest.raises(ValueError):
        build_model(name, 3, 61, 30)
