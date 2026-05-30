from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch.utils.data import DataLoader

from data.dataset import TrafficSeqDataset, _scale_from_train, _split_by_column, _stratified_split, load_sequence_csv
from models import build_model
from train import _load_state_dict, eval_model, train_one
from utils import deep_merge, ensure_dir, save_json, seed_everything


def _is_zero_shot(cfg: dict) -> bool:
    return all(key in cfg for key in ("source_csv", "target_csv", "source_checkpoint"))


def _completed_result(cfg: dict, require_best: bool = True):
    output_dir = Path(cfg.get("output_dir", "results")) / cfg["exp_name"]
    summary_path = output_dir / "summary.csv"
    best_path = output_dir / "best.pt"
    if not summary_path.exists() or (require_best and not best_path.exists()):
        return None
    df = pd.read_csv(summary_path)
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def _sort_results(df: pd.DataFrame) -> pd.DataFrame:
    for metric in ("test_macro_f1", "covered_macro_f1", "full_accuracy"):
        if metric in df.columns:
            return df.sort_values(metric, ascending=False)
    return df


def _merge_and_write_results(results_path: Path, new_df: pd.DataFrame, configured_names: set[str] | None = None) -> pd.DataFrame:
    ensure_dir(results_path.parent)
    if results_path.exists():
        old_df = pd.read_csv(results_path)
        if "exp_name" in old_df.columns and "exp_name" in new_df.columns:
            old_df = old_df[~old_df["exp_name"].isin(new_df["exp_name"])]
        df = pd.concat([old_df, new_df], ignore_index=True, sort=False)
    else:
        df = new_df
    if configured_names is not None and "exp_name" in df.columns:
        df = df[df["exp_name"].isin(configured_names)]
    df = _sort_results(df)
    df.to_csv(results_path, index=False)
    return df


def _run_one(merged: dict):
    if _is_zero_shot(merged):
        return zero_shot_one(merged)
    return train_one(merged)


def _split_data(data, test_size: float, val_size: float, seed: int):
    split = _split_by_column(data)
    if split is None:
        split = _stratified_split(data.X, data.y, test_size=test_size, val_size=val_size, seed=seed)
    return split


def _source_scaler(csv_path: str | Path, seq_len: int, test_size: float, val_size: float, seed: int):
    data = load_sequence_csv(csv_path, seq_len=seq_len)
    X_train, _, _, _, _, _ = _split_data(data, test_size=test_size, val_size=val_size, seed=seed)
    _, scaler = _scale_from_train(X_train)
    return scaler


