from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd
import yaml

from train import train_one
from utils import deep_merge, ensure_dir


def _completed_result(cfg: dict):
    output_dir = Path(cfg.get("output_dir", "results")) / cfg["exp_name"]
    summary_path = output_dir / "summary.csv"
    best_path = output_dir / "best.pt"
    if not summary_path.exists() or not best_path.exists():
        return None
    df = pd.read_csv(summary_path)
    return None if df.empty else df.iloc[0].to_dict()


def _merge_and_write_results(results_path: Path, new_df: pd.DataFrame, configured_names: set[str] | None = None):
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
    if "test_macro_f1" in df.columns:
        df = df.sort_values("test_macro_f1", ascending=False)
    df.to_csv(results_path, index=False)
    return df


def _merge_experiment(base: dict, exp: dict) -> dict:
    merged = deep_merge(copy.deepcopy(base), exp)
    merged["model_cfg"] = deep_merge(base.get("model_cfg", {}), exp.get("model_cfg", {}))
    return merged


def main():
    parser = argparse.ArgumentParser(description="Run the closed-set experiments used by Revision 10.")
    parser.add_argument("--config", default="configs/tls40_s.yaml")
    parser.add_argument("--resume", dest="resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--force", action="store_true", help="Rerun experiments even when results exist.")
    parser.add_argument("--extend", action="store_true", help="Continue finished experiments to the configured epoch count.")
    parser.add_argument("--only", nargs="*", default=None, help="Only run the listed experiment names.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Override base output_dir. Intended for parallel execution: each worker "
            "writes to its own directory so concurrent runs cannot race on "
            "all_results.csv. Per-run artefacts (metrics.json, summary.csv, best.pt) "
            "are written under this directory either way."
        ),
    )
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    base = cfg["base"]
    if args.output_dir:
        base["output_dir"] = args.output_dir
    configured = [_merge_experiment(base, exp) for exp in cfg["experiments"]]
    configured_names = {exp["exp_name"] for exp in configured}
    selected = set(args.only or [])
    unknown = selected - configured_names
    if unknown:
        raise ValueError(f"Unknown --only experiment name(s): {', '.join(sorted(unknown))}")

    rows = []
    for merged in configured:
        if selected and merged["exp_name"] not in selected:
            continue
        merged["resume"] = bool(args.resume and not args.force)
        merged["extend_training"] = bool(args.extend)
        print(f"\n===== RUN {merged['exp_name']} =====")
        completed = _completed_result(merged) if merged["resume"] and not args.extend else None
        if completed is not None:
            print(f"[resume] skip completed: {merged['exp_name']}")
            rows.append(completed)
        else:
            rows.append(train_one(merged))

    if not rows:
        print("No experiments selected.")
        return

    output_dir = Path(base.get("output_dir", "results"))
    results_path = output_dir / "all_results.csv"
    df = _merge_and_write_results(
        results_path,
        pd.DataFrame(rows),
        configured_names if not selected else None,
    )
    print("\nSaved:", results_path)
    columns = [
        "exp_name",
        "model",
        "seed",
        "layout",
        "seq_len",
        "test_accuracy",
        "test_macro_f1",
        "trainable_params",
        "seconds",
    ]
    print(df[[column for column in columns if column in df.columns]])


if __name__ == "__main__":
    main()
