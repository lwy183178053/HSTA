from __future__ import annotations

import argparse
from pathlib import Path

import torch
import yaml

from data.dataset import make_loaders
from models import build_model
from train import eval_model, load_model_state
from utils import save_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    if args.config:
        with open(args.config, encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle)
    else:
        cfg = checkpoint["config"]

    device = "cuda" if torch.cuda.is_available() and not cfg.get("cpu", False) else "cpu"
    loaders = make_loaders(
        cfg["data_csv"],
        seq_len=int(cfg.get("seq_len", 30)),
        batch_size=int(cfg.get("batch_size", 256)),
        eval_batch_size=int(cfg.get("eval_batch_size", min(int(cfg.get("batch_size", 256)), 512))),
        seed=int(cfg.get("seed", 599)),
        num_workers=int(cfg.get("num_workers", 0)),
        train_unknown=bool(cfg.get("train_unknown", True)),
    )
    model = build_model(
        cfg["model"],
        input_dim=loaders["input_dim"],
        num_classes=loaders["num_classes"],
        seq_len=loaders["seq_len"],
        cfg=cfg.get("model_cfg", {}),
    ).to(device)
    state = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
    load_model_state(model, state, context=str(args.checkpoint))
    use_amp = bool(cfg.get("amp", True)) and str(device).startswith("cuda")
    reject_threshold = checkpoint.get("reject_threshold") if isinstance(checkpoint, dict) else None
    if reject_threshold is None:
        metrics_path = Path(args.checkpoint).with_name("metrics.json")
        if metrics_path.exists():
            import json
            with metrics_path.open(encoding="utf-8") as handle:
                reject_threshold = json.load(handle).get("reject_threshold")
    metrics, _, _ = eval_model(
        model,
        loaders[args.split],
        device,
        amp=use_amp,
        unknown_index=loaders.get("unknown_index"),
        classes=loaders.get("classes"),
        reject_threshold=reject_threshold,
        source_groups=loaders.get(f"{args.split}_source_groups"),
    )
    payload = {
        "split": args.split,
        "metrics": metrics,
        "reject_threshold": reject_threshold,
        "checkpoint": str(Path(args.checkpoint).resolve()),
    }
    print(payload)
    if args.out:
        save_json(payload, args.out)


if __name__ == "__main__":
    main()