def _target_test_loader(
    csv_path: str | Path,
    scaler,
    seq_len: int,
    batch_size: int,
    test_size: float,
    val_size: float,
    seed: int,
    num_workers: int,
):
    data = load_sequence_csv(csv_path, seq_len=seq_len)
    _, _, _, _, X_test, y_test = _split_data(data, test_size=test_size, val_size=val_size, seed=seed)
    n, seq_len_actual, dim = X_test.shape
    X_test = scaler.transform(X_test.reshape(-1, dim)).astype("float32").reshape(n, seq_len_actual, dim)
    loader = DataLoader(
        TrafficSeqDataset(X_test, y_test),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    return loader, [str(c) for c in data.label_encoder.classes_], int(dim), int(seq_len_actual)


def zero_shot_one(cfg: dict):
    seed_everything(int(cfg.get("seed", 42)))
    start = time.time()
    device = "cuda" if torch.cuda.is_available() and not cfg.get("cpu", False) else "cpu"
    seq_len = int(cfg.get("seq_len", 30))
    batch_size = int(cfg.get("batch_size", 512))
    test_size = float(cfg.get("test_size", 0.2))
    val_size = float(cfg.get("val_size", 0.1))
    seed = int(cfg.get("seed", 42))
    num_workers = int(cfg.get("num_workers", 0))

    checkpoint_path = Path(cfg["source_checkpoint"])
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"source_checkpoint not found: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    source_classes = [str(c) for c in checkpoint.get("classes", [])]
    if not source_classes:
        raise ValueError(f"Checkpoint does not include classes: {checkpoint_path}")

    scaler = _source_scaler(cfg["source_csv"], seq_len=seq_len, test_size=test_size, val_size=val_size, seed=seed)
    target_loader, target_classes, input_dim, target_seq_len = _target_test_loader(
        cfg["target_csv"],
        scaler=scaler,
        seq_len=seq_len,
        batch_size=batch_size,
        test_size=test_size,
        val_size=val_size,
        seed=seed,
        num_workers=num_workers,
    )

    model = build_model(
        cfg["model"],
        input_dim=input_dim,
        num_classes=len(source_classes),
        seq_len=target_seq_len,
        cfg=cfg.get("model_cfg", {}),
    ).to(device)
    model.load_state_dict(_load_state_dict(checkpoint_path, device), strict=True)
    raw_metrics, y_true_idx, y_pred_source_idx = eval_model(model, target_loader, device)

    source_index = {label: idx for idx, label in enumerate(source_classes)}
    mapped_true = np.asarray([source_index.get(target_classes[int(i)], -1) for i in y_true_idx], dtype="int64")
    covered_mask = mapped_true >= 0
    full_correct = (mapped_true == y_pred_source_idx) & covered_mask
    full_accuracy = float(full_correct.mean()) if len(full_correct) else 0.0
    covered_accuracy = float(accuracy_score(mapped_true[covered_mask], y_pred_source_idx[covered_mask])) if covered_mask.any() else 0.0
    overlap_labels = sorted(set(source_classes) & set(target_classes))
    overlap_indices = [source_index[label] for label in overlap_labels]
    if covered_mask.any():
        precision, recall, f1, _ = precision_recall_fscore_support(
            mapped_true[covered_mask],
            y_pred_source_idx[covered_mask],
            labels=overlap_indices,
            average="macro",
            zero_division=0,
        )
    else:
        precision = recall = f1 = 0.0

    output_dir = Path(cfg.get("output_dir", "results")) / cfg["exp_name"]
    ensure_dir(output_dir)
    result = {
        "exp_name": cfg["exp_name"],
        "model": cfg["model"],
        "transfer_type": "zero_shot",
        "device": device,
        "seq_len": seq_len,
        "source_checkpoint": str(checkpoint_path),
        "source_csv": str(cfg["source_csv"]),
        "target_csv": str(cfg["target_csv"]),
        "source_num_classes": len(source_classes),
        "target_num_classes": len(target_classes),
        "overlap_classes": len(overlap_labels),
        "target_test_samples": int(len(y_true_idx)),
        "target_covered_samples": int(covered_mask.sum()),
        "target_coverage": float(covered_mask.mean()) if len(covered_mask) else 0.0,
        "full_accuracy": full_accuracy,
        "covered_accuracy": covered_accuracy,
        "covered_macro_precision": float(precision),
        "covered_macro_recall": float(recall),
        "covered_macro_f1": float(f1),
        "raw_index_accuracy": float(raw_metrics["accuracy"]),
        "seconds": float(time.time() - start),
    }
    save_json(
        {
            "result": result,
            "source_classes": source_classes,
            "target_classes": target_classes,
            "overlap_classes": overlap_labels,
            "config": cfg,
        },
        output_dir / "metrics.json",
    )
    pd.DataFrame([result]).to_csv(output_dir / "summary.csv", index=False)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/tls40_s.yaml")
    parser.add_argument("--resume", dest="resume", action="store_true", default=True, help="Skip finished experiments and resume latest.pt checkpoints.")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Disable experiment/checkpoint resume.")
    parser.add_argument("--force", action="store_true", help="Rerun experiments even when summary.csv already exists.")
    parser.add_argument("--extend", action="store_true", help="Continue finished experiments from latest.pt up to the configured epoch count.")
    parser.add_argument("--only", nargs="*", default=None, help="Only run the listed experiment names.")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    base = cfg["base"]
    rows = []
    row_output_dirs = []
    selected = set(args.only or [])
    configured_names = set()
    configured_names_by_output_dir = {}
    for exp in cfg["experiments"]:
        merged = deep_merge(copy.deepcopy(base), exp)
        merged["model_cfg"] = deep_merge(base.get("model_cfg", {}), exp.get("model_cfg", {}))
        configured_names.add(merged["exp_name"])
        exp_output_dir = str(Path(merged.get("output_dir", base.get("output_dir", "results"))))
        configured_names_by_output_dir.setdefault(exp_output_dir, set()).add(merged["exp_name"])
        if selected and merged["exp_name"] not in selected:
            continue
        merged["resume"] = bool(args.resume and not args.force)
        merged["extend_training"] = bool(args.extend)
        run_kind = "ZERO-SHOT" if _is_zero_shot(merged) else "RUN"
        print(f"\n===== {run_kind} {merged['exp_name']} =====")
        if merged["resume"] and not args.extend:
            completed = _completed_result(merged, require_best=not _is_zero_shot(merged))
            if completed is not None:
                print(f"[resume] skip completed: {merged['exp_name']}")
                rows.append(completed)
                row_output_dirs.append(exp_output_dir)
                continue
        rows.append(_run_one(merged))
        row_output_dirs.append(exp_output_dir)

    if not rows:
        print("No experiments selected.")
        return

    output_dir = Path(base.get("output_dir", "results"))
    new_df = pd.DataFrame(rows)
    results_path = output_dir / "all_results.csv"
    df = _merge_and_write_results(results_path, new_df, configured_names if not selected else None)

    rows_by_output_dir = {}
    for row, row_output_dir in zip(rows, row_output_dirs):
        row_output_path = Path(row_output_dir)
        if row_output_path == output_dir:
            continue
        rows_by_output_dir.setdefault(row_output_path, []).append(row)
    for row_output_path, group_rows in rows_by_output_dir.items():
        group_names = configured_names_by_output_dir.get(str(row_output_path)) if not selected else None
        _merge_and_write_results(row_output_path / "all_results.csv", pd.DataFrame(group_rows), group_names)

    print("\nSaved:", results_path)
    cols = [
        "exp_name",
        "model",
        "block_repeats",
        "hybrid_layers",
        "layout",
        "transfer_type",
        "seq_len",
        "test_accuracy",
        "test_macro_f1",
        "covered_accuracy",
        "covered_macro_f1",
        "trainable_params",
        "seconds",
    ]
    print(df[[col for col in cols if col in df.columns]])


if __name__ == "__main__":
    main()
