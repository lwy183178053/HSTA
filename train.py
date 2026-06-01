from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from tqdm import tqdm

from data.dataset import make_loaders
from models import build_model
from utils import count_parameters, ensure_dir, save_json, seed_everything


def _autocast(enabled: bool):
    return torch.amp.autocast(device_type="cuda", enabled=enabled)


def _grad_scaler(enabled: bool):
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except TypeError:
        return torch.cuda.amp.GradScaler(enabled=enabled)


def eval_model(model, loader, device):
    model.eval()
    criterion = nn.CrossEntropyLoss()
    losses, y_true, y_pred = [], [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            losses.append(float(criterion(logits, y).item()))
            y_true.extend(y.detach().cpu().numpy())
            y_pred.extend(logits.argmax(dim=1).detach().cpu().numpy())
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    return (
        {
            "loss": float(np.mean(losses)),
            "accuracy": float(accuracy),
            "macro_precision": float(precision),
            "macro_recall": float(recall),
            "macro_f1": float(f1),
        },
        np.asarray(y_true),
        np.asarray(y_pred),
    )


def _metric_improved(value: float, best: float, mode: str, min_delta: float) -> bool:
    if mode == "min":
        return value < best - min_delta
    return value > best + min_delta


def _mean_or_nan(values):
    finite = [float(v) for v in values if np.isfinite(float(v))]
    if not finite:
        return float("nan")
    return float(np.mean(finite))


def _load_state_dict(path: Path, device):
    checkpoint = torch.load(path, map_location=device)
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        return checkpoint["state_dict"]
    return checkpoint


def _load_training_checkpoint(path: Path, model, optimizer, scaler, scheduler, device, load_optimizer: bool = True):
    checkpoint = torch.load(path, map_location=device)
    if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint:
        raise ValueError(f"Invalid training checkpoint: {path}")
    model.load_state_dict(checkpoint["state_dict"])
    if load_optimizer and checkpoint.get("optimizer_state_dict") is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if load_optimizer and checkpoint.get("scaler_state_dict") is not None:
        scaler.load_state_dict(checkpoint["scaler_state_dict"])
    if load_optimizer and scheduler is not None and checkpoint.get("scheduler_state_dict") is not None:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    return checkpoint


def require_pretrained_for_lora(cfg: dict) -> None:
    model_name = str(cfg.get("model", "")).lower()
    model_cfg = cfg.get("model_cfg", {}) or {}
    is_lora = model_name.endswith("_lora") or bool(model_cfg.get("lora", False))
    if is_lora and not cfg.get("pretrained_path"):
        raise ValueError(
            "LoRA fine-tuning requires pretrained_path. "
            "Train the full hybrid main model first, then point pretrained_path to its best.pt."
        )


def load_pretrained_weights_if_needed(model, cfg: dict, device):
    pretrained_path = cfg.get("pretrained_path")
    if not pretrained_path:
        return {"loaded": False}

    pretrained_path = Path(pretrained_path)
    if not pretrained_path.exists():
        raise FileNotFoundError(
            f"pretrained_path not found: {pretrained_path}. "
            "Train the referenced base model first, or update pretrained_path in the config."
        )

    source_state = _load_state_dict(pretrained_path, device)
    target_state = model.state_dict()
    reset_head = bool(cfg.get("reset_head", False))
    loaded = {}
    skipped = []

    for key, value in source_state.items():
        candidates = [key]
        if key.endswith(".weight") or key.endswith(".bias"):
            stem, suffix = key.rsplit(".", 1)
            candidates.append(f"{stem}.linear.{suffix}")

        matched = False
        for candidate in candidates:
            if reset_head and candidate.startswith("head."):
                continue
            if candidate in target_state and tuple(target_state[candidate].shape) == tuple(value.shape):
                loaded[candidate] = value
                matched = True
                break
        if not matched:
            skipped.append(key)

    missing, unexpected = model.load_state_dict(loaded, strict=False)
    info = {
        "loaded": True,
        "path": str(pretrained_path),
        "loaded_keys": len(loaded),
        "skipped_keys": len(skipped),
        "missing_keys": list(missing),
        "unexpected_keys": list(unexpected),
        "reset_head": reset_head,
    }
    print(
        f"[pretrained] loaded {info['loaded_keys']} keys from {pretrained_path}, "
        f"skipped {info['skipped_keys']}, reset_head={reset_head}"
    )
    return info


def train_one(cfg: dict):
    seed_everything(int(cfg.get("seed", 42)))
    require_pretrained_for_lora(cfg)
    output_dir = Path(cfg.get("output_dir", "results")) / cfg["exp_name"]
    ensure_dir(output_dir)

    device = "cuda" if torch.cuda.is_available() and not cfg.get("cpu", False) else "cpu"
    loaders = make_loaders(
        cfg["data_csv"],
        seq_len=int(cfg.get("seq_len", 30)),
        feature_cols=cfg.get("feature_cols"),
        batch_size=int(cfg.get("batch_size", 256)),
        test_size=float(cfg.get("test_size", 0.2)),
        val_size=float(cfg.get("val_size", 0.1)),
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
    adapted_note = str(getattr(model, "adapted_note", ""))
    if adapted_note:
        print(f"[model] {adapted_note}")
    best_path = output_dir / "best.pt"
    latest_path = output_dir / "latest.pt"
    summary_path = output_dir / "summary.csv"
    history_path = output_dir / "history.csv"
    resume_enabled = bool(cfg.get("resume", True))
    extend_training = bool(cfg.get("extend_training", False))
    resume_candidate = resume_enabled and latest_path.exists() and (extend_training or not summary_path.exists())
    resume_best_only_candidate = (
        resume_enabled
        and best_path.exists()
        and history_path.exists()
        and not latest_path.exists()
        and not summary_path.exists()
    )
    if resume_candidate or resume_best_only_candidate:
        checkpoint_path = latest_path if resume_candidate else best_path
        pretrained_info = {"loaded": False, "skipped_for_resume": True, "checkpoint": str(checkpoint_path)}
    else:
        pretrained_info = load_pretrained_weights_if_needed(model, cfg, device)

    total_params, trainable_params = count_parameters(model)
    trainable = [param for param in model.parameters() if param.requires_grad]
    if not trainable:
        raise ValueError("No trainable parameters. Check LoRA freeze settings.")

    optimizer = torch.optim.AdamW(
        trainable,
        lr=float(cfg.get("lr", 5e-4)),
        weight_decay=float(cfg.get("weight_decay", 1e-4)),
    )
    criterion = nn.CrossEntropyLoss()
    history = []
    start = time.time()
    previous_seconds = 0.0

    epochs = int(cfg.get("epochs", 50))
    patience = int(cfg.get("patience", 10))
    early_metric = str(cfg.get("early_stop_metric", "val_macro_f1"))
    early_mode = str(cfg.get("early_stop_mode", "min" if early_metric.endswith("loss") else "max"))
    min_delta = float(cfg.get("early_stop_min_delta", 0.0))
    best = float("inf") if early_mode == "min" else -float("inf")
    best_epoch = 0
    bad_epochs = 0
    stopped_epoch = 0
    stop_reason = ""

    scheduler = None
    scheduler_info = {"enabled": False}
    if cfg.get("lr_scheduler", "none") == "reduce_on_plateau":
        scheduler_metric = str(cfg.get("lr_scheduler_metric", early_metric))
        scheduler_mode = str(cfg.get("lr_scheduler_mode", "min" if scheduler_metric.endswith("loss") else "max"))
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode=scheduler_mode,
            factor=float(cfg.get("lr_factor", 0.5)),
            patience=int(cfg.get("lr_patience", 3)),
            threshold=float(cfg.get("lr_threshold", min_delta)),
            threshold_mode="abs",
            min_lr=float(cfg.get("min_lr", 1e-6)),
        )
        scheduler_info = {"enabled": True, "type": "reduce_on_plateau", "metric": scheduler_metric, "mode": scheduler_mode}

    use_amp = bool(cfg.get("amp", True)) and device == "cuda"
    scaler = _grad_scaler(use_amp)
    start_epoch = 1
    if resume_candidate:
        load_optimizer = not (extend_training and bool(cfg.get("reset_optimizer_on_extend", True)))
        checkpoint = _load_training_checkpoint(latest_path, model, optimizer, scaler, scheduler, device, load_optimizer=load_optimizer)
        history = checkpoint.get("history", [])
        start_epoch = int(checkpoint.get("epoch", 0)) + 1
        best = float(checkpoint.get("best", best))
        best_epoch = int(checkpoint.get("best_epoch", best_epoch))
        bad_epochs = int(checkpoint.get("bad_epochs", bad_epochs))
        stopped_epoch = int(checkpoint.get("stopped_epoch", stopped_epoch))
        stop_reason = str(checkpoint.get("stop_reason", stop_reason))
        previous_seconds = float(checkpoint.get("elapsed_seconds", 0.0))
        pretrained_info = checkpoint.get("pretrained", pretrained_info)
        if extend_training and bool(cfg.get("reset_patience_on_extend", True)):
            bad_epochs = 0
            stopped_epoch = 0
            stop_reason = ""
        start = time.time()
        action = "extending" if extend_training else "continuing"
        optimizer_note = "reset optimizer" if not load_optimizer else "restored optimizer"
        print(f"[resume] loaded {latest_path}; {action} at epoch {start_epoch}/{epochs} ({optimizer_note})")
    elif resume_best_only_candidate:
        history_df = pd.read_csv(history_path)
        if early_metric in history_df.columns:
            metric_values = pd.to_numeric(history_df[early_metric], errors="coerce")
            finite_mask = np.isfinite(metric_values.to_numpy(dtype=float))
        else:
            metric_values = pd.Series(dtype=float)
            finite_mask = np.asarray([], dtype=bool)
        if finite_mask.any():
            finite_metrics = metric_values[finite_mask]
            best_idx = finite_metrics.idxmin() if early_mode == "min" else finite_metrics.idxmax()
            history = history_df.to_dict("records")
            best = float(history_df.loc[best_idx, early_metric])
            best_epoch = int(history_df.loc[best_idx, "epoch"])
            stopped_epoch = int(history_df.iloc[-1]["epoch"])
            stop_reason = "recovered_interrupted_best_checkpoint"
            start_epoch = epochs + 1
            print(f"[resume] no latest.pt; evaluating existing best.pt from interrupted run at epoch {best_epoch}")
        else:
            print(f"[resume] {history_path} has no finite {early_metric}; restarting {cfg['exp_name']}")

    def save_latest(epoch: int):
        torch.save(
            {
                "state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
                "config": cfg,
                "input_dim": loaders["input_dim"],
                "num_classes": loaders["num_classes"],
                "classes": loaders["classes"],
                "feature_cols": loaders["feature_cols"],
                "epoch": int(epoch),
                "history": history,
                "best": float(best),
                "best_epoch": int(best_epoch),
                "bad_epochs": int(bad_epochs),
                "stopped_epoch": int(stopped_epoch),
                "stop_reason": stop_reason,
                "pretrained": pretrained_info,
                "scheduler": scheduler_info,
                "elapsed_seconds": float(previous_seconds + time.time() - start),
            },
            latest_path,
        )

    for epoch in range(start_epoch, epochs + 1):
        model.train()
        losses = []
        nonfinite_train_batches = 0
        epoch_stop_reason = ""
        lr_before = float(optimizer.param_groups[0]["lr"])
        for batch_idx, (x, y) in enumerate(tqdm(loaders["train"], desc=f"{cfg['exp_name']} ep{epoch}/{epochs}", leave=False), start=1):
            x = x.to(device)
            y = y.to(device)
            optimizer.zero_grad(set_to_none=True)
            with _autocast(use_amp):
                loss = criterion(model(x), y)
            if not torch.isfinite(loss):
                nonfinite_train_batches += 1
                epoch_stop_reason = f"nonfinite_train_loss_batch_{batch_idx}"
                print(f"[warn] {cfg['exp_name']} epoch {epoch}: non-finite train loss at batch {batch_idx}; stopping this experiment")
                break
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            loss_value = float(loss.detach().item())
            losses.append(loss_value)

        if epoch_stop_reason:
            row = {
                "epoch": epoch,
                "lr": lr_before,
                "train_loss": _mean_or_nan(losses),
                "val_loss": float("nan"),
                "val_accuracy": float("nan"),
                "val_macro_precision": float("nan"),
                "val_macro_recall": float("nan"),
                "val_macro_f1": float("nan"),
                "lr_after": float(optimizer.param_groups[0]["lr"]),
                "best_epoch": best_epoch,
                "bad_epochs": bad_epochs,
                "nonfinite_train_batches": nonfinite_train_batches,
                "stop_reason": epoch_stop_reason,
            }
            history.append(row)
            pd.DataFrame(history).to_csv(output_dir / "history.csv", index=False)
            stopped_epoch = epoch
            stop_reason = epoch_stop_reason
            save_latest(epoch)
            break

        val_metrics, _, _ = eval_model(model, loaders["val"], device)
        row = {
            "epoch": epoch,
            "lr": lr_before,
            "train_loss": _mean_or_nan(losses),
            **{f"val_{key}": value for key, value in val_metrics.items()},
        }
        metric_value = float(row[early_metric])
        if not np.isfinite(metric_value):
            bad_epochs += 1
            row["lr_after"] = float(optimizer.param_groups[0]["lr"])
            row["best_epoch"] = best_epoch
            row["bad_epochs"] = bad_epochs
            row["nonfinite_train_batches"] = nonfinite_train_batches
            row["stop_reason"] = f"nonfinite_{early_metric}"
            history.append(row)
            pd.DataFrame(history).to_csv(output_dir / "history.csv", index=False)
            stopped_epoch = epoch
            stop_reason = row["stop_reason"]
            save_latest(epoch)
            print(f"[warn] {cfg['exp_name']} epoch {epoch}: non-finite {early_metric}; stopping this experiment")
            break
        if _metric_improved(metric_value, best, early_mode, min_delta):
            best = metric_value
            best_epoch = epoch
            bad_epochs = 0
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "config": cfg,
                    "input_dim": loaders["input_dim"],
                    "num_classes": loaders["num_classes"],
                    "classes": loaders["classes"],
                    "feature_cols": loaders["feature_cols"],
                },
                best_path,
            )
        else:
            bad_epochs += 1
        if scheduler is not None:
            scheduler.step(float(row[scheduler_info["metric"]]))
        row["lr_after"] = float(optimizer.param_groups[0]["lr"])
        row["best_epoch"] = best_epoch
        row["bad_epochs"] = bad_epochs
        row["nonfinite_train_batches"] = nonfinite_train_batches
        if bad_epochs >= patience:
            stopped_epoch = epoch
            stop_reason = "early_stopping_patience"
            row["stop_reason"] = stop_reason
        else:
            row["stop_reason"] = ""
        history.append(row)
        pd.DataFrame(history).to_csv(output_dir / "history.csv", index=False)
        save_latest(epoch)
        if bad_epochs >= patience:
            break

    if not best_path.exists():
        raise RuntimeError(f"No valid checkpoint was saved for {cfg['exp_name']}. Check history.csv for non-finite losses.")
    model.load_state_dict(_load_state_dict(best_path, device))
    test_metrics, y_true, y_pred = eval_model(model, loaders["test"], device)
    report = classification_report(y_true, y_pred, target_names=loaders["classes"], zero_division=0, output_dict=True)
    model_cfg = cfg.get("model_cfg", {}) or {}
    base_layout = model_cfg.get("layout", [])
    block_repeats = int(model_cfg.get("block_repeats", 1))
    expanded_layout = base_layout * block_repeats if base_layout else []
    result = {
        "exp_name": cfg["exp_name"],
        "model": cfg["model"],
        "seed": int(cfg.get("seed", 42)),
        "layout": "|".join(expanded_layout),
        "block_repeats": block_repeats,
        "hybrid_layers": len(expanded_layout),
        "device": device,
        "seq_len": int(cfg.get("seq_len", 30)),
        "total_params": total_params,
        "trainable_params": trainable_params,
        "trainable_ratio": trainable_params / max(total_params, 1),
        "epochs_run": len(history),
        "best_epoch": best_epoch,
        "stopped_epoch": stopped_epoch,
        "stop_reason": stop_reason,
        "best_val_metric": float(best),
        "early_stop_metric": early_metric,
        "seconds": float(previous_seconds + time.time() - start),
        **{f"test_{key}": value for key, value in test_metrics.items()},
    }
    if adapted_note:
        result["adapted_note"] = adapted_note
    save_json(
        {
            "result": result,
            "classes": loaders["classes"],
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
            "classification_report": report,
            "config": cfg,
            "pretrained": pretrained_info,
            "scheduler": scheduler_info,
        },
        output_dir / "metrics.json",
    )
    pd.DataFrame([result]).to_csv(output_dir / "summary.csv", index=False)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    if "base" in cfg:
        raise ValueError("This file contains multiple experiments. Use run_experiments.py for configs with base/experiments.")
    print(train_one(cfg))


if __name__ == "__main__":
    main()
