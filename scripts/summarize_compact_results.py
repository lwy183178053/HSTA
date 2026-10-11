"""汇总当前 40 类 small 实验的核心指标。

``all_results.csv`` 保留完整运行的精简字段；每个运行目录中的
``metrics.json`` 仍是 raw argmax 和 threshold rejection 的审计来源。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


METRICS = {
    "known_accuracy": "test_threshold_known_accuracy",
    "known_macro_f1": "test_threshold_known_macro_f1",
    "unknown_precision": "test_threshold_unknown_precision",
    "unknown_recall": "test_threshold_unknown_recall",
    "unknown_f1": "test_threshold_unknown_f1",
    "unknown_auroc": "test_threshold_unknown_auroc",
    "unknown_aupr": "test_threshold_unknown_aupr",
    "known_false_unknown": "test_threshold_known_false_unknown_rate",
    "unknown_false_known": "test_threshold_unknown_false_known_rate",
    "open_set_accuracy": "test_threshold_open_set_accuracy",
    "open_set_macro_f1": "test_threshold_open_set_macro_f1",
}

LEGACY_FIELDS = {
    "known_accuracy": "test_known_accuracy",
    "known_macro_f1": "test_known_macro_f1",
    "unknown_precision": "test_unknown_precision",
    "unknown_recall": "test_unknown_recall",
    "unknown_f1": "test_unknown_f1",
    "unknown_auroc": "test_unknown_auroc",
    "unknown_aupr": "test_unknown_aupr",
    "known_false_unknown": "test_known_false_unknown_rate",
    "unknown_false_known": "test_unknown_false_known_rate",
    "open_set_accuracy": "test_open_set_accuracy",
    "open_set_macro_f1": "test_open_set_macro_f1",
}


def _metric_columns(frame: pd.DataFrame) -> dict[str, str]:
    selected: dict[str, str] = {}
    for label, current in METRICS.items():
        if current in frame.columns:
            selected[label] = current
        elif LEGACY_FIELDS[label] in frame.columns:
            selected[label] = LEGACY_FIELDS[label]
    return selected


def main() -> None:
    path = Path("results/compact_s/all_results.csv")
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}，请先运行 scripts/run_wsl_experiments.sh main")
    frame = pd.read_csv(path)

    names = {
        "hsta-cm": "HSTA-CM",
        "hsta_cm": "HSTA-CM",
        "30pkttcnet-adapted": "30pktTCNET",
        "30pkttcnet": "30pktTCNET",
        "netmamba-adapted": "NetMamba",
        "netmamba": "NetMamba",
        "srvit": "SRViT",
        "srvit-adapted": "SRViT",
        "trafficaudio": "TrafficAudio",
        "trafficaudio-adapted": "TrafficAudio",
        "bpf-gnn": "BPF-GNN",
        "bpf_gnn": "BPF-GNN",
    }
    model = frame.get("model", pd.Series("unknown", index=frame.index)).astype(str).str.lower()
    frame["model_name"] = model.map(names).fillna(frame.get("model", model))
    exp = frame.get("exp_name", pd.Series("", index=frame.index)).astype(str)
    frame["variant"] = "closed"
    frame.loc[exp.str.contains("open", case=False), "variant"] = "open"
    frame.loc[exp.str.contains("no_conv|no_mamba|no_attention", case=False, regex=True), "variant"] = "ablation"
    frame["dataset"] = exp.str.extract(r"((?:tls|quic)40_s)", expand=False).fillna("")
    frame["seed"] = pd.to_numeric(frame.get("seed"), errors="coerce")

    selected = _metric_columns(frame)
    columns = ["model_name", "variant", "dataset", "seed"] + list(selected.values())
    compact = frame[[column for column in columns if column in frame.columns]].copy()
    compact = compact.rename(columns={source: label for label, source in selected.items()})
    for label in selected:
        compact[label] = pd.to_numeric(compact[label], errors="coerce")

    rows: list[dict[str, object]] = []
    for (model_name, variant, dataset), group in compact.groupby(
        ["model_name", "variant", "dataset"], dropna=False
    ):
        row: dict[str, object] = {
            "model": model_name,
            "variant": variant,
            "dataset": dataset,
            "seeds": int(group["seed"].nunique()) if "seed" in group else 0,
        }
        for label in selected:
            values = group[label].dropna()
            row[f"{label}_mean"] = float(values.mean()) if not values.empty else float("nan")
            row[f"{label}_std"] = float(values.std(ddof=1)) if len(values) > 1 else float("nan")
        rows.append(row)

    summary = pd.DataFrame(rows)
    if not summary.empty:
        order = ["dataset", "variant", "open_set_macro_f1_mean"]
        sort_columns = [column for column in order if column in summary]
        ascending = [column != "open_set_macro_f1_mean" for column in sort_columns]
        summary = summary.sort_values(sort_columns, ascending=ascending)
    output = path.with_name("compact_summary.csv")
    summary.to_csv(output, index=False)
    print(f"已写入 {output}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
