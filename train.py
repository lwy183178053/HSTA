from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from tqdm import tqdm

from data.dataset import make_loaders
from data.open_set import open_set_metrics, unknown_score_from_logits
from models import build_model
from utils import count_parameters, ensure_dir, save_json, seed_everything


# ``metrics.json`` remains the complete audit record.  CSV summaries are kept
# intentionally small so model comparisons do not repeat every raw/threshold
# field and per-class report column.
SUMMARY_COLUMNS = (
    "exp_name",
    "model",
    "seed",
    "train_unknown",
    "early_stop_metric",
    "layout",
    "epochs_run",
    "best_epoch",
    "stop_reason",
    "best_val_metric",
    "effective_train_batch_size",
    "train_batch_size",
    "eval_batch_size",
    "train_microbatch_sizes",
    "train_microbatch_size_min",
    "train_microbatch_size_max",
    "train_microbatch_fallback_used",
    "total_params",
    "trainable_params",
    "seconds",
    "test_accuracy",
    "test_macro_f1",
) + tuple(
    f"test_{view}_{metric}" for view in ("raw", "threshold")
    for metric in ("open_set_accuracy", "open_set_macro_f1", "known_accuracy", "known_macro_f1",
                   "unknown_precision", "unknown_recall", "unknown_f1", "unknown_auroc",
                   "unknown_aupr", "known_false_unknown_rate", "unknown_false_known_rate")
)


def compact_result(result: dict) -> dict:
    """Return the paper-facing scalar result view while retaining full JSON."""

    return {column: result.get(column, float("nan")) for column in SUMMARY_COLUMNS}


def _autocast(enabled: bool):
    return torch.amp.autocast(device_type="cuda", enabled=enabled)


def _grad_scaler(enabled: bool):
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except TypeError:
        return torch.cuda.amp.GradScaler(enabled=enabled)


def _is_cuda_oom(error: RuntimeError) -> bool:
    out_of_memory_type = getattr(torch.cuda, "OutOfMemoryError", ())
    return (bool(out_of_memory_type) and isinstance(error, out_of_memory_type)) or "out of memory" in str(error).lower()


def _train_accumulated_batch(
    model,
    x,
    y,
    device,
    criterion,
    optimizer,
    scaler,
    use_amp: bool,
    microbatch_candidates: list[int],
) -> tuple[float, int]:
    """Apply one effective-batch optimizer step, retrying CUDA OOM at smaller microbatches."""
    batch_count = int(y.shape[0])
    candidates = list(dict.fromkeys(min(batch_count, int(size)) for size in microbatch_candidates if int(size) > 0))
    if not candidates:
        raise ValueError("microbatch_candidates must contain a positive size")
    cuda_device = str(device).startswith("cuda")

    for candidate_index, microbatch_size in enumerate(candidates):
        optimizer.zero_grad(set_to_none=True)
        loss_sum = 0.0
        x_micro = y_micro = logits = loss = None
        try:
            for start in range(0, batch_count, microbatch_size):
                end = min(start + microbatch_size, batch_count)
                x_micro = x[start:end].to(device, non_blocking=True)
                y_micro = y[start:end].to(device, non_blocking=True)
                with _autocast(bool(use_amp and cuda_device)):
                    logits = model(x_micro)
                    loss = criterion(logits, y_micro)
                    auxiliary_loss = getattr(model, "auxiliary_loss", None)
                    if auxiliary_loss is not None:
                        extra_loss = auxiliary_loss(y_micro)
                        if extra_loss is not None:
                            loss = loss + extra_loss
                if not torch.isfinite(loss):
                    optimizer.zero_grad(set_to_none=True)
                    return float(loss.detach().item()), microbatch_size
                count = end - start
                loss_sum += float(loss.detach().item()) * count
                scaler.scale(loss * (count / batch_count)).backward()
                del x_micro, y_micro, logits, loss
        except RuntimeError as error:
            optimizer.zero_grad(set_to_none=True)
            if not cuda_device or not _is_cuda_oom(error):
                raise
            x_micro = y_micro = logits = loss = None
            torch.cuda.empty_cache()
            if candidate_index + 1 >= len(candidates):
                tried = ", ".join(str(value) for value in candidates)
                raise RuntimeError(
                    f"CUDA out of memory for effective batch {batch_count}; "
                    f"all microbatch sizes failed: {tried}"
                ) from error
            next_size = candidates[candidate_index + 1]
            print(f"[batch] CUDA OOM at microbatch {microbatch_size}; retrying with {next_size}")
            continue

        # Keep optimizer.step outside the retry block: retrying after a partial
        # optimizer update could silently apply a batch twice.
        scaler.step(optimizer)
        scaler.update()
        return loss_sum / batch_count, microbatch_size

    raise AssertionError("unreachable microbatch retry state")


