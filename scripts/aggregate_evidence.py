#!/usr/bin/env python
"""Regenerate every manuscript table from raw run records and test significance.

WHAT THIS DOES
--------------
Reads each run's `metrics.json` (the authoritative per-run record, not the
aggregated CSVs) and reports, for every model x task:

  * n seeds, mean, sample standard deviation
  * a Welch t-test and a paired test against each reference model

It then writes a consolidated report so the manuscript numbers can be traced
back to individual runs instead of being copied by hand.

WHY WILCOXON NEEDS >= 6 PAIRS
-----------------------------
The manuscript reports 3 seeds. The exact two-sided Wilcoxon signed-rank test
has a minimum attainable p-value of 2/2^3 = 0.25 at n=3, so it CANNOT reach
significance at n=3 no matter how large the gap is. The script therefore:
  * runs Welch's t-test (which has no such floor) as the primary test, and
  * runs the paired test only when n >= 6, reporting "n too small" otherwise.
Treat any p-value derived from 3 seeds as indicative only.

USAGE
-----
    cd E:\\AllProject\\流量分析python项目\\HSTA
    & 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' scripts\\aggregate_evidence.py

    # custom roots / output
    ... scripts\\aggregate_evidence.py --results results --out results/evidence_report

OUTPUTS
-------
    results/evidence_report/summary.md        human-readable tables + tests
    results/evidence_report/summary.csv       machine-readable per model x task
    results/evidence_report/pairwise.csv      every pairwise comparison
    results/evidence_report/coverage.csv      which runs exist / are missing

DEPENDENCIES
------------
pandas is required. numpy/scipy are used when present; the paired test falls
back to an exact sign test implemented with math.comb, so the script still runs
in a minimal environment.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd

TASKS = ("quic40_s", "quic60_s", "tls40_s", "tls60_s")
TASK_LABEL = {
    "quic40_s": "QUIC-40",
    "quic60_s": "QUIC-60",
    "tls40_s": "TLS-40",
    "tls60_s": "TLS-60",
}

# ---------------------------------------------------------------------------
# Variant manifest: maps a results directory + experiment-name prefix to the
# label used in the manuscript. Extend this when new evidence lands.
# ---------------------------------------------------------------------------
VARIANTS: list[dict] = [
    {"label": "HSTA", "dir": "hsta_flash", "prefix": "hsta_flash",
     "role": "proposed"},
    {"label": "Front Attention", "dir": "hsta_flash_ablation",
     "prefix": "hsta_flash_attention_front", "role": "ablation"},
    {"label": "Middle Attention", "dir": "hsta_flash_ablation",
     "prefix": "hsta_flash_attention_middle", "role": "ablation"},
    {"label": "No Attention (v13)", "dir": "hsta_no_attention_v13",
     "prefix": "ablation_v13_no_attention", "role": "ablation"},
    {"label": "No Attention (legacy)", "dir": "hsta_no_attention",
     "prefix": "ablation_no_attention", "role": "ablation"},
]

# Parameter-matched baselines: label is derived from the run name so newly
# generated depths are picked up automatically.
ALIGNMENT_DIR = "alignment_baselines_v13"
ALIGNMENT_PREFIX = "alignv13_"

MAIN_RESULTS = {
    "GRU": ("quic40_s", "gru_5layer"),
    "Transformer": ("quic40_s", "transformer_5layer"),
    "30pktTCNET": ("sota_adapted", "30pkttcnet_adapted"),
    "NetMamba": ("sota_adapted", "netmamba_adapted"),
    "SRViT": ("recent_journal_baselines", "srvit"),
    "TrafficAudio": ("recent_journal_baselines", "trafficaudio"),
    "BPF-GNN": ("recent_journal_baselines", "bpf_gnn"),
}

# The GRU / Transformer baseline runs live in per-task directories named after
# the task itself (results/quic60_s, results/tls40_s, ...). MAIN_RESULTS above
# only pairs them with the quic40_s directory, which left GRU and Transformer
# absent from the QUIC-60 / TLS tables. These directories close that gap.
MAIN_RESULT_DIRS = ("quic40_s", "quic60_s", "tls40_s", "tls60_s")

# Ratio studies. scripts/ratio_analysis.py reports these in detail; mapping them
# here too stops `report` from listing the directories as unmapped.
RATIO_STUDIES = {
    "ratio_scale_v13": "ratio_scale_v13",
    "ratio_budget_v13": "ratio_budget_v13",
}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def task_of(run_name: str) -> str | None:
    m = re.search(r"(quic40_s|quic60_s|tls40_s|tls60_s)", run_name)
    return m.group(1) if m else None


def seed_of(run_name: str) -> int | None:
    m = re.search(r"seed(\d+)", run_name)
    return int(m.group(1)) if m else None


def load_runs(results_root: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for metrics_path in sorted(results_root.glob("*/*/metrics.json")):
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  [warn] unreadable {metrics_path}: {exc}")
            continue
        result = payload.get("result")
        if not isinstance(result, dict):
            print(f"  [warn] no 'result' block in {metrics_path}")
            continue
        run = str(result.get("exp_name") or metrics_path.parent.name)
        rows.append({
            "run": run,
            "dir": metrics_path.parent.parent.name,
            "seed": result.get("seed", seed_of(run)),
            "task": task_of(run),
            "accuracy": result.get("test_accuracy"),
            "macro_f1": result.get("test_macro_f1"),
            "macro_precision": result.get("test_macro_precision"),
            "macro_recall": result.get("test_macro_recall"),
            "params": result.get("total_params"),
            "epochs_run": result.get("epochs_run"),
            "best_epoch": result.get("best_epoch"),
            "stop_reason": result.get("stop_reason"),
            "attention_backend_actual": result.get("attention_backend_actual"),
            "layout": result.get("layout"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["task"])
    return df


def variant_label(row: pd.Series) -> str | None:
    for spec in VARIANTS:
        if row["dir"] == spec["dir"] and row["run"].startswith(spec["prefix"]):
            return spec["label"]
    if row["dir"] == ALIGNMENT_DIR and row["run"].startswith(ALIGNMENT_PREFIX):
        core = row["run"][len(ALIGNMENT_PREFIX):]
        core = re.sub(r"_(quic40_s|quic60_s|tls40_s|tls60_s)_seed\d+$", "", core)
        return f"aligned:{core}"
    # Baselines stored in per-task directories (results/quic60_s, ...).
    if row["dir"] in MAIN_RESULT_DIRS:
        for label, (_directory, prefix) in MAIN_RESULTS.items():
            if row["run"].startswith(prefix):
                return label
        return None
    # Ratio studies are analysed in detail by scripts/ratio_analysis.py; label
    # them here so coverage shows them rather than calling them unmapped.
    if row["dir"] in RATIO_STUDIES:
        return f"ratio:{row['dir']}"
    for label, (directory, prefix) in MAIN_RESULTS.items():
        if row["dir"] == directory and row["run"].startswith(prefix):
            return label
    return None


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def welch_t(a: list[float], b: list[float]):
    """Welch's t-test from first principles. Returns (t, df, p) or None."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se2 = va / na + vb / nb
    if se2 <= 0:
        return None
    t = (ma - mb) / math.sqrt(se2)
    df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    try:
        from scipy import stats  # type: ignore
        p = 2 * stats.t.sf(abs(t), df)
    except Exception:
        p = _normal_sf(abs(t)) * 2
    return t, df, p


