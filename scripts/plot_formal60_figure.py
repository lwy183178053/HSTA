"""Plot the latest known-class and overall open-set results from Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
from rebuild_mvif_paper import MODEL_ORDER, _load_latest_metrics


DATASET_NAMES = {"tls60": "TLS", "quic60": "QUIC"}
COLORS = {"TLS": "#0072B2", "QUIC": "#D78300"}
MARKERS = {"TLS": "o", "QUIC": "s"}


def _parse_summary(value: str) -> tuple[float, float]:
    match = re.fullmatch(r"\s*([\d.]+)\s*±\s*([\d.]+)\s*", value)
    if match is None:
        raise ValueError(f"Invalid mean ± sample SD value: {value}")
    return float(match.group(1)), float(match.group(2))


def _load(path: Path) -> dict:
    return _load_latest_metrics(path)


def plot(metrics: dict, output: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    panels = [
        ("known", "macro_f1", "Known-Class Macro-F1 (%)", "(a) Known-Class Recognition"),
        ("open", "macro_f1", "Overall Open-Set Macro-F1 (%)", "(b) Open-Set Recognition"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.55), dpi=300, sharey=True)
    x = np.arange(len(MODEL_ORDER), dtype=float)
    offset = 0.11
    for ax, (section, metric, ylabel, title) in zip(axes, panels):
        for shift, dataset_key in ((-offset, "tls60"), (offset, "quic60")):
            dataset_label = DATASET_NAMES[dataset_key]
            means, stds = [], []
            for model in MODEL_ORDER:
                mean, std = _parse_summary(metrics[section][dataset_key][model][metric])
                means.append(mean)
                stds.append(std)
            ax.errorbar(
                x + shift,
                means,
                yerr=stds,
                fmt=MARKERS[dataset_label],
                color=COLORS[dataset_label],
                markerfacecolor="white",
                markeredgewidth=1.1,
                markersize=5.0,
                capsize=2.4,
                elinewidth=1.0,
                linewidth=0,
                label=dataset_label,
                zorder=3,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(MODEL_ORDER, rotation=22, ha="right")
        ax.set_ylim(0, 100)
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold")
        ax.grid(axis="y", color="#D9DDE2", linewidth=0.55, linestyle="--", alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="both", labelsize=8)
    axes[1].set_ylabel("")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 0.98), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.92), w_pad=1.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(output.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"已写入 {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latest-metrics", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../paper/源稿归档/figure3_formal60.png"),
    )
    args = parser.parse_args()
    plot(_load(args.latest_metrics), args.output)


if __name__ == "__main__":
    main()
