#!/usr/bin/env python
"""Analyse the Mamba:Attention ratio study.

Reads the run records produced by:

    configs/ratio_scale_v13.yaml    ->  results/ratio_scale_v13

and reports Macro-F1 as a function of the state-space : attention ratio.

The ratio is recovered from the actual layer layout stored in each run's
`metrics.json`, NOT parsed from the experiment name, so a mislabelled run name
cannot silently produce a wrong ratio.

WHAT IT DECIDES
    For each task it reports whether the 2:1 arm is the best arm, and by how
    much, so the manuscript can either claim a ratio design rule or state
    honestly that no ratio effect was detected.

USAGE
    cd E:\\AllProject\\流量分析python项目\\HSTA
    & 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' scripts\\ratio_analysis.py

OUTPUTS
    results/ratio_report/ratio_summary.md
    results/ratio_report/ratio_summary.csv
    results/ratio_report/ratio_tests.csv
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

STUDIES = {
    "ratio_scale_v13": "Study 1: fixed WIDTH (d=128); ratio varies but so does model size",
    "ratio_budget_v13": "Study 2: CONTROLLED PARAMETER BUDGET; the only study that can attribute a difference to the ratio",
    # The placement control is analysed separately (see placement_summary):
    # every placement variant sits at the same 2:1 ratio, so a ratio-style
    # comparison table does not apply to it.
}

# Where a study's runs physically live, when that differs from the study key.
# The placement extension reuses the original ablation directory so its
# existing 3-seed runs are not duplicated.
STUDY_DIRS = {
    "placement_v13": ("hsta_flash_ablation", "placement_v13", "hsta_flash"),
}

PLACEMENT_STUDY = "placement_v13"

SEEDS_OF_INTEREST = (42, 2025, 3407, 1337, 7, 2024)
ZERO_ATTENTION = "1:0"
ZERO_MAMBA = "0:1"


def parse_layout(layout) -> tuple[int, int] | None:
    """Return (n_mamba, n_attention) from a layout list or 'a|b|c' string."""
    if layout is None:
        return None
    if isinstance(layout, str):
        parts = [p.strip().lower() for p in layout.split("|") if p.strip()]
    elif isinstance(layout, (list, tuple)):
        parts = [str(p).strip().lower() for p in layout]
    else:
        return None
    m = sum(1 for p in parts if p in {"mamba", "ssm"})
    a = sum(1 for p in parts if p in {"attention", "attn"})
    return m, a


def ratio_label(m: int, a: int) -> str:
    """Human label for the state-space : attention balance."""
    if a == 0:
        return ZERO_ATTENTION          # e.g. "1:0", no attention at all
    if m == 0:
        return ZERO_MAMBA              # e.g. "0:1", attention only
    divisor = _gcd(m, a)
    return f"{m // divisor}:{a // divisor}"


def _gcd(x: int, y: int) -> int:
    while y:
        x, y = y, x % y
    return abs(x) or 1


def task_of(run: str) -> str | None:
    m = re.search(r"(quic40_s|quic60_s|tls40_s|tls60_s)", run)
    return m.group(1) if m else None


def load_study(results_root: Path, study: str) -> list[dict]:
    """Load every run belonging to `study`, summed over its source directories.

    A study may draw from more than one results directory: the placement
    extension reuses the original ablation folder so its existing runs are not
    re-trained.
    """
    rows: list[dict] = []
    specs = STUDY_DIRS.get(study, (study,))
    for directory in specs:
        rows.extend(_load_directory(results_root / directory, study))
    return rows


def _load_directory(study_dir: Path, study: str) -> list[dict]:
    rows: list[dict] = []
    if not study_dir.exists():
        return rows
    for metrics_path in sorted(study_dir.glob("*/metrics.json")):
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            print(f"  [warn] unreadable {metrics_path}")
            continue
        result = payload.get("result") or {}
        cfg = (payload.get("config") or {}).get("model_cfg") or {}
        layout = result.get("layout") or cfg.get("layout")
        counts = parse_layout(layout)
        if counts is None:
            continue
        m, a = counts
        run = str(result.get("exp_name") or metrics_path.parent.name)
        rows.append({
            "study": study,
            "run": run,
            "task": task_of(run),
            "seed": result.get("seed"),
            "mamba_blocks": m,
            "attention_blocks": a,
            "ratio": ratio_label(m, a),
            "dim": cfg.get("dim"),
            "params": result.get("total_params"),
            "macro_f1": result.get("test_macro_f1"),
            "accuracy": result.get("test_accuracy"),
            "layout": layout if isinstance(layout, str) else "|".join(map(str, layout or [])),
        })
    return rows


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = (
        df.groupby(["study", "task", "ratio", "mamba_blocks", "attention_blocks", "dim"])
        .agg(n=("macro_f1", "count"),
             f1_mean=("macro_f1", "mean"),
             f1_std=("macro_f1", "std"),
             params=("params", "median"))
        .reset_index()
    )
    out["f1_mean"] = out["f1_mean"] * 100.0
    out["f1_std"] = out["f1_std"] * 100.0
    return out.sort_values(["study", "task", "f1_mean"], ascending=[True, True, False])


def compare_to_two_to_one(summary: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Difference of every distinct ratio against the 2:1 arm, per study/task.

    Matching is done on the (normalised) ratio label rather than on raw block
    counts, so a 4:2 arm correctly counts as a 2:1 arm.
    """
    rows: list[dict] = []
    if summary.empty:
        return pd.DataFrame()
    for (study, task), group in summary.groupby(["study", "task"]):
        # Average any arms that share a ratio (e.g. a 4:2 and a 2:1 arm).
        by_ratio = (group.groupby("ratio")
                    .agg(f1_mean=("f1_mean", "mean"),
                         params=("params", "median"),
                         mamba=("mamba_blocks", "first"),
                         attn=("attention_blocks", "first"))
                    .reset_index())
        ref_rows = by_ratio[by_ratio["ratio"] == "2:1"]
        if ref_rows.empty:
            continue
        ref = ref_rows.iloc[0]
        ref_runs = df[(df["study"] == study) & (df["task"] == task) &
                      (df["ratio"] == "2:1")]

        for _, arm in by_ratio.iterrows():
            if arm["ratio"] == "2:1":
                continue
            arm_runs = df[(df["study"] == study) & (df["task"] == task) &
                          (df["ratio"] == arm["ratio"])]
            shared = sorted(set(arm_runs["seed"]) & set(ref_runs["seed"]))
            delta = float(ref["f1_mean"] - arm["f1_mean"])
            per_seed = []
            for s in shared:
                rv = ref_runs[ref_runs["seed"] == s]["macro_f1"]
                av = arm_runs[arm_runs["seed"] == s]["macro_f1"]
                if not rv.empty and not av.empty:
                    per_seed.append((float(rv.iloc[0]) - float(av.iloc[0])) * 100.0)
            rows.append({
                "study": study,
                "task": task,
                "arm": f"{int(arm['mamba'])}M:{int(arm['attn'])}A ({arm['ratio']})",
                "arm_ratio": arm["ratio"],
                "arm_params": arm["params"],
                "ref_params": ref["params"],
                "delta_vs_2to1_pp": delta,
                "n_shared_seeds": len(shared),
                "delta_min_pp": min(per_seed) if per_seed else None,
                "delta_max_pp": max(per_seed) if per_seed else None,
                "sign_consistent": (all(d > 0 for d in per_seed) or
                                    all(d < 0 for d in per_seed)) if per_seed else None,
            })
    return pd.DataFrame(rows).sort_values(["study", "task", "delta_vs_2to1_pp"],
                                          ascending=[True, True, False])


