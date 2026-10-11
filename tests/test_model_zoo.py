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
    assert full.branch_names == ("mamba", "raw_conv", "dft_conv")
    assert full.packet_position.shape == (1, 30, 256)
    assert full.frequency_position.shape == (1, 16, 256)
    assert full.branch_type.shape == (3, 256)
    assert [b[0].kernel_size for b in full.spatial] == [(1,), (3,), (5,)]
    assert [b[0].kernel_size for b in full.dft_spatial] == [(1,), (3,), (5,)]
    assert len(full.temporal) == 2
    assert isinstance(full.attention, FlashAttentionBlock)
    assert full.head.out_features == 61
    no_conv = build_model("hsta-cm", 3, 61, 30, {"use_conv": False})
    assert no_conv.token_count == 30 and no_conv.dft_spatial is None
    no_mamba = build_model("hsta-cm", 3, 61, 30, {"use_mamba": False})
    assert no_mamba.token_count == 46 and len(no_mamba.temporal) == 0
    assert isinstance(build_model("hsta-cm", 3, 61, 30, {"use_attention": False}).attention, torch.nn.Identity)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
@pytest.mark.skipif(importlib.util.find_spec("mamba_ssm") is None, reason="supported WSL mamba_ssm environment required")
@pytest.mark.parametrize("flags,tokens", [({}, 76), ({"use_conv": False}, 30), ({"use_mamba": False}, 46), ({"use_attention": False}, 76)])
def test_256_dim_61_class_cuda_forward_backward(flags, tokens):
    model = build_model("hsta-cm", 3, 61, 30, flags).cuda().train()
    seen = []
    hook = model.token_fusion.register_forward_pre_hook(lambda module, args: seen.append(args[0].shape[1]))
    with torch.autocast("cuda", dtype=torch.float16):
        logits = model(torch.randn(2, 30, 3, device="cuda"))
        loss = torch.nn.functional.cross_entropy(logits, torch.tensor([0, 60], device="cuda"))
    assert logits.shape == (2, 61) and torch.isfinite(loss)
    loss.backward()
    hook.remove()
    assert seen == [tokens]
    assert model.head.weight.grad is not None
    for module in model.modules():
        if isinstance(module, FlashSelfAttention):
            assert module.actual_attention_backend == "flash"


@pytest.mark.parametrize("name", ["hsta", "gru", "transformer", "hsta_cm_dft"])
def test_obsolete_registry_names_rejected(name):
    with pytest.raises(ValueError):
        build_model(name, 3, 61, 30)