def eval_model(
    model,
    loader,
    device,
    amp: bool = False,
    unknown_index: int | None = None,
    classes=None,
    reject_threshold: float | None = None,
    source_groups=None,
):
    model.eval()
    criterion = nn.CrossEntropyLoss()
    losses, y_true, y_pred, logits_all = [], [], [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            with _autocast(bool(amp and str(device).startswith("cuda"))):
                logits = model(x)
                # Closed-set baselines have no unknown output neuron. Their
                # validation/test batches still contain unknown examples, so
                # compute CE only for labels represented by the model head.
                valid_labels = y < logits.shape[1]
                loss = criterion(logits[valid_labels], y[valid_labels]) if torch.any(valid_labels) else logits.sum() * 0.0
            losses.append(float(loss.item()))
            y_true.extend(y.detach().cpu().numpy())
            y_pred.extend(logits.argmax(dim=1).detach().cpu().numpy())
            logits_all.append(logits.detach().float().cpu().numpy())
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)
    # For a closed-set baseline, unknown labels are deliberately excluded
    # from the supervised validation metric because the head has no unknown
    # class. They are retained in the returned arrays for open-set scoring.
    logits_preview = logits_all[0] if logits_all else None
    known_eval_mask = None
    if unknown_index is not None and logits_preview is not None and logits_preview.shape[1] <= int(unknown_index):
        known_eval_mask = y_true != int(unknown_index)
    metric_y_true = y_true[known_eval_mask] if known_eval_mask is not None else y_true
    metric_y_pred = y_pred[known_eval_mask] if known_eval_mask is not None else y_pred
    accuracy = accuracy_score(metric_y_true, metric_y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(metric_y_true, metric_y_pred, average="macro", zero_division=0)
    metrics = {
            "loss": float(np.mean(losses)),
            "accuracy": float(accuracy),
            "macro_precision": float(precision),
            "macro_recall": float(recall),
            "macro_f1": float(f1),
        }
    logits = np.concatenate(logits_all)
    if unknown_index is not None:
        known_mask = y_true != int(unknown_index)
        known_labels = np.arange(len(classes or []), dtype=np.int64)
        if known_labels.size and int(unknown_index) < known_labels.size:
            known_labels = known_labels[known_labels != int(unknown_index)]
        if np.any(known_mask):
            known_precision, known_recall, known_f1, _ = precision_recall_fscore_support(
                y_true[known_mask], y_pred[known_mask], labels=known_labels, average="macro", zero_division=0,
            )
            metrics.update({
                "known_macro_precision": float(known_precision),
                "known_macro_recall": float(known_recall),
                "known_macro_f1": float(known_f1),
            })
    # Persist both protocol views.  ``raw`` is the classifier argmax; the
    # ``threshold`` view applies the validation-calibrated reject threshold.
    # Keeping both namespaces in every result makes it impossible to confuse a
    # closed-set argmax score with the open-set operating point.
    raw_open = open_set_metrics(y_true, y_pred, logits, classes, unknown_index, None)
    threshold_open = open_set_metrics(y_true, y_pred, logits, classes, unknown_index, reject_threshold)
    for prefix, open_metrics in (("raw", raw_open), ("threshold", threshold_open)):
        for key, value in open_metrics.items():
            metrics[f"{prefix}_{key}"] = value

    # Legacy unprefixed fields retain the threshold operating point so existing
    # summaries continue to read the calibrated result.
    metrics.update(threshold_open)
    metrics["raw_open_set_macro_f1"] = raw_open["open_set_macro_f1"]
    metrics["threshold_open_set_macro_f1"] = threshold_open["open_set_macro_f1"]
    metrics["open_set_macro_f1"] = threshold_open["open_set_macro_f1"]
    if source_groups is not None:
        source_groups = np.asarray(source_groups, dtype=str).reshape(-1)
        if source_groups.shape[0] != y_true.shape[0]:
            raise ValueError("source_groups must align with evaluation samples")
        grouped = {}
        for group in sorted(set(source_groups.tolist())):
            mask = source_groups == group
            if not np.any(mask):
                continue
            grouped[group] = {
                "count": int(np.sum(mask)),
                "raw": open_set_metrics(
                    y_true[mask], y_pred[mask], logits[mask], classes, unknown_index, None,
                ),
                "threshold": open_set_metrics(
                    y_true[mask], y_pred[mask], logits[mask], classes, unknown_index, reject_threshold,
                ),
            }
            if group in {"unknown_test_heldout", "noise_test"}:
                # Pair this unknown source with the known test population
                # so precision, AUROC and AUPR have both positive/negative data.
                mixed = mask | (y_true != int(unknown_index))
                grouped[group]["mixed_with_known"] = {
                    "raw": open_set_metrics(y_true[mixed], y_pred[mixed], logits[mixed], classes, unknown_index),
                    "threshold": open_set_metrics(y_true[mixed], y_pred[mixed], logits[mixed], classes, unknown_index, reject_threshold),
                }
        metrics["source_group_metrics"] = grouped
    return (
        metrics,
        y_true,
        y_pred,
    )


def calibrate_reject_threshold(model, loader, device, amp: bool, unknown_index: int | None, quantile: float) -> float | None:
    """Calibrate a closed-set reject threshold using known validation flows only."""
    if unknown_index is None:
        return None
    model.eval()
    scores = []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with _autocast(bool(amp and str(device).startswith("cuda"))):
                logits = model(x)
            logits_np = logits.detach().float().cpu().numpy()
            y_np = y.detach().cpu().numpy()
            scores.extend(unknown_score_from_logits(logits_np, unknown_index)[y_np != int(unknown_index)].tolist())
    if not scores:
        return None
    return float(np.quantile(np.asarray(scores, dtype=np.float64), float(quantile)))


def _metric_improved(value: float, best: float, mode: str, min_delta: float) -> bool:
    if mode == "min":
        return value < best - min_delta
    return value > best + min_delta


def _mean_or_nan(values):
    finite = [float(v) for v in values if np.isfinite(float(v))]
    if not finite:
        return float("nan")
    return float(np.mean(finite))


def _attention_runtime_metadata(model, cfg: dict, device: str, use_amp: bool) -> dict:
    attention_modules = [module for module in model.modules() if module.__class__.__name__ == "FlashSelfAttention"]
    requested = sorted({str(getattr(module, "attention_backend", "flash")) for module in attention_modules})
    actual = sorted({str(getattr(module, "actual_attention_backend", "uninitialized")) for module in attention_modules})
    model_cfg = cfg.get("model_cfg", {}) or {}
    return {
        "requested_backend": "flash",
        "module_requested_backends": requested,
        "actual_backends": actual,
        "flash_attention_enforced": any(
            bool(getattr(module, "flash_attention_enforced", False)) for module in attention_modules
        ),
        "amp_enabled": bool(use_amp),
        "amp_dtype": "float16" if use_amp else "float32",
        "mamba_blocks_fp32": any(
            module.__class__.__name__ in {"MambaBlock", "MambaPlusMixer"}
            for module in model.modules()
        ),
        "device": str(device),
        "cuda_device": torch.cuda.get_device_name(0) if str(device).startswith("cuda") else "",
    }


def _load_state_dict(path: Path, device):
    checkpoint = torch.load(path, map_location=device)
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        return checkpoint["state_dict"]
    return checkpoint


def load_model_state(model, state_dict: dict, context: str = "checkpoint"):
    """Load a checkpoint with the current model layout.

    The active 60-class protocol starts every run from a fresh model.  Resume
    checkpoints therefore must match the current architecture exactly; legacy
    parameters are intentionally not migrated or silently ignored.
    """
    del context
    model.load_state_dict(state_dict, strict=True)


def _load_training_checkpoint(path: Path, model, optimizer, scaler, scheduler, device, load_optimizer: bool = True):
    checkpoint = torch.load(path, map_location=device)
    if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint:
        raise ValueError(f"Invalid training checkpoint: {path}")
    load_model_state(model, checkpoint["state_dict"], context=str(path))
    optimizer_restored = bool(load_optimizer)
    if load_optimizer and checkpoint.get("optimizer_state_dict") is not None:
        try:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        except ValueError as error:
            if "parameter group" not in str(error).lower():
                raise
            optimizer_restored = False
            print(f"[checkpoint] {path}: optimizer state reset after parameter layout changed")
    if optimizer_restored and load_optimizer and checkpoint.get("scaler_state_dict") is not None:
        scaler.load_state_dict(checkpoint["scaler_state_dict"])
    if optimizer_restored and load_optimizer and scheduler is not None and checkpoint.get("scheduler_state_dict") is not None:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    return checkpoint, optimizer_restored


def train_one(cfg: dict):
    seed_everything(int(cfg.get("seed", 599)))
    output_dir = Path(cfg.get("output_dir", "results")) / cfg["exp_name"]
    ensure_dir(output_dir)

    device = "cuda" if torch.cuda.is_available() and not cfg.get("cpu", False) else "cpu"
    train_batch_size = int(cfg.get("batch_size", 256))
    eval_batch_size = int(cfg.get("eval_batch_size", min(train_batch_size, 512)))
    fallback_sizes = [int(size) for size in cfg.get("oom_microbatch_fallbacks", [])]
    preferred_microbatch_size = int(cfg.get("train_microbatch_size", train_batch_size))
    microbatch_candidates = list(dict.fromkeys([preferred_microbatch_size] + fallback_sizes))
    if (
        train_batch_size <= 0 or eval_batch_size <= 0 or preferred_microbatch_size <= 0
        or any(size <= 0 for size in fallback_sizes)
    ):
        raise ValueError("batch_size, eval_batch_size, train_microbatch_size and OOM fallback sizes must be positive")
    print(
        f"[batch] effective={train_batch_size}, eval={eval_batch_size}, "
        f"microbatch candidates={microbatch_candidates} (CUDA OOM fallback)"
    )
    loaders = make_loaders(
        cfg["data_csv"],
        seq_len=int(cfg.get("seq_len", 30)),
        feature_cols=cfg.get("feature_cols"),
        batch_size=train_batch_size,
        eval_batch_size=eval_batch_size,
        test_size=float(cfg.get("test_size", 0.2)),
        val_size=float(cfg.get("val_size", 0.1)),
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
    scaler_metadata = {
        "mean": loaders["scaler"].mean_.astype(float).tolist(),
        "scale": loaders["scaler"].scale_.astype(float).tolist(),
    }
    if hasattr(model, "set_input_scaler"):
        model.set_input_scaler(loaders["scaler"].mean_, loaders["scaler"].scale_)
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
        and (extend_training or not summary_path.exists())
    )
    total_params, trainable_params = count_parameters(model)
    trainable = [param for param in model.parameters() if param.requires_grad]
    if not trainable:
        raise ValueError("No trainable parameters.")

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
    used_microbatch_sizes: set[int] = set()

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
        # Extension is a continuation of the existing optimization trajectory.
        # Resetting the optimizer remains available as an explicit opt-in for
        # experiments that intentionally want a fresh LR/momentum state.
        load_optimizer = not (extend_training and bool(cfg.get("reset_optimizer_on_extend", False)))
        checkpoint, optimizer_restored = _load_training_checkpoint(
            latest_path, model, optimizer, scaler, scheduler, device, load_optimizer=load_optimizer
        )
        used_microbatch_sizes = {int(size) for size in checkpoint.get("train_microbatch_sizes", [])}
        history = checkpoint.get("history", [])
        start_epoch = int(checkpoint.get("epoch", 0)) + 1
        best = float(checkpoint.get("best", best))
        best_epoch = int(checkpoint.get("best_epoch", best_epoch))
        bad_epochs = int(checkpoint.get("bad_epochs", bad_epochs))
        stopped_epoch = int(checkpoint.get("stopped_epoch", stopped_epoch))
        stop_reason = str(checkpoint.get("stop_reason", stop_reason))
        previous_seconds = float(checkpoint.get("elapsed_seconds", 0.0))
        if extend_training and bool(cfg.get("reset_patience_on_extend", True)):
            bad_epochs = 0
            stopped_epoch = 0
            stop_reason = ""
        start = time.time()
        action = "extending" if extend_training else "continuing"
        optimizer_note = "restored optimizer" if optimizer_restored else "reset optimizer after parameter change"
        print(f"[resume] loaded {latest_path}; {action} at epoch {start_epoch}/{epochs} ({optimizer_note})")
    elif resume_best_only_candidate:
        # A completed run may have lost latest.pt (for example after copying
        # only the selected checkpoint).  When extending, restore the best
        # model and, for new checkpoints, its optimizer/scheduler state rather
        # than silently starting again at epoch 1.
        checkpoint, _ = _load_training_checkpoint(
            best_path,
            model,
            optimizer,
            scaler,
            scheduler,
            device,
            load_optimizer=not (extend_training and bool(cfg.get("reset_optimizer_on_extend", False))),
        )
        used_microbatch_sizes = {int(size) for size in checkpoint.get("train_microbatch_sizes", [])}
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
            best_epoch = int(checkpoint.get("best_epoch", history_df.loc[best_idx, "epoch"]))
            checkpoint_epoch = int(checkpoint.get("epoch", best_epoch))
            stopped_epoch = int(history_df.iloc[-1]["epoch"])
            stop_reason = "recovered_best_checkpoint"
            if extend_training:
                # The history may contain non-improving epochs after the
                # selected best checkpoint. Continue after the latest recorded
                # epoch so an interrupted copy-only run never duplicates rows.
                history_last_epoch = int(history_df.iloc[-1]["epoch"])
                start_epoch = max(checkpoint_epoch, history_last_epoch) + 1
                if bool(cfg.get("reset_patience_on_extend", True)):
                    bad_epochs = 0
                    stopped_epoch = 0
                    stop_reason = ""
                action = "extending"
            else:
                start_epoch = epochs + 1
                action = "evaluating"
            print(f"[resume] no latest.pt; {action} from best.pt at epoch {checkpoint_epoch}/{epochs}")
        else:
            print(f"[resume] {history_path} has no finite {early_metric}; restarting {cfg['exp_name']}")

    def save_latest(epoch: int):
        attention_runtime = _attention_runtime_metadata(model, cfg, device, use_amp)
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
                "scaler": scaler_metadata,
                "epoch": int(epoch),
                "history": history,
                "best": float(best),
                "best_epoch": int(best_epoch),
                "bad_epochs": int(bad_epochs),
                "stopped_epoch": int(stopped_epoch),
                "stop_reason": stop_reason,
                "scheduler": scheduler_info,
                "elapsed_seconds": float(previous_seconds + time.time() - start),
                "attention_runtime": attention_runtime,
                "train_microbatch_sizes": sorted(used_microbatch_sizes),
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
            loss_value, microbatch_size = _train_accumulated_batch(
                model, x, y, device, criterion, optimizer, scaler, use_amp, microbatch_candidates,
            )
            used_microbatch_sizes.add(int(microbatch_size))
            if not np.isfinite(loss_value):
                nonfinite_train_batches += 1
                epoch_stop_reason = f"nonfinite_train_loss_batch_{batch_idx}"
                print(f"[warn] {cfg['exp_name']} epoch {epoch}: non-finite train loss at batch {batch_idx}; stopping this experiment")
                break
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

        val_metrics, _, _ = eval_model(
            model, loaders["val"], device, amp=use_amp,
            unknown_index=loaders.get("unknown_index"), classes=loaders.get("classes"),
        )
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
        improved = _metric_improved(metric_value, best, early_mode, min_delta)
        if improved:
            best = metric_value
            best_epoch = epoch
            bad_epochs = 0
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
        if improved:
            attention_runtime = _attention_runtime_metadata(model, cfg, device, use_amp)
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    # Keep the selected checkpoint self-contained so an
                    # interrupted/copy-only run can be extended without
                    # reinitializing AdamW or the LR scheduler.
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scaler_state_dict": scaler.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
                    "config": cfg,
                    "input_dim": loaders["input_dim"],
                    "num_classes": loaders["num_classes"],
                    "classes": loaders["classes"],
                    "feature_cols": loaders["feature_cols"],
                    "scaler": scaler_metadata,
                    "epoch": int(epoch),
                    "history": history,
                    "best": float(best),
                    "best_epoch": int(best_epoch),
                    "bad_epochs": int(bad_epochs),
                    "stopped_epoch": int(stopped_epoch),
                    "stop_reason": stop_reason,
                    "scheduler": scheduler_info,
                    "elapsed_seconds": float(previous_seconds + time.time() - start),
                    "attention_runtime": attention_runtime,
                    "train_microbatch_sizes": sorted(used_microbatch_sizes),
                },
                best_path,
            )
        save_latest(epoch)
        if bad_epochs >= patience:
            break

    if not best_path.exists():
        raise RuntimeError(f"No valid checkpoint was saved for {cfg['exp_name']}. Check history.csv for non-finite losses.")
    load_model_state(model, _load_state_dict(best_path, device), context=str(best_path))
    reject_threshold = None
    if bool(cfg.get("calibrate_reject_threshold", True)):
        reject_threshold = calibrate_reject_threshold(
            model,
            loaders["val"],
            device,
            use_amp,
            loaders.get("unknown_index"),
            float(cfg.get("reject_threshold_quantile", 0.95)),
        )
    test_metrics, y_true, y_pred = eval_model(
        model, loaders["test"], device, amp=use_amp,
        unknown_index=loaders.get("unknown_index"), classes=loaders.get("classes"),
        reject_threshold=reject_threshold,
        source_groups=loaders.get("test_source_groups"),
    )
    report = classification_report(
        y_true,
        y_pred,
        labels=np.arange(len(loaders["classes"])),
        target_names=loaders["classes"],
        zero_division=0,
        output_dict=True,
    )
    model_cfg = cfg.get("model_cfg", {}) or {}
    base_layout = model_cfg.get("layout", [])
    block_repeats = int(model_cfg.get("block_repeats", 1))
    expanded_layout = base_layout * block_repeats if base_layout else []
    if getattr(model, "layout", None):
        expanded_layout = list(getattr(model, "layout"))
    attention_runtime = _attention_runtime_metadata(model, cfg, device, use_amp)
    result = {
        "exp_name": cfg["exp_name"],
        "model": cfg["model"],
        "seed": int(cfg.get("seed", 599)),
        "layout": "|".join(expanded_layout),
        "block_repeats": block_repeats,
        "hybrid_layers": len(expanded_layout),
        "device": device,
        "seq_len": int(cfg.get("seq_len", 30)),
        "total_params": total_params,
        "trainable_params": trainable_params,
        "trainable_ratio": trainable_params / max(total_params, 1),
        "effective_train_batch_size": int(loaders["train_batch_size"]),
        "train_batch_size": int(loaders["train_batch_size"]),
        "eval_batch_size": int(loaders["eval_batch_size"]),
        "train_microbatch_sizes": sorted(used_microbatch_sizes),
        "train_microbatch_size_min": min(used_microbatch_sizes) if used_microbatch_sizes else 0,
        "train_microbatch_size_max": max(used_microbatch_sizes) if used_microbatch_sizes else 0,
        "train_microbatch_fallback_used": any(
            size < int(loaders["train_batch_size"]) for size in used_microbatch_sizes
        ),
        "epochs_run": len(history),
        "best_epoch": best_epoch,
        "stopped_epoch": stopped_epoch,
        "stop_reason": stop_reason,
        "best_val_metric": float(best),
        "early_stop_metric": early_metric,
        "train_unknown": bool(cfg.get("train_unknown", True)),
        "reject_threshold": reject_threshold,
        "attention_backend_requested": attention_runtime["requested_backend"],
        "attention_backend_actual": "|".join(attention_runtime["actual_backends"]),
        "flash_attention_enforced": attention_runtime["flash_attention_enforced"],
        "amp_dtype": attention_runtime["amp_dtype"],
        "cuda_device": attention_runtime["cuda_device"],
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
            "scheduler": scheduler_info,
            "attention_runtime": attention_runtime,
            "reject_threshold": reject_threshold,
            "scaler": scaler_metadata,
        },
        output_dir / "metrics.json",
    )
    pd.DataFrame([compact_result(result)]).to_csv(output_dir / "summary.csv", index=False)
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
