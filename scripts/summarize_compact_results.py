"""Write the small, paper-facing result table.

Each run keeps its complete ``metrics.json`` while ``summary.csv`` and this
derived table expose only scalar comparison fields.  This script deliberately
creates a compact view for the manuscript so the raw and threshold metric
namespaces do not appear as duplicate columns in the first result table.  The
threshold-rejection view is the primary open-set operating point; raw argmax
metrics remain available in ``metrics.json``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# These are the metrics a reader needs to compare the models.  The underlying
# result files contain the full protocol (both raw and threshold views).
PRIMARY_METRICS = {
    "known_accuracy": "test_threshold_known_accuracy",
    "known_macro_f1": "test_threshold_known_macro_f1",
    "unknown_f1": "test_threshold_unknown_f1",
    "unknown_auroc": "test_threshold_unknown_auroc",
    "unknown_aupr": "test_threshold_unknown_aupr",
    "open_set_macro_f1": "test_threshold_open_set_macro_f1",
}


def main() -> None:
    path = Path("results/compact_s/all_results.csv")
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run scripts/run_wsl_experiments.sh compact_s first")
    df = pd.read_csv(path)
    model_names = {
        "hsta-cm": "HSTA-CM-no-DFT",
        "hsta_cm": "HSTA-CM-no-DFT",
        "hsta-cm-dft": "HSTA-CM-DFT",
        "hsta_cm_dft": "HSTA-CM-DFT",
        "30pkttcnet-adapted": "30pktTCNET-adapted",
        "netmamba-adapted": "NetMamba-adapted",
        "srvit": "SRViT-adapted",
        "trafficaudio": "TrafficAudio-adapted",
        "bpf-gnn": "BPF-GNN-adapted",
        "bpf_gnn": "BPF-GNN-adapted",
    }
    df["variant"] = df["model"].map(model_names).fillna(df["model"])
    # Both the current names (tls22_s/quic22_s) and older probe names are
    # accepted, so the reporting script remains useful for archived runs.
    df["task"] = df["exp_name"].str.extract(r"((?:tls|quic)22_(?:s|small|medium|paper))", expand=False)
    df["task"] = df["task"].fillna(df["exp_name"].str.extract(r"((?:tls|quic))", expand=False))

    # A few early probe files predate the explicit threshold namespace.  Use
    # their legacy fields as a compatibility fallback without changing them.
    selected = {}
    for short_name, column in PRIMARY_METRICS.items():
        if column in df.columns:
            selected[short_name] = column
        else:
            legacy = {
                "known_accuracy": "test_known_accuracy",
                "known_macro_f1": "test_known_macro_f1",
                "unknown_f1": "test_unknown_f1",
                "unknown_auroc": "test_unknown_auroc",
                "unknown_aupr": "test_unknown_aupr",
                "open_set_macro_f1": "test_open_set_macro_f1",
            }[short_name]
            if legacy in df.columns:
                selected[short_name] = legacy

    keep = ["variant", "task", "seed"] + list(selected.values())
    compact = df.loc[df["variant"] != "unknown", keep].copy()
    compact = compact.rename(columns={column: short_name for short_name, column in selected.items()})
    for column in selected:
        compact[column] = pd.to_numeric(compact[column], errors="coerce")

    grouped = []
    for (variant, task), group in compact.groupby(["variant", "task"], dropna=False):
        row = {"model": variant, "dataset": task, "seeds": int(group["seed"].nunique())}
        for metric in selected:
            values = group[metric].dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            # A single-seed result has no empirical standard deviation.  Keep
            # it as NaN so it cannot be mistaken for a measured zero.
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else float("nan")
        grouped.append(row)
    summary = pd.DataFrame(grouped)
    sort_columns = ["dataset"]
    ascending = [True]
    if "open_set_macro_f1_mean" in summary.columns:
        sort_columns.append("open_set_macro_f1_mean")
        ascending.append(False)
    summary = summary.sort_values(sort_columns, ascending=ascending)
    summary.to_csv(path.with_name("compact_summary.csv"), index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
