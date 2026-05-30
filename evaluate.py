from __future__ import annotations

import argparse
from pathlib import Path

import torch
import yaml

from data.dataset import make_loaders
from models import build_model
from train import eval_model
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
        seed=int(cfg.get("seed", 42)),
        num_workers=int(cfg.get("num_workers", 0)),
    )
    model = build_model(
        cfg["model"],
        input_dim=loaders["input_dim"],
        num_classes=loaders["num_classes"],
        seq_len=loaders["seq_len"],
        cfg=cfg.get("model_cfg", {}),
    ).to(device)
    state = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
    model.load_state_dict(state)
    metrics, _, _ = eval_model(model, loaders[args.split], device)
    payload = {"split": args.split, "metrics": metrics, "checkpoint": str(Path(args.checkpoint).resolve())}
    print(payload)
    if args.out:
        save_json(payload, args.out)


if __name__ == "__main__":
    main()