def _normal_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def paired_test(a: list[float], b: list[float]):
    """Paired comparison on matched seeds.

    Returns (method, statistic, p, n_pairs). Falls back to an exact sign test
    when scipy is unavailable or n is too small for Wilcoxon.
    """
    if len(a) != len(b) or len(a) < 2:
        return None
    diffs = [x - y for x, y in zip(a, b)]
    nz = [d for d in diffs if d != 0]
    n_nonzero = len(nz)
    n_pairs = len(diffs)
    if n_nonzero == 0:
        return ("all-zero differences", 0.0, 1.0, 0)
    pos = sum(1 for d in nz if d > 0)

    if n_pairs >= 6:
        try:
            from scipy import stats  # type: ignore
            stat, p = stats.wilcoxon(nz, alternative="two-sided")
            return ("wilcoxon", float(stat), float(p), n_pairs)
        except Exception:
            pass

    # Exact two-sided sign test: p = 2 * P(X <= min(pos, n-pos))
    k = min(pos, n_nonzero - pos)
    tail = sum(math.comb(n_nonzero, i) for i in range(0, k + 1)) / (2 ** n_nonzero)
    return ("sign-test(exact)", float(k), min(1.0, 2 * tail), n_pairs)


def noise_floor(n: int) -> str:
    """Minimum attainable two-sided Wilcoxon p at this n."""
    if n < 5:
        return f"n={n}: Wilcoxon floor 2/2^{n} = {2 / 2 ** n:.3f} (cannot reach p<0.05)"
    return f"n={n}"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def summarise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["variant"] = df.apply(variant_label, axis=1)
    df = df[df["variant"].notna()]
    if df.empty:
        return df
    grouped = (
        df.groupby(["variant", "task"])
        .agg(n=("macro_f1", "count"),
             f1_mean=("macro_f1", "mean"),
             f1_std=("macro_f1", "std"),
             acc_mean=("accuracy", "mean"),
             acc_std=("accuracy", "std"),
             params=("params", "median"))
        .reset_index()
    )
    for col in ("f1_mean", "f1_std", "acc_mean", "acc_std"):
        grouped[col] = grouped[col] * 100.0
    return grouped.sort_values(["task", "f1_mean"], ascending=[True, False])


