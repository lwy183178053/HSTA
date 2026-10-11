"""正式模型及五个基线的 CUDA 前后向验收，并验证 HSTA 的 batch 4096。"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
import mamba_ssm
from models import build_model
from models.flash_attention import FlashSelfAttention


def main():
    records = []
    for name, classes, cfg in [
        ("hsta-cm", 61, {}), ("hsta-cm", 60, {}),
        ("30pkttcnet-adapted", 60, {"depth": 5}),
        ("netmamba-adapted", 60, {"depth": 5}),
        ("srvit", 60, {"depth": 4}), ("trafficaudio", 60, {}), ("bpf-gnn", 60, {}),
    ]:
        model = build_model(name, 3, classes, 30, {"dim": 256, **cfg}).cuda().train()
        with torch.autocast("cuda", dtype=torch.float16):
            out = model(torch.randn(8, 30, 3, device="cuda"))
            loss = torch.nn.functional.cross_entropy(out, torch.arange(8, device="cuda"))
        assert out.shape == (8, classes) and torch.isfinite(loss)
        loss.backward()
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        for module in model.modules():
            if isinstance(module, FlashSelfAttention):
                assert module.actual_attention_backend == "flash"
        records.append({"model": name, "classes": classes,
                        "parameters": sum(p.numel() for p in model.parameters()),
                        "tokens": getattr(model, "token_count", None), "batch_size": 8})
        del model, out, loss
        torch.cuda.empty_cache()
    model = build_model("hsta-cm", 3, 61, 30, {"dim": 256}).cuda().train()
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
        records.append({"model": "hsta-cm", "classes": 61, "parameters": sum(p.numel() for p in model.parameters()),
                        "tokens": model.token_count, "batch_size": 4096,
                        "peak_allocated_bytes": torch.cuda.max_memory_allocated()})
    finally:
        del model
        torch.cuda.empty_cache()
    print(json.dumps({"torch": torch.__version__, "mamba": mamba_ssm.__version__,
                      "gpu": torch.cuda.get_device_name(), "passed": records}, ensure_ascii=False))


if __name__ == "__main__":
    main()
