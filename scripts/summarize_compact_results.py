"""汇总当前 60 类正式实验的核心指标。

``all_results.csv`` 保留完整运行的精简字段；每个运行目录中的
``metrics.json`` 仍是 raw argmax 和 threshold rejection 的审计来源。

默认模式允许在队列尚未完成时生成部分快照。使用 ``--require-complete``
时会额外检查 42 个正式运行、唯一的模型/数据集/seed 组合，以及每个运行
目录中的 ``summary.csv`` 和 ``metrics.json``，并展平来源分层指标。
"""

from __future__ import annotations

import argparse
import json
import re
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

SEEDS = {599, 5009, 813}
DATASETS = {"tls60": "CESNET-TLS22-S", "quic60": "CESNET-QUIC22-S"}
MODEL_PREFIXES = {
    "mvif_net_open": "MVIF-Net",
    "mvif_net_closed": "MVIF-Net",
    "tcnet": "30pktTCNET",
    "netmamba": "NetMamba",
    "srvit": "SRViT",
    "trafficaudio": "TrafficAudio",
    "bpfgnn": "BPF-GNN",
}

ACTIVE_RESULTS = Path("results/mvif_net_masked_global_pooling/all_results.csv")

def _metric_columns(frame: pd.DataFrame) -> dict[str, str]:
    selected: dict[str, str] = {}
    for view in ("raw", "threshold"):
        for label, current in METRICS.items():
            column = current.replace("test_threshold_", f"test_{view}_")
            if column in frame.columns:
                selected[f"{view}_{label}"] = column
    return selected


def _expected_experiments() -> set[str]:
    names = set()
    for prefix in MODEL_PREFIXES:
        for dataset in ("tls60", "quic60"):
            for seed in sorted(SEEDS):
                names.add(f"{prefix}_{dataset}_seed{seed}")
    return names


def _parse_run_name(exp_name: str) -> tuple[str, str, int]:
    match = re.fullmatch(r"(.+?)_(tls60|quic60)_seed(\d+)", exp_name)
    if not match:
        raise ValueError(f"无法解析正式运行名: {exp_name}")
    prefix, dataset, seed_text = match.groups()
    return prefix, dataset, int(seed_text)


def _run_dir(path: Path, exp_name: str) -> Path:
    """Locate a run when the active queue mixes MVIF and archived baseline roots."""

    candidates = [path.parent / exp_name, Path("results/formal60") / exp_name]
    for candidate in candidates:
        if (candidate / "metrics.json").exists() or (candidate / "summary.csv").exists():
            return candidate
    return candidates[0]


def _validate_complete(frame: pd.DataFrame, path: Path) -> None:
    expected = _expected_experiments()
    actual = set(frame["exp_name"].astype(str)) if "exp_name" in frame else set()
    if len(frame) != 42 or len(actual) != 42 or actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{path} 未达到 42 条唯一正式运行: rows={len(frame)}, unique={len(actual)}, "
            f"missing={missing}, extra={extra}"
        )

    keys = []
    for exp_name in sorted(actual):
        prefix, dataset, seed = _parse_run_name(exp_name)
        if prefix not in MODEL_PREFIXES or seed not in SEEDS:
            raise ValueError(f"运行矩阵非法: {exp_name}")
        keys.append((prefix, DATASETS[dataset], seed))
        run_dir = _run_dir(path, exp_name)
        for marker in ("summary.csv", "metrics.json"):
            if not (run_dir / marker).exists():
                raise FileNotFoundError(f"{exp_name} 缺少 {marker}")
        with (run_dir / "metrics.json").open(encoding="utf-8") as handle:
            payload = json.load(handle)
        result = payload.get("result", payload)
        if result.get("exp_name") != exp_name:
            raise ValueError(f"{exp_name}/metrics.json 的 exp_name 不一致")
        if int(result.get("seed", -1)) != seed:
            raise ValueError(f"{exp_name}/metrics.json 的 seed 不一致")
        if int(result.get("trainable_params", -1)) <= 0:
            raise ValueError(f"{exp_name}/metrics.json 缺少有效 trainable_params")
    if len(keys) != len(set(keys)):
        raise ValueError("模型/数据集/seed 组合存在重复")


def _source_group_rows(path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics_paths = list(path.parent.glob("*/metrics.json"))
    if path.parent != Path("results/formal60"):
        metrics_paths.extend(Path("results/formal60").glob("*/metrics.json"))
    for metrics_path in sorted(set(metrics_paths)):
        with metrics_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        result = payload.get("result", payload)
        exp_name = str(result.get("exp_name", metrics_path.parent.name))
        if "test_source_group_metrics" not in result:
            continue
        prefix, dataset, seed = _parse_run_name(exp_name)
        for source_group, group_metrics in result["test_source_group_metrics"].items():
            for view in ("raw", "threshold"):
                metrics = group_metrics.get(view)
                if not metrics:
                    continue
                row = {
                    "exp_name": exp_name,
                    "model": MODEL_PREFIXES.get(prefix, prefix),
                    "dataset": DATASETS.get(dataset, dataset),
                    "seed": seed,
                    "source_group": source_group,
                    "view": view,
                }
                row.update({key: metrics.get(key) for key in METRICS})
                rows.append(row)
            mixed = group_metrics.get("mixed_with_known")
            if mixed:
                for view in ("raw", "threshold"):
                    metrics = mixed.get(view)
                    if not metrics:
                        continue
                    row = {
                        "exp_name": exp_name,
                        "model": MODEL_PREFIXES.get(prefix, prefix),
                        "dataset": DATASETS.get(dataset, dataset),
                        "seed": seed,
                        "source_group": f"{source_group}+known",
                        "view": view,
                    }
                    row.update({key: metrics.get(key) for key in METRICS})
                    rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="要求正式队列 42 个运行全部完成，并输出来源分层快照",
    )
    args = parser.parse_args()
    path = ACTIVE_RESULTS
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}，请先运行 scripts/run_wsl_experiments.sh main")
    frame = pd.read_csv(path)
    if args.require_complete:
        _validate_complete(frame, path)

    names = {
        "mvif-net": "MVIF-Net",
        "mvif_net": "MVIF-Net",
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
    frame["dataset"] = exp.str.extract(r"((?:tls|quic)60)", expand=False).fillna("")
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
        order = ["dataset", "variant", "threshold_open_set_macro_f1_mean"]
        sort_columns = [column for column in order if column in summary]
        ascending = [column != "threshold_open_set_macro_f1_mean" for column in sort_columns]
        summary = summary.sort_values(sort_columns, ascending=ascending)
    output = path.with_name("comparison_summary.csv")
    summary.to_csv(output, index=False)
    print(f"已写入 {output}")
    print(summary.to_string(index=False))

    if args.require_complete:
        source = _source_group_rows(path)
        source_output = path.with_name("comparison_source_groups.csv")
        source.to_csv(source_output, index=False)
        print(f"已写入 {source_output}，共 {len(source)} 条来源分层记录")


if __name__ == "__main__":
    main()
