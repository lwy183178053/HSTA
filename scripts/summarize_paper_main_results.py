from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd


MODEL_ORDER = (
    "GRU",
    "Transformer",
    "30pktTCNET",
    "NetMamba",
    "SRViT",
    "TrafficAudio",
    "BPF-GNN",
    "HSTA",
)
TASK_ORDER = ("quic40_s", "quic60_s", "tls40_s", "tls60_s")
SEEDS = (42, 2025, 3407)
METRICS = ("accuracy", "macro_precision", "macro_recall", "macro_f1")
DEFAULT_INPUTS = (
    "results/tls40_s/all_results.csv",
    "results/quic40_s/all_results.csv",
    "results/tls60_s/all_results.csv",
    "results/quic60_s/all_results.csv",
    "results/sota_adapted/all_results.csv",
    "results/recent_journal_baselines/all_results.csv",
    "results/hsta_flash/all_results.csv",
)
PREFIX_TO_MODEL = (
    ("gru_5layer_", "GRU"),
    ("transformer_5layer_", "Transformer"),
    ("30pkttcnet_adapted_", "30pktTCNET"),
    ("netmamba_adapted_", "NetMamba"),
    ("srvit_", "SRViT"),
    ("trafficaudio_", "TrafficAudio"),
    ("bpf_gnn_", "BPF-GNN"),
    ("hsta_flash_", "HSTA"),
)


def _identity(exp_name: str):
    if "_depth" in exp_name or "attention_front" in exp_name or "attention_middle" in exp_name:
        return None
    model = next((name for prefix, name in PREFIX_TO_MODEL if exp_name.startswith(prefix)), None)
    task = next(
        (
            task
            for task in TASK_ORDER
            if f"_{task}_" in exp_name or exp_name.endswith(f"_{task}")
        ),
        None,
    )
    if model is None or task is None:
        return None
    suffix = exp_name.rsplit("_seed", 1)
    if len(suffix) == 2 and suffix[1].isdigit():
        return model, task, int(suffix[1])
    if model == "GRU" and exp_name == f"gru_5layer_{task}":
        return model, task, 42
    return None


def summarize_results(paths: list[Path]) -> pd.DataFrame:
    selected = []
    for path in paths:
        if not Path(path).exists():
            continue
        for row in pd.read_csv(path).to_dict("records"):
            identity = _identity(str(row.get("exp_name", "")))
            if identity is None:
                continue
            model, task, seed = identity
            values = {metric: pd.to_numeric(row.get(f"test_{metric}"), errors="coerce") for metric in METRICS}
            if seed not in SEEDS or not all(math.isfinite(float(value)) for value in values.values()):
                continue
            selected.append({"model": model, "task": task, "seed": seed, **values})

    raw = pd.DataFrame(selected).drop_duplicates(["model", "task", "seed"], keep="last")
    expected = {(model, task, seed) for model in MODEL_ORDER for task in TASK_ORDER for seed in SEEDS}
    observed = set(raw[["model", "task", "seed"]].itertuples(index=False, name=None)) if not raw.empty else set()
    missing = sorted(expected - observed)
    if missing:
        raise ValueError(f"Main-result matrix is incomplete; missing {len(missing)} rows: {missing[:8]}")

    rows = []
    for model in MODEL_ORDER:
        for task in TASK_ORDER:
            group = raw[(raw["model"] == model) & (raw["task"] == task)].sort_values("seed")
            out = {"model": model, "task": task, "effective_seeds": len(group)}
            for metric in METRICS:
                percent = group[metric].astype(float) * 100.0
                out[f"{metric}_mean"] = float(percent.mean())
                out[f"{metric}_std"] = float(percent.std(ddof=1))
            rows.append(out)
    return pd.DataFrame(rows)


def _markdown(summary: pd.DataFrame) -> str:
    lines = [
        "# Paper Main Results",
        "",
        "All values are percentages reported as mean +/- standard deviation over seeds 42, 2025, and 3407.",
        "",
        "| Model | Task | Accuracy | Macro-Precision | Macro-Recall | Macro-F1 | Seeds |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        values = [f"{row[f'{metric}_mean']:.2f} +/- {row[f'{metric}_std']:.2f}" for metric in METRICS]
        lines.append(
            f"| {row['model']} | {row['task']} | {values[0]} | {values[1]} | {values[2]} | {values[3]} | {row['effective_seeds']} |"
        )
    lines.extend(
        [
            "",
            "SRViT, TrafficAudio, and BPF-GNN are unified-input reimplementations of their published core structures using the shared [B,30,3] packet side-channel input and training protocol.",
            "HSTA uses the strict PyTorch SDPA FlashAttention backend for the final model table.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Build the fixed eight-model paper result table.")
    parser.add_argument("--inputs", nargs="*", default=list(DEFAULT_INPUTS))
    parser.add_argument("--output-dir", default="results/recent_journal_baselines")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_results([Path(path) for path in args.inputs])
    csv_path = output_dir / "paper_main_results.csv"
    md_path = output_dir / "paper_main_results.md"
    summary.to_csv(csv_path, index=False)
    md_path.write_text(_markdown(summary), encoding="utf-8")
    print(f"Saved: {csv_path}")
    print(f"Saved: {md_path}")


if __name__ == "__main__":
    main()
