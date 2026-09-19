#!/usr/bin/env python
"""Report the EXACT parameter count of every candidate alignment baseline.

WHY THIS EXISTS
---------------
The submission claims HSTA "reduces parameters by 41.5%" relative to a pure
Transformer. That number comes from comparing:

    HSTA                 2 Mamba + 3 FFN blocks   (0.602M / 0.605M)
    TrafficTransformer   depth = 5                (1.030M / 1.033M)

The baselines were all configured with depth=5 while HSTA only carries TWO
state-space blocks, so the gap is largely a depth-configuration artefact
rather than an architectural-efficiency result. A reviewer can neutralise the
claim by asking for a parameter-matched comparison.

This script does NOT train anything and does NOT guess. It builds each
candidate model through the project's own `build_model` factory and prints its
real parameter count, so the matched-depth choices can be made from measured
numbers.

USAGE
-----
    cd E:\\AllProject\\流量分析python项目\\HSTA
    & 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' scripts\\alignment_models.py

    # report only the candidate table, skip writing YAML:
    ... scripts\\alignment_models.py --no-write

WHAT IT WRITES
--------------
    configs/alignment_baselines_v13.yaml   (only if --write, the default)
        A ready-to-run config containing the parameter-matched Transformer and
        Mamba baselines at the depth closest to the HSTA budget.

NOTE
----
Parameter counts are printed for both a 40-class and a 60-class head, because
the classification head differs between the QUIC/TLS-40 and -60 tasks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import build_model  # noqa: E402

SEQ_LEN = 30
INPUT_DIM = 3

# HSTA reference configurations, exactly as used in configs/hsta_flash.yaml
HSTA_CFG = {
    "dim": 128,
    "heads": 4,
    "mlp_ratio": 4,
    "dropout": 0.15,
    "d_state": 16,
    "d_conv": 4,
    "expand": 2,
    "pooling": "mean",
    "max_len": 256,
    "layout": ["mamba", "mamba", "mlp", "attention", "mlp"],
    "attention_backend": "flash",
}

# Everything that changes the block stack, i.e. what we want to sweep.
CANDIDATES = (
    [("transformer", {"dim": 128, "heads": 4, "mlp_ratio": 4, "dropout": 0.15}, d)
     for d in (1, 2, 3, 4, 5)]
    + [("netmamba_adapted", {"dim": 128, "dropout": 0.15, "d_state": 16, "d_conv": 4,
                             "expand": 2, "pooling": "mean", "max_len": 256}, d)
       for d in (1, 2, 3, 4, 5)]
    + [("gru", {"hidden": 128, "dropout": 0.15, "pooling": "last"}, d)
       for d in (1, 2, 3, 4, 5)]
    + [("30pkttcnet_adapted", {"channels": 128, "kernel_size": 3, "dropout": 0.15,
                               "classifier_hidden": 128}, d)
       for d in (1, 2, 3, 4, 5)]
)

# ---------------------------------------------------------------------------
# Parameter accounting for the Mamba:Attention ratio arms
# (configs/ratio_scale_v13.yaml).
#
# This does NOT search for a width that equalises parameters. It reports the
# measured parameter count of every ratio arm at the fixed study width, because
# the design intent is a FIXED-WIDTH sweep:
#
#   A ratio arm that carries MORE parameters than the 2:1 arm cannot claim a
#   capacity advantage, and an arm carrying fewer is strictly cheaper. Printing
#   the counts per arm lets the manuscript show that the 2:1 arm is at most as
#   large as its 1:1 rival, so a 2:1 win cannot be dismissed as a capacity
#   artefact -- and that argument needs no extra training runs.
#
# Use `scripts/ratio_calculator.py` for the fast analytic version; this is the
# measured cross-check that builds the real models.
# ---------------------------------------------------------------------------
RATIO_ARMS: list[tuple[str, list[str]]] = [
    ("1:1  (M1A1)", ["mamba", "mlp", "attention", "mlp"]),
    ("2:1  (M2A1)", ["mamba", "mamba", "mlp", "attention", "mlp"]),
    ("3:1  (M3A1)", ["mamba", "mamba", "mamba", "mlp", "attention", "mlp"]),
    ("4:1  (M4A1)", ["mamba", "mamba", "mamba", "mamba", "mlp", "attention", "mlp"]),
    ("1:0  (no attention)", ["mamba", "mlp"]),
    ("1:2  (M1A2)", ["mamba", "mlp", "attention", "mlp", "attention", "mlp"]),
    ("2:2  (M2A2)", ["mamba", "mamba", "mlp", "attention", "mlp", "attention",
                     "mlp"]),
]
STUDY_DIM = 128


def ratio_arms_probe(target: int, num_classes: int) -> None:
    """Measured parameter count of every ratio arm at the study width."""
    print("=" * 78)
    print(f"Ratio arms at dim={STUDY_DIM} ({num_classes} classes; "
          f"HSTA budget {target:,})")
    print("=" * 78)
    print(f"  {'arm':<22}{'params':>12}{'vs HSTA':>11}   layout")
    print("  " + "-" * 74)

    for label, layout in RATIO_ARMS:
        cfg = {
            "dim": STUDY_DIM, "heads": 4, "mlp_ratio": 4, "dropout": 0.15,
            "d_state": 16, "d_conv": 4, "expand": 2, "pooling": "mean",
            "max_len": 256, "layout": layout, "attention_backend": "flash",
        }
        n = try_count("hsta", cfg, num_classes)
        if n is None:
            print(f"  {label:<22}{'[could not build]':>12}")
            continue
        delta = (n - target) / target * 100.0
        print(f"  {label:<22}{n:>12,}{delta:>10.1f}%   {'|'.join(layout)}")
    print("  " + "-" * 74)
    print("  Interpretation: if the 2:1 arm matches or beats 1:1 while carrying")
    print("  no more parameters, capacity cannot explain the win. Only the")
    print("  2:1-vs-1:1 and 2:1-vs-3:1 pairs are needed for the ratio argument.")
    print()


def count_params(name: str, cfg: dict, num_classes: int) -> int:
    model = build_model(name, INPUT_DIM, num_classes, SEQ_LEN, cfg)
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def try_count(name: str, cfg: dict, num_classes: int):
    """Count parameters, or return None if the model cannot be built here.

    Mamba-based candidates need `mamba-ssm` with CUDA, so this probe should be
    run in the project's WSL environment. Failing softly keeps the other rows
    reportable instead of aborting the whole table.
    """
    try:
        return count_params(name, cfg, num_classes)
    except Exception as exc:  # noqa: BLE001 - deliberately broad for a probe
        print(f"  [skip] {name}: {type(exc).__name__}: {exc}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    # Single flag: writing is the default, --no-write suppresses it. (Using a
    # store_true/store_false pair would make the last default win.)
    parser.add_argument("--no-write", dest="write", action="store_false", default=True,
                        help="report only; do not write configs/alignment_baselines_v13.yaml.")
    args = parser.parse_args()

    print("=" * 78)
    print("HSTA reference parameter counts (measured, not estimated)")
    print("=" * 78)
    hsta_40 = try_count("hsta", HSTA_CFG, 40)
    hsta_60 = try_count("hsta", HSTA_CFG, 60)
    if hsta_40 is None:
        print("  [error] HSTA could not be built; run this probe inside WSL with "
              "mamba-ssm installed.")
        return 3
    print(f"  HSTA  (40 classes) : {hsta_40:,}")
    print(f"  HSTA  (60 classes) : {hsta_60:,}")
    print("  layout             : " + " -> ".join(HSTA_CFG["layout"]))
    print()

    print("=" * 78)
    print("Candidate baselines by depth")
    print("=" * 78)
    print(f"{'model':<22}{'depth':>6}{'40cls':>14}{'60cls':>14}")
    print("-" * 78)

    rows = []
    for name, cfg, depth in CANDIDATES:
        merged = dict(cfg)
        merged["depth"] = depth
        n40 = try_count(name, merged, 40)
        n60 = try_count(name, merged, 60)
        if n40 is None or n60 is None:
            print(f"{name:<22}{depth:>6}{'n/a':>14}{'n/a':>14}")
            continue
        rows.append((name, depth, n40, n60))
        print(f"{name:<22}{depth:>6}{n40:>14,}{n60:>14,}")
    print("-" * 78)
    print()

    if not rows:
        print("No candidates could be built.")
        return 4

    # Closest parameter match per family (used to build the YAML).
    family_depths: dict[str, list[int]] = {}
    for name, depth, n40, _n60 in rows:
        family_depths.setdefault(name, []).append(depth)

    matched: dict[str, int] = {}
    for name, depths in family_depths.items():
        best = min(depths, key=lambda d: abs(
            next(n for m, dd, n, _ in rows if m == name and dd == d) - hsta_40))
        matched[name] = best

    print("=" * 78)
    print("Closest parameter match to HSTA (40-class budget)")
    print("=" * 78)
    for name, depth in matched.items():
        n40 = next(n for m, d, n, _ in rows if m == name and d == depth)
        delta = (n40 - hsta_40) / hsta_40 * 100.0
        print(f"  {name:<22} depth={depth}  {n40:>12,}  ({delta:+.1f}% vs HSTA)")
    print()

    # Parameter accounting for the ratio arms of configs/ratio_scale_v13.yaml.
    ratio_arms_probe(hsta_40, 40)

    if not args.write:
        return 0

    out_path = PROJECT_ROOT / "configs" / "alignment_baselines_v13.yaml"
    written = _write_config(out_path, hsta_40, hsta_60, rows, matched)
    print(f"Wrote {written}")
    print()
    print("Next:")
    print("  1. Inspect the parameter deltas above.")
    print("  2. bash scripts/run_evidence_pack.sh stage_alignment")
    print("  3. python scripts/aggregate_evidence.py    # regenerates tables + tests")
    return 0


def _write_config(path: Path, hsta_40: int, hsta_60: int, rows, matched) -> Path:
    """Emit a runnable config for the parameter-matched baselines."""
    tasks = [
        ("quic40_s", "data/processed/datazoo_quic40_s_seq30.csv", 40),
        ("quic60_s", "data/processed/datazoo_quic60_s_seq30.csv", 60),
        ("tls40_s", "data/processed/datazoo_tls40_s_seq30.csv", 40),
        ("tls60_s", "data/processed/datazoo_tls60_s_seq30.csv", 60),
    ]
    seeds = (42, 2025, 3407)

    lines: list[str] = []
    lines.append("# =============================================================================")
    lines.append("# Parameter-matched baselines, generated by scripts/alignment_models.py")
    lines.append("# =============================================================================")
    lines.append("#")
    lines.append("# Generated from MEASURED parameter counts, not estimates.")
    lines.append(f"#   HSTA reference: {hsta_40:,} params (40 cls) / {hsta_60:,} params (60 cls)")
    lines.append("#")
    lines.append("# Purpose: neutralise the objection that the submission's '41.5% fewer")
    lines.append("# parameters' claim is an artefact of the baselines being configured at")
    lines.append("# depth=5 while HSTA carries only two state-space blocks.")
    lines.append("#")
    lines.append("# These deltas are the honest headline for the efficiency argument:")
    lines.append("# report the depth, the parameter count, and the Macro-F1 together.")
    lines.append("# ----------------------------------------------------------------------------")
    for name, depth in matched.items():
        n40 = next(n for m, d, n, _ in rows if m == name and d == depth)
        n60 = next(n for m, d, _n40, n in rows if m == name and d == depth)
        lines.append(f"#   {name:<20} depth={depth}  {n40:>10,} (40cls)  {n60:>10,} (60cls)")
    lines.append("# =============================================================================")
    lines.append("")
    lines.append("base:")
    lines.append("  output_dir: results/alignment_baselines_v13")
    lines.append("  seed: 42")
    lines.append("  epochs: 100")
    lines.append("  patience: 20")
    lines.append("  batch_size: 512")
    lines.append("  lr: 0.0005")
    lines.append("  weight_decay: 0.0001")
    lines.append("  lr_scheduler: reduce_on_plateau")
    lines.append("  lr_scheduler_metric: val_macro_f1")
    lines.append("  lr_factor: 0.5")
    lines.append("  lr_patience: 3")
    lines.append("  min_lr: 0.000001")
    lines.append("  early_stop_metric: val_macro_f1")
    lines.append("  early_stop_min_delta: 0.0005")
    lines.append("  seq_len: 30")
    lines.append("  amp: true")
    lines.append("  num_workers: 0")
    lines.append("  model_cfg:")
    lines.append("    dim: 128")
    lines.append("    hidden: 128")
    lines.append("    heads: 4")
    lines.append("    mlp_ratio: 4")
    lines.append("    dropout: 0.15")
    lines.append("    d_state: 16")
    lines.append("    d_conv: 4")
    lines.append("    expand: 2")
    lines.append("    pooling: mean")
    lines.append("    max_len: 256")
    lines.append("")
    lines.append("experiments:")

    for model_name, depth in matched.items():
        for task, csv_path, _ncls in tasks:
            for seed in seeds:
                lines.append(f"  - exp_name: alignv13_{model_name}_d{depth}_{task}_seed{seed}")
                lines.append(f"    model: {model_name}")
                lines.append(f"    data_csv: {csv_path}")
                lines.append(f"    seed: {seed}")
                lines.append("    model_cfg:")
                lines.append(f"      depth: {depth}")
                if model_name == "gru":
                    lines.append('      pooling: "last"')
                lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
