"""正式 MVIF-Net 及五个基线的 CUDA 前后向验收。"""
import json
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
import mamba_ssm
from models import build_model
from models.flash_attention import FlashSelfAttention


def main():
    parser = argparse.ArgumentParser(description="CUDA model smoke test")
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="batch used for the regular forward/backward checks (default: 8)",
    )
    parser.add_argument(
        "--check-large-batch", action="store_true",
        help="also run the optional batch-4096 MVIF-Net check",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    records = []
    for name, classes, cfg in [
        ("mvif-net", 61, {"graph_k": 4, "branch_residual_init": 0.1, "residual_scale_max": 0.5}),
        ("mvif-net", 60, {"graph_k": 4, "branch_residual_init": 0.1, "residual_scale_max": 0.5}),
        ("30pkttcnet-adapted", 60, {"channels": 300, "depth": 4, "classifier_hidden": 300}),
        ("netmamba-adapted", 60, {"dim": 292, "depth": 4, "max_len": 30}),
        ("srvit", 60, {"dim": 192, "depth": 4, "mlp_ratio": 3}),
        ("trafficaudio", 60, {"dim": 416}),
        ("bpf-gnn", 60, {"dim": 664, "graph_depths": [1, 2, 1]}),
    ]:
        model = build_model(name, 3, classes, 30, {"dim": 256, **cfg}).cuda().train()
        use_amp = name != "netmamba-adapted"
        x = torch.randn(args.batch_size, 30, 3, device="cuda")
        if name == "mvif-net":
            x[0, -3:] = 0.0
            if args.batch_size > 1:
                x[1, -6:] = 0.0
        with torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
            out = model(x)
            loss = torch.nn.functional.cross_entropy(out, torch.arange(args.batch_size, device="cuda") % classes)
        assert out.shape == (args.batch_size, classes) and torch.isfinite(loss)
        loss.backward()
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        for module in model.modules():
            if isinstance(module, FlashSelfAttention):
                assert module.attention_backend == "sdpa_auto"
        records.append({"model": name, "classes": classes,
                        "parameters": sum(p.numel() for p in model.parameters()),
                        "tokens": getattr(model, "token_count", None), "batch_size": args.batch_size})
        del model, out, loss
        torch.cuda.empty_cache()
    if not args.check_large_batch:
        print(json.dumps({"torch": torch.__version__, "mamba": mamba_ssm.__version__,
                          "gpu": torch.cuda.get_device_name(), "passed": records}, ensure_ascii=False))
        return
    model = build_model(
        "mvif-net", 3, 61, 30,
        {"dim": 256, "graph_k": 4, "branch_residual_init": 0.1, "residual_scale_max": 0.5},
    ).cuda().train()
    try:
        torch.cuda.reset_peak_memory_stats()
        x = torch.randn(4096, 30, 3, device="cuda")
        y = torch.randint(0, 61, (4096,), device="cuda")
        with torch.autocast("cuda", dtype=torch.float16):
            out = model(x)
            loss = torch.nn.functional.cross_entropy(out, y)
        assert out.shape == (4096, 61) and torch.isfinite(loss)
        loss.backward()
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        records.append({"model": "mvif-net", "classes": 61, "parameters": sum(p.numel() for p in model.parameters()),
                        "tokens": model.token_count, "batch_size": 4096,
                        "peak_allocated_bytes": torch.cuda.max_memory_allocated()})
    finally:
        del model
        torch.cuda.empty_cache()
    print(json.dumps({"torch": torch.__version__, "mamba": mamba_ssm.__version__,
                      "gpu": torch.cuda.get_device_name(), "passed": records}, ensure_ascii=False))


if __name__ == "__main__":
    main()
