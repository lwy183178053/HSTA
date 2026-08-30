import unittest
import importlib.util

import torch

from models import build_model
from models.transformer import MultiHeadSelfAttention


class RecentJournalBaselineTests(unittest.TestCase):
    def test_recent_models_accept_shared_packet_input(self):
        for name in ("srvit", "trafficaudio", "bpf_gnn"):
            with self.subTest(model=name):
                model = build_model(
                    name,
                    input_dim=3,
                    num_classes=40,
                    seq_len=30,
                    cfg={"dim": 64, "dropout": 0.0},
                )
                x = torch.randn(2, 30, 3, requires_grad=True)
                logits = model(x)
                self.assertEqual(tuple(logits.shape), (2, 40))
                loss = logits.square().mean()
                loss.backward()
                self.assertTrue(torch.isfinite(logits).all())
                self.assertTrue(torch.isfinite(x.grad).all())

    def test_srvit_exposes_multiscale_patches_and_relative_bias(self):
        model = build_model(
            "srvit",
            input_dim=3,
            num_classes=40,
            seq_len=30,
            cfg={"dim": 64, "depth": 2, "heads": 4, "dropout": 0.0},
        )
        self.assertEqual(tuple(model.patch_kernel_sizes), (3, 5, 7))
        self.assertEqual(len(model.blocks), 2)
        self.assertEqual(tuple(model.blocks[0].attn.relative_position_bias.shape), (4, 59))

    def test_trafficaudio_uses_fixed_mfcc_shape(self):
        model = build_model(
            "trafficaudio",
            input_dim=3,
            num_classes=40,
            seq_len=30,
            cfg={"dim": 64, "dropout": 0.0},
        )
        mfcc = model.mfcc(torch.randn(2, 30, 3))
        self.assertEqual(mfcc.shape[0], 2)
        self.assertEqual(mfcc.shape[1], 8)
        self.assertGreater(mfcc.shape[2], 0)
        self.assertTrue(torch.isfinite(mfcc).all())

    def test_bpf_gnn_builds_feature_packet_flow_hierarchy(self):
        model = build_model(
            "bpf_gnn",
            input_dim=3,
            num_classes=40,
            seq_len=30,
            cfg={"dim": 64, "dropout": 0.0},
        )
        self.assertEqual(model.hierarchy, ("feature", "packet", "flow"))
        self.assertEqual(model.top_k, 4)
        self.assertEqual(model.num_subflows, 5)
        packet_adj = model.build_packet_adjacency(torch.randn(2, 30, 64))
        self.assertEqual(tuple(packet_adj.shape), (2, 30, 30))
        self.assertTrue(torch.allclose(packet_adj, packet_adj.transpose(1, 2)))


class FlashAttentionBackendTests(unittest.TestCase):
    def test_manual_and_flash_backends_have_identical_state_dict_keys(self):
        manual = MultiHeadSelfAttention(64, heads=4, dropout=0.0, attention_backend="manual")
        flash = MultiHeadSelfAttention(64, heads=4, dropout=0.0, attention_backend="flash")
        self.assertEqual(list(manual.state_dict()), list(flash.state_dict()))
        flash.load_state_dict(manual.state_dict(), strict=True)

    def test_strict_flash_rejects_cpu_instead_of_silent_fallback(self):
        attention = MultiHeadSelfAttention(64, heads=4, dropout=0.0, attention_backend="flash")
        with self.assertRaisesRegex(RuntimeError, "CUDA.*FP16.*BF16"):
            attention(torch.randn(2, 30, 64))

    @unittest.skipUnless(
        torch.cuda.is_available()
        and hasattr(torch.backends.cuda, "is_flash_attention_available")
        and torch.backends.cuda.is_flash_attention_available(),
        "A PyTorch build with a FlashAttention kernel is required for strict FlashAttention",
    )
    def test_manual_and_flash_outputs_and_input_gradients_match(self):
        manual = MultiHeadSelfAttention(64, heads=4, dropout=0.0, attention_backend="manual").cuda().eval()
        flash = MultiHeadSelfAttention(64, heads=4, dropout=0.0, attention_backend="flash").cuda().eval()
        flash.load_state_dict(manual.state_dict(), strict=True)
        manual_input = torch.randn(3, 30, 64, device="cuda", requires_grad=True)
        flash_input = manual_input.detach().clone().requires_grad_(True)

        with torch.autocast(device_type="cuda", dtype=torch.float16):
            manual_output = manual(manual_input)
            flash_output = flash(flash_input)
        manual_output.float().square().mean().backward()
        flash_output.float().square().mean().backward()

        self.assertTrue(torch.allclose(manual_output, flash_output, atol=2e-3, rtol=2e-3))
        self.assertTrue(torch.allclose(manual_input.grad, flash_input.grad, atol=2e-3, rtol=2e-3))
        self.assertEqual(flash.actual_attention_backend, "flash")

    @unittest.skipUnless(importlib.util.find_spec("mamba_ssm"), "mamba_ssm is installed in WSL")
    def test_hsta_factory_propagates_flash_backend(self):
        model = build_model(
            "hsta",
            input_dim=3,
            num_classes=40,
            seq_len=30,
            cfg={
                "dim": 64,
                "heads": 4,
                "layout": ["mamba", "mamba", "mlp", "attention", "mlp"],
                "attention_backend": "flash",
            },
        )
        attention_blocks = [block for block in model.blocks if hasattr(block, "attn")]
        self.assertEqual(len(attention_blocks), 1)
        self.assertEqual(attention_blocks[0].attn.attention_backend, "flash")


if __name__ == "__main__":
    unittest.main()