def verdict(summary: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    if summary.empty:
        return ["_No ratio runs found yet. Run the ratio studies first._"]

    for (study, task), group in summary.groupby(["study", "task"]):
        group = group.sort_values("f1_mean", ascending=False)
        top = group.iloc[0]
        two_one = group[group["ratio"] == "2:1"]
        label = f"{study} / {task}"
        if two_one.empty:
            lines.append(f"- **{label}**: no 2:1 arm present; best is "
                         f"{top['ratio']} at {top['f1_mean']:.2f}. Cannot compare.")
            continue
        two_one = two_one.iloc[0]
        gap = float(top["f1_mean"] - two_one["f1_mean"])
        if top["ratio"] == "2:1":
            lines.append(f"- **{label}**: 2:1 is the best arm "
                         f"({two_one['f1_mean']:.2f} +/- {_sd(two_one)}, "
                         f"next best {top['ratio']} is {gap:.2f} pp behind).")
        else:
            lines.append(f"- **{label}**: 2:1 is NOT the best arm. "
                         f"{top['ratio']} is ahead by {gap:.2f} pp "
                         f"({top['f1_mean']:.2f} vs {two_one['f1_mean']:.2f}).")
    return lines


def _sd(row) -> str:
    return "n/a" if pd.isna(row["f1_std"]) else f"{row['f1_std']:.2f}"


def placement_variant(parts: list[str]) -> str | None:
    """Name the placement variant from a parsed layout."""
    if "attention" not in parts:
        return "No Attention"
    idx = parts.index("attention")
    if idx == 0:
        return "Front Attention"
    if idx == len(parts) - 1:
        return "Late Attention"
    if idx + 1 < len(parts) and parts[idx + 1] == "mlp":
        return "HSTA (post-transformation)"
    return "Middle Attention"


def placement_summary(results_root: Path) -> pd.DataFrame:
    """Front / Middle / HSTA placement comparison at an equal parameter budget.

    This is the paper's cleanest control: the variants differ only in where the
    attention block sits, and HSTA vs Front / Middle are parameter-identical.
    Reported separately from the ratio table because every arm is 2:1.
    """
    rows: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for directory in STUDY_DIRS[PLACEMENT_STUDY]:
        study_dir = results_root / directory
        if not study_dir.exists():
            continue
        for metrics_path in sorted(study_dir.glob("*/metrics.json")):
            try:
                payload = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            result = payload.get("result") or {}
            cfg = (payload.get("config") or {}).get("model_cfg") or {}
            raw = result.get("layout") or cfg.get("layout")
            counts = parse_layout(raw)
            if counts is None or counts[1] != 1:
                continue          # placement study is single-attention only
            parts = ([p.strip().lower() for p in raw.split("|")] if isinstance(raw, str)
                     else [str(p).lower() for p in raw])
            run = str(result.get("exp_name") or metrics_path.parent.name)
            task = task_of(run)
            seed = result.get("seed")
            if task is None or "quic40" in task or "tls40" in task:
                continue          # 60-class study only
            key = (run, int(seed))
            if key in seen:       # a run may appear in two source directories
                continue
            seen.add(key)
            rows.append({
                "task": task,
                "variant": placement_variant(parts),
                "seed": seed,
                "params": result.get("total_params"),
                "macro_f1": result.get("test_macro_f1"),
                "layout": "|".join(parts),
                "run": run,
            })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    out = (df.groupby(["task", "variant", "params"])
           .agg(n=("macro_f1", "count"),
                f1_mean=("macro_f1", "mean"),
                f1_std=("macro_f1", "std"))
           .reset_index())
    out["f1_mean"] *= 100.0
    out["f1_std"] *= 100.0
    return out.sort_values(["task", "f1_mean"], ascending=[True, False])


def format_markdown(summary: pd.DataFrame, tests: pd.DataFrame,
                    placement: pd.DataFrame | None = None) -> str:
    out: list[str] = ["# Mamba:Attention ratio + attention placement analysis\n"]
    out.append("Ratios and variants are recovered from each run's stored layer "
               "layout.\n")

    if placement is not None and not placement.empty:
        out.append("## 0. Attention placement (equal-parameter control)\n")
        out.append("All arms are 2:1. HSTA and Front are parameter-identical, so "
                   "any gap here is caused by placement alone.\n")
        out.append("| Task | Variant | n | Macro-F1 | Params |")
        out.append("|---|---|---|---|---|")
        for _, r in placement.iterrows():
            params = "" if pd.isna(r["params"]) else format(int(r["params"]), ",")
            out.append(f"| {r['task']} | {r['variant']} | {int(r['n'])} | "
                       f"{r['f1_mean']:.2f} +/- {_sd(r)} | {params} |")
        out.append("")

    if summary.empty:
        out.append("_No ratio runs found. Expected under `results/ratio_scale_v13`._\n")
        return "\n".join(out)

    out.append("## 1. Arms by study and task\n")
    out.append("| Study | Task | Mamba | Attn | Ratio | dim | n | Macro-F1 | Params |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in summary.iterrows():
        params = "" if pd.isna(r["params"]) else format(int(r["params"]), ",")
        out.append(f"| {r['study']} | {r['task']} | {int(r['mamba_blocks'])} | "
                   f"{int(r['attention_blocks'])} | {r['ratio']} | "
                   f"{'' if pd.isna(r['dim']) else int(r['dim'])} | {int(r['n'])} | "
                   f"{r['f1_mean']:.2f} +/- {_sd(r)} | {params} |")
    out.append("")

    out.append("## 2. Difference against the 2:1 arm\n")
    if tests.empty:
        out.append("_No comparable arms._\n")
    else:
        out.append("Positive delta means the 2:1 arm scored higher.\n")
        out.append("| Study | Task | Arm | delta (pp) | per-seed range | sign consistent | n |")
        out.append("|---|---|---|---|---|---|---|")
        for _, r in tests.iterrows():
            rng = "-"
            if r["delta_min_pp"] is not None and r["delta_max_pp"] is not None:
                rng = f"{r['delta_min_pp']:+.2f} .. {r['delta_max_pp']:+.2f}"
            sign = "-" if r["sign_consistent"] is None else ("yes" if r["sign_consistent"] else "no")
            out.append(f"| {r['study']} | {r['task']} | {r['arm']} | "
                       f"{r['delta_vs_2to1_pp']:+.2f} | {rng} | {sign} | "
                       f"{r['n_shared_seeds']} |")
        out.append("")

    out.append("## 3. Verdict per study and task\n")
    out.extend(verdict(summary))
    out.append("")
    out.append("## 4. Reading these results honestly\n")
    out.append("- `sign consistent = yes` means the 2:1 arm led on EVERY shared "
               "seed. That is weaker than significance but stronger than a mean "
               "difference, and it is worth reporting at n=3.\n")
    out.append("- Parameters are NOT matched in Study 1 (`ratio_scale_v13`): they rise "
               "monotonically with the number of Mamba blocks. A monotone accuracy "
               "trend there is exactly what a CAPACITY effect looks like, so Study 1 "
               "CANNOT attribute a difference to the ratio. Only Study 2 "
               "(`ratio_budget_v13`) controls model size by arm, and only Study 2 may "
               "be used for a ratio claim.\n")
    out.append("- n=3 seeds cannot reach p<0.05 (exact Wilcoxon floor 0.25). The "
               "study now runs 6 seeds, where the two-sided floor is 2/2^6 = 0.031. "
               "Any comparison still backed by only 3 shared seeds is labelled a "
               "sign test.\n")
    out.append("- The calculator in scripts/ratio_calculator.py is calibrated against "
               "the stored HSTA runs. For the budget study, retain the measured "
               "parameter count in every arm and do not claim exact matching for "
               "the approximately 3% M2A2 near-match.\n")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="results/ratio_report")
    args = parser.parse_args()

    results_root = Path(args.results)
    if not results_root.exists():
        print(f"ERROR: results root not found: {results_root.resolve()}")
        return 2

    rows: list[dict] = []
    for study in STUDIES:
        found = load_study(results_root, study)
        print(f"{study:<22} {len(found):>3} runs")
        rows.extend(found)

    placement = placement_summary(results_root)
    if not placement.empty:
        print(f"{'placement':<22} {int(placement['n'].sum()):>3} runs")

    if not rows and placement.empty:
        print("\nNo ratio runs found.")
        print("Run:")
        print("  bash scripts/run_evidence_pack.sh parallel_ratio 3")
        return 1

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["study", "task", "ratio", "mamba_blocks", "attention_blocks",
                 "dim", "macro_f1", "accuracy", "params", "run", "seed", "layout"])
    summary = summarise(df)
    tests = compare_to_two_to_one(summary, df)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_dir / "ratio_summary.csv", index=False)
    tests.to_csv(out_dir / "ratio_tests.csv", index=False)
    if not placement.empty:
        placement.to_csv(out_dir / "placement_summary.csv", index=False)
    (out_dir / "ratio_summary.md").write_text(
        format_markdown(summary, tests, placement), encoding="utf-8")

    if not placement.empty:
        print()
        print("=" * 78)
        print("PLACEMENT (equal-parameter control)")
        print("=" * 78)
        show = placement.copy()
        show["Macro-F1"] = show.apply(lambda r: f"{r['f1_mean']:.2f} +/- {_sd(r)}", axis=1)
        print(show[["task", "variant", "n", "Macro-F1", "params"]].to_string(index=False))

    if summary.empty:
        print()
        print("No ratio arms yet -- run the ratio study to fill the ratio tables.")
        print(f"Wrote {out_dir / 'ratio_summary.md'}")
        return 0

    print()
    print("=" * 78)
    print("ARMS")
    print("=" * 78)
    show = summary.copy()
    show["Macro-F1"] = show.apply(lambda r: f"{r['f1_mean']:.2f} +/- {_sd(r)}", axis=1)
    print(show[["study", "task", "mamba_blocks", "attention_blocks", "ratio",
                "dim", "n", "Macro-F1", "params"]].to_string(index=False))
    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    for line in verdict(summary):
        print(line)
    print()
    print(f"Wrote {out_dir / 'ratio_summary.md'}")
    print(f"Wrote {out_dir / 'ratio_summary.csv'}")
    print(f"Wrote {out_dir / 'ratio_tests.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