def pairwise(summary_df: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    reference = "HSTA"
    out: list[dict] = []
    for task in TASKS:
        ref = df[(df["variant"] == reference) & (df["task"] == task)]
        if ref.empty:
            continue
        ref_by_seed = dict(zip(ref["seed"], ref["macro_f1"]))
        for other in sorted(df[df["task"] == task]["variant"].unique()):
            if other == reference:
                continue
            # Ratio-study arms are not baselines. A ratio arm is a DIFFERENT
            # architecture from HSTA, so "HSTA vs ratio:scale_v13" would compare
            # HSTA against a mixture of other models. Those comparisons belong
            # to scripts/ratio_analysis.py, which compares ratio arms against
            # each other within one study.
            if str(other).startswith("ratio:"):
                continue
            cur = df[(df["variant"] == other) & (df["task"] == task)]
            if cur.empty:
                continue
            mean_ref = sum(ref_by_seed.values()) / len(ref_by_seed)
            mean_cur = cur["macro_f1"].mean()
            shared = sorted(set(cur["seed"]) & set(ref_by_seed))
            a = [ref_by_seed[s] for s in shared]
            b = [float(cur[cur["seed"] == s]["macro_f1"].iloc[0]) for s in shared]
            wt = welch_t(list(ref_by_seed.values()), list(cur["macro_f1"]))
            pt = paired_test(a, b)
            out.append({
                "task": TASK_LABEL.get(task, task),
                "reference": reference,
                "comparison": other,
                "n_ref": len(ref_by_seed),
                "n_cmp": int(cur.shape[0]),
                "n_shared_seeds": len(shared),
                "delta_pp": (mean_ref - mean_cur) * 100.0,
                "welch_p": None if wt is None else wt[2],
                "paired_method": None if pt is None else pt[0],
                "paired_stat": None if pt is None else pt[1],
                "paired_p": None if pt is None else pt[2],
                "paired_n": None if pt is None else pt[3],
            })
    return pd.DataFrame(out)


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spec in VARIANTS:
        for task in TASKS:
            subset = df[(df["dir"] == spec["dir"]) &
                        (df["run"].str.startswith(spec["prefix"])) &
                        (df["task"] == task)]
            seeds = sorted(int(s) for s in subset["seed"].dropna().unique())
            rows.append({
                "variant": spec["label"],
                "task": TASK_LABEL[task],
                "runs_found": int(subset.shape[0]),
                "seeds": ",".join(str(s) for s in seeds) or "-",
                "status": "OK" if subset.shape[0] >= 3 else "MISSING/INCOMPLETE",
            })
    return pd.DataFrame(rows)


def format_markdown(summary_df, pair_df, cov_df, df) -> str:
    lines: list[str] = []
    lines.append("# Evidence report (regenerated from raw run records)\n")
    lines.append(f"Runs discovered: **{len(df)}** across "
                 f"**{df['dir'].nunique() if not df.empty else 0}** result directories.\n")

    lines.append("## 1. Coverage -- which runs actually exist\n")
    if cov_df.empty:
        lines.append("_No ablation variants found._\n")
    else:
        lines.append("| Variant | Task | Runs | Seeds | Status |")
        lines.append("|---|---|---|---|---|")
        for _, r in cov_df.iterrows():
            lines.append(f"| {r['variant']} | {r['task']} | {r['runs_found']} | "
                         f"{r['seeds']} | {r['status']} |")
        lines.append("")

    lines.append("## 2. Macro-F1 by variant and task (%)\n")
    if summary_df.empty:
        lines.append("_Nothing to summarise._\n")
    else:
        lines.append("| Variant | Task | n | Macro-F1 (mean +/- sd) | Accuracy (mean +/- sd) | Params |")
        lines.append("|---|---|---|---|---|---|")
        for _, r in summary_df.iterrows():
            std = 0.0 if pd.isna(r["f1_std"]) else r["f1_std"]
            astd = 0.0 if pd.isna(r["acc_std"]) else r["acc_std"]
            lines.append(
                f"| {r['variant']} | {TASK_LABEL.get(r['task'], r['task'])} | {int(r['n'])} | "
                f"{r['f1_mean']:.2f} +/- {std:.2f} | "
                f"{r['acc_mean']:.2f} +/- {astd:.2f} | "
                f"{'' if pd.isna(r['params']) else format(int(r['params']), ',')} |")
        lines.append("")

    lines.append("## 3. Pairwise comparisons against HSTA\n")
    if pair_df.empty:
        lines.append("_No comparisons available._\n")
    else:
        lines.append("`delta_pp` is the Macro-F1 gap in percentage points "
                     "(positive = HSTA ahead).\n")
        lines.append("| Task | Comparison | n (ref/cmp/shared) | delta (pp) | Welch p | Paired | Paired p |")
        lines.append("|---|---|---|---|---|---|---|")
        for _, r in pair_df.iterrows():
            welch = "-" if pd.isna(r["welch_p"]) else f"{r['welch_p']:.4f}"
            paired_p = "-" if pd.isna(r["paired_p"]) else f"{r['paired_p']:.4f}"
            method = r["paired_method"] or "-"
            lines.append(
                f"| {r['task']} | {r['comparison']} | "
                f"{r['n_ref']}/{r['n_cmp']}/{r['n_shared_seeds']} | "
                f"{r['delta_pp']:+.2f} | {welch} | {method} | {paired_p} |")
        lines.append("")

    lines.append("## 4. Statistical power warning\n")
    seeds = sorted(int(s) for s in df["seed"].dropna().unique()) if not df.empty else []
    lines.append(f"Distinct seeds present in the records: {seeds or 'none'}\n")
    for n in sorted({len(df[df['variant'] == v]['seed'].dropna().unique())
                     for v in df['variant'].dropna().unique()} if not df.empty else set()):
        if n:
            lines.append(f"- {noise_floor(n)}")
    lines.append("")
    lines.append("**Do not claim significance from 3 seeds.** At n=3 the exact "
                 "Wilcoxon signed-rank test cannot produce p<0.25, so a "
                 "non-significant result is uninformative rather than evidence "
                 "of no effect. Raise the seed count before making ordering claims.\n")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default="results", help="results root directory")
    parser.add_argument("--out", default="results/evidence_report", help="output directory")
    args = parser.parse_args()

    results_root = Path(args.results)
    out_dir = Path(args.out)
    if not results_root.exists():
        print(f"ERROR: results root not found: {results_root.resolve()}")
        return 2

    print(f"Scanning {results_root.resolve()} ...")
    df = load_runs(results_root)
    print(f"Discovered {len(df)} runs with a readable result block.")
    if df.empty:
        print("Nothing to report.")
        return 1

    df["variant"] = df.apply(variant_label, axis=1)
    known = df[df["variant"].notna()].copy()
    unknown_dirs = sorted(set(df[df["variant"].isna()]["dir"]) - {""})
    if unknown_dirs:
        print("[note] directories present but not mapped to a variant: "
              + ", ".join(unknown_dirs))

    summary_df = summarise(known)
    pair_df = pairwise(summary_df, known)
    cov_df = coverage(df)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    pair_df.to_csv(out_dir / "pairwise.csv", index=False)
    cov_df.to_csv(out_dir / "coverage.csv", index=False)
    known.to_csv(out_dir / "runs.csv", index=False)
    (out_dir / "summary.md").write_text(
        format_markdown(summary_df, pair_df, cov_df, known), encoding="utf-8")

    print()
    print("=" * 78)
    print("COVERAGE")
    print("=" * 78)
    print(cov_df.to_string(index=False))
    print()
    print("=" * 78)
    print("MACRO-F1 SUMMARY (%)")
    print("=" * 78)
    if not summary_df.empty:
        show = summary_df.copy()
        show["Macro-F1"] = show.apply(
            lambda r: f"{r['f1_mean']:.2f} +/- {0.0 if pd.isna(r['f1_std']) else r['f1_std']:.2f}",
            axis=1)
        print(show[["variant", "task", "n", "Macro-F1"]].to_string(index=False))
    print()
    print("=" * 78)
    print("PAIRWISE vs HSTA")
    print("=" * 78)
    if not pair_df.empty:
        show = pair_df[["task", "comparison", "n_ref", "n_cmp", "n_shared_seeds",
                        "delta_pp", "welch_p", "paired_method", "paired_p"]]
        print(show.to_string(index=False))
    print()
    print(f"Wrote {out_dir / 'summary.md'}")
    print(f"Wrote {out_dir / 'summary.csv'}")
    print(f"Wrote {out_dir / 'pairwise.csv'}")
    print(f"Wrote {out_dir / 'coverage.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
