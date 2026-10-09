"""Summarize the compact S comparison by model and protocol/task."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    path = Path("results/compact_s/all_results.csv")
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run scripts/run_wsl_experiments.sh compact_s first")
    df = pd.read_csv(path)
    model_names = {
        "hsta-cm": "HSTA-CM",
        "hsta_cm": "HSTA-CM",
        "hsta-cm-dft": "HSTA-CM-DFT",
        "hsta_cm_dft": "HSTA-CM-DFT",
        "30pkttcnet-adapted": "30pktTCNET-adapted",
        "netmamba-adapted": "NetMamba-adapted",
        "srvit": "SRViT-adapted",
        "trafficaudio": "TrafficAudio-adapted",
        "bpf-gnn": "BPF-GNN-adapted",
        "bpf_gnn": "BPF-GNN-adapted",
    }
    df["variant"] = df["model"].map(model_names).fillna("unknown")
    df["task"] = df["exp_name"].str.extract(r"((?:tls|quic)22_s)", expand=False)
    summary = (
        df[df["variant"] != "unknown"]
        .groupby(["variant", "task"], as_index=False)
        .agg(
            seeds=("seed", "nunique"),
            accuracy_mean=("test_accuracy", "mean"),
            accuracy_std=("test_accuracy", "std"),
            macro_f1_mean=("test_macro_f1", "mean"),
            macro_f1_std=("test_macro_f1", "std"),
        )
    )
    summary.to_csv(path.with_name("compact_summary.csv"), index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
