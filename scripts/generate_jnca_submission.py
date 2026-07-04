from __future__ import annotations

import math
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "paper" / "submission_jnca"
FIG_DIR = OUT_DIR / "figures"
ENGLISH_OVERLEAF_ZIP = ROOT / "paper" / "jnca_english_overleaf_package.zip"
UPLOAD_BUNDLE = OUT_DIR / "JNCA_recommended_upload_bundle.zip"
OVERLEAF_DIRECT_ZIP = OUT_DIR / "UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip"
EDITORIAL_SOURCE_ZIP = OUT_DIR / "JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip"
FIGURE_UPLOAD_ZIP = OUT_DIR / "FIGURES_FOR_UPLOAD.zip"
GRAPHICAL_ABSTRACT = OUT_DIR / "Graphical_Abstract.png"
GRAPHICAL_ABSTRACT_TIF = OUT_DIR / "Graphical_Abstract.tif"
FIGURE_CAPTIONS_DOCX = OUT_DIR / "Figure_Captions.docx"
OVERLEAF_IMPORT_GUIDE = OUT_DIR / "OVERLEAF_IMPORT_GUIDE.md"
GFA_COMPLIANCE_CHECK = OUT_DIR / "JNCA_GFA_COMPLIANCE_CHECK.md"
PLACEHOLDER_REPLACEMENT_CHECK = OUT_DIR / "FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md"
IMPORT_FORMAT_CHECK = OUT_DIR / "SUBMISSION_IMPORT_FORMAT_CHECK.md"
LATEX_TROUBLESHOOTING = OUT_DIR / "LATEX_IMPORT_TROUBLESHOOTING.md"
SOURCE_DOC_CANDIDATES = [
    ROOT / "paper" / "加密QUIC_TLS流量分类_修改版1.docx",
    ROOT / "paper" / "加密QUIC_TLS流量分类_最终优化版.docx",
    ROOT / "paper" / "加密QUIC_TLS流量分类_初稿.docx",
]
DRAWIO = ROOT / "paper" / "论文全部图_精修可编辑.drawio"
MANUSCRIPT_TITLE = "Hybrid State-Space Transition-Attention Modeling for Lightweight Encrypted QUIC/TLS Traffic Classification"
MANUSCRIPT_KEYWORDS = "Encrypted traffic classification; QUIC; TLS; Mamba; state-space model; cross-protocol transfer"
CORE_PROPERTY_AUTHOR = "Author metadata placeholder"


EN_STATEMENTS = [
    (
        "Author contributions (CRediT)",
        "Author One: Conceptualization, Methodology, Software, Investigation, Writing - original draft. "
        "Author Two: Data curation, Validation, Formal analysis, Visualization. "
        "Author Three: Supervision, Writing - review and editing, Project administration. [placeholder; confirm final roles before submission]",
    ),
    ("Funding", "Funding information is to be completed. [placeholder or state no funding]"),
    (
        "Declaration of competing interest",
        "The authors declare that they have no known competing financial interests or personal relationships that could have influenced the work reported in this paper. [to be confirmed by all authors]",
    ),
    (
        "Data and code availability",
        "The experiments are based on CESNET-QUIC22, CESNET-TLS22, and DataZoo. Code and processing scripts are available in the project repository; the final link should be handled according to the journal's anonymous review or repository policy.",
    ),
    ("Acknowledgements", "To be completed. [placeholder]"),
]

CN_STATEMENTS = [
    (
        "作者贡献（CRediT）",
        "Author One：Conceptualization、Methodology、Software、Investigation、Writing - original draft；"
        "Author Two：Data curation、Validation、Formal analysis、Visualization；"
        "Author Three：Supervision、Writing - review and editing、Project administration。[占位，请投稿前确认最终角色]",
    ),
    ("资金支持", "本研究资金支持信息待补充。[占位，请替换或写明无资金支持]"),
    ("利益冲突", "作者声明不存在已知竞争性经济利益或个人关系会影响本文工作。[占位，请作者确认]"),
    ("数据和代码可用性", "实验基于公开 CESNET-QUIC22、CESNET-TLS22 和 DataZoo；代码与处理脚本位于本项目仓库，提交前请按匿名审稿或公开仓库要求处理链接。"),
    ("致谢", "待补充。[占位]"),
]


TASKS = {
    "quic40_s": ("QUIC-40", ROOT / "results" / "quic40_s" / "all_results.csv"),
    "quic60_s": ("QUIC-60", ROOT / "results" / "quic60_s" / "all_results.csv"),
    "tls40_s": ("TLS-40", ROOT / "results" / "tls40_s" / "all_results.csv"),
    "tls60_s": ("TLS-60", ROOT / "results" / "tls60_s" / "all_results.csv"),
}


def resolve_source_doc() -> Path:
    for path in SOURCE_DOC_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("No source manuscript docx found under paper/.")


SOURCE_DOC = resolve_source_doc()


def fmt_pct(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{float(value) * 100:.2f}"


def fmt_num(value: float | int | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{float(value):.{digits}f}"


def mean_std_pct(values: pd.Series) -> str:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    if len(vals) == 0:
        return "-"
    if len(vals) == 1:
        return fmt_pct(vals.iloc[0])
    return f"{vals.mean() * 100:.2f}±{vals.std(ddof=1) * 100:.2f}"


def mean_std_plain(values: pd.Series, digits: int = 3) -> str:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    if len(vals) == 0:
        return "-"
    if len(vals) == 1:
        return fmt_num(vals.iloc[0], digits)
    return f"{vals.mean():.{digits}f}±{vals.std(ddof=1):.{digits}f}"


def task_frame(task_key: str) -> pd.DataFrame:
    return pd.read_csv(TASKS[task_key][1])


def source_tables() -> dict[int, list[list[str]]]:
    doc = Document(str(SOURCE_DOC))
    tables: dict[int, list[list[str]]] = {}
    for idx, table in enumerate(doc.tables, start=1):
        rows: list[list[str]] = []
        for row in table.rows:
            rows.append([cell.text.strip() for cell in row.cells])
        tables[idx] = rows
    return tables


def model_rows(task_key: str, models: list[str]) -> dict[str, tuple[str, str]]:
    df = task_frame(task_key)
    out: dict[str, tuple[str, str]] = {}
    for model in models:
        if model == "Hybrid":
            sub = df[
                (df["model"].astype(str).str.lower() == "hybrid")
                & df["exp_name"].str.contains("hybrid_mm_mlp_a_mlp_")
                & ~df["exp_name"].str.contains("2block|4block")
            ]
        elif model == "Transformer":
            sub = df[df["model"].astype(str).str.lower() == "transformer"]
        else:
            sub = df[df["model"].astype(str).str.lower() == model.lower()]
        out[model] = (
            mean_std_pct(sub["test_accuracy"]),
            mean_std_pct(sub["test_macro_f1"]),
        )
    return out


def sota_rows(task_key: str) -> dict[str, tuple[str, str]]:
    df = pd.read_csv(ROOT / "results" / "sota_adapted" / "all_results.csv")
    task = task_key.replace("_s", "")
    out: dict[str, tuple[str, str]] = {}
    for name in ["30pktTCNET-adapted", "NetMamba-adapted"]:
        sub = df[(df["model"] == name) & df["exp_name"].str.contains(task)]
        out[name] = (mean_std_pct(sub["test_accuracy"]), mean_std_pct(sub["test_macro_f1"]))
    return out


def build_main_result_tables() -> tuple[list[list[str]], list[list[str]]]:
    rows40 = [["Model", "QUIC-40 Acc", "QUIC-40 Macro-F1", "TLS-40 Acc", "TLS-40 Macro-F1"]]
    rows60 = [["Model", "QUIC-60 Acc", "QUIC-60 Macro-F1", "TLS-60 Acc", "TLS-60 Macro-F1"]]
    for model in ["MLP", "CNN", "LSTM", "GRU", "Transformer"]:
        q = model_rows("quic40_s", [model])[model]
        t = model_rows("tls40_s", [model])[model]
        rows40.append([model, q[0], q[1], t[0], t[1]])
    for model in ["30pktTCNET-adapted", "NetMamba-adapted"]:
        q = sota_rows("quic40_s")[model]
        t = sota_rows("tls40_s")[model]
        rows40.append([model, q[0], q[1], t[0], t[1]])
    q = model_rows("quic40_s", ["Hybrid"])["Hybrid"]
    t = model_rows("tls40_s", ["Hybrid"])["Hybrid"]
    rows40.append(["HSTA-Hybrid (Proposed)", q[0], q[1], t[0], t[1]])

    for model in ["GRU", "Transformer"]:
        q = model_rows("quic60_s", [model])[model]
        t = model_rows("tls60_s", [model])[model]
        rows60.append([model, q[0], q[1], t[0], t[1]])
    for model in ["30pktTCNET-adapted", "NetMamba-adapted"]:
        q = sota_rows("quic60_s")[model]
        t = sota_rows("tls60_s")[model]
        rows60.append([model, q[0], q[1], t[0], t[1]])
    q = model_rows("quic60_s", ["Hybrid"])["Hybrid"]
    t = model_rows("tls60_s", ["Hybrid"])["Hybrid"]
    rows60.append(["HSTA-Hybrid (Proposed)", q[0], q[1], t[0], t[1]])
    return rows40, rows60


def build_scaling_table() -> list[list[str]]:
    q40 = model_rows("quic40_s", ["Hybrid"])["Hybrid"][1]
    q60 = model_rows("quic60_s", ["Hybrid"])["Hybrid"][1]
    t40 = model_rows("tls40_s", ["Hybrid"])["Hybrid"][1]
    t60 = model_rows("tls60_s", ["Hybrid"])["Hybrid"][1]

    def first(s: str) -> float:
        return float(s.split("±")[0])

    return [
        ["Protocol", "40 classes", "60 classes", "Change (percentage points)"],
        ["QUIC", q40, q60, f"{first(q60) - first(q40):.2f}"],
        ["TLS", t40, t60, f"{first(t60) - first(t40):.2f}"],
    ]


def build_ablation_table() -> list[list[str]]:
    df = pd.read_csv(ROOT / "results" / "ablation_s" / "all_results.csv")
    rows = [["Variant", "QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]]
    mapping = [
        ("No Attention", "ablation_no_attention"),
        ("Attention-front", "ablation_attention_front"),
        ("Attention-middle", "ablation_attention_middle"),
    ]
    task_fragments = {
        "QUIC-40": "quic40",
        "QUIC-60": "quic60",
        "TLS-40": "tls40",
        "TLS-60": "tls60",
    }
    for label, prefix in mapping:
        row = [label]
        for task in task_fragments.values():
            sub = df[df["exp_name"].str.contains(prefix) & df["exp_name"].str.contains(task)]
            row.append(mean_std_pct(sub["test_macro_f1"]))
        rows.append(row)
    proposed = ["HSTA-Hybrid (Proposed)"]
    for key in ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]:
        proposed.append(model_rows(key, ["Hybrid"])["Hybrid"][1])
    rows.append(proposed)
    return rows


def build_efficiency_table() -> list[list[str]]:
    df = pd.read_csv(ROOT / "results" / "efficiency_benchmark" / "summary.csv")
    rows = [["Model", "Batch", "Params (M)", "GFLOPs/sample", "Latency (ms)", "Throughput (samples/s)", "Peak memory (MB)"]]
    model_order = ["30pktTCNET-adapted", "NetMamba-adapted", "Transformer", "HSTA-Hybrid"]
    name_map = {"transformer": "Transformer", "hybrid": "HSTA-Hybrid"}
    for raw_model in ["30pktTCNET-adapted", "NetMamba-adapted", "transformer", "hybrid"]:
        sub = df[(df["variant"] == "main") & (df["batch_size"].isin([1, 32, 512]))]
        if raw_model == "hybrid":
            sub = sub[(sub["model"] == "hybrid") & (sub["exp_name"].str.contains("hybrid_mm_mlp_a_mlp_"))]
        else:
            sub = sub[sub["model"] == raw_model]
        display = name_map.get(raw_model, raw_model)
        for batch in [1, 32, 512]:
            b = sub[sub["batch_size"] == batch]
            if b.empty:
                continue
            rows.append(
                [
                    display,
                    str(batch),
                    fmt_num(b["parameters_m"].mean(), 3),
                    fmt_num(b["gflops_per_sample"].mean(), 4),
                    fmt_num(b["latency_ms_mean"].mean(), 3),
                    f"{b['throughput_samples_per_s'].mean():.0f}",
                    fmt_num(b["gpu_memory_peak_allocated_mb"].mean(), 1),
                ]
            )
    # Preserve the conceptual order even if pandas grouping order differs.
    order = {name: i for i, name in enumerate(model_order)}
    body = sorted(rows[1:], key=lambda r: (order.get(r[0], 99), int(r[1])))
    return [rows[0]] + body


def build_depth_table() -> list[list[str]]:
    rows = [["Depth N", "Description", "QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]]
    variants = [
        ("1 Block", "Main model (1×HSTA)", ""),
        ("2 Blocks", "2×HSTA Blocks", "2block"),
        ("4 Blocks", "4×HSTA Blocks", "4block"),
    ]
    for label, desc, frag in variants:
        row = [label, desc]
        for key in ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]:
            df = task_frame(key)
            if frag:
                sub = df[df["exp_name"].str.contains(frag)]
            else:
                sub = df[
                    (df["model"].astype(str).str.lower() == "hybrid")
                    & df["exp_name"].str.contains("seed42")
                    & ~df["exp_name"].str.contains("2block|4block")
                ]
            row.append(fmt_pct(sub["test_macro_f1"].iloc[0]) if not sub.empty else "-")
        rows.append(row)
    return rows


def build_transfer_table() -> list[list[str]]:
    df = pd.read_csv(ROOT / "results" / "transfer_s" / "all_results.csv")
    rows = [["Direction", "Zero-shot Acc", "Covered F1", "LoRA F1", "LoRA params (%)", "Full FT F1", "From-scratch F1", "FT - scratch"]]
    cases = [
        ("QUIC→TLS-40", "quic_to_tls40", "tls40_s"),
        ("TLS→QUIC-40", "tls_to_quic40", "quic40_s"),
        ("QUIC→TLS-60", "quic_to_tls60", "tls60_s"),
        ("TLS→QUIC-60", "tls_to_quic60", "quic60_s"),
    ]
    for label, frag, target_key in cases:
        zero = df[df["exp_name"].str.contains("zero_shot_" + frag)]
        lora = df[df["exp_name"].str.contains("hybrid_lora_" + frag)]
        ft = df[df["exp_name"].str.contains("full_ft_" + frag)]
        scratch_str = model_rows(target_key, ["Hybrid"])["Hybrid"][1]
        scratch = float(scratch_str.split("±")[0])
        ft_f1 = float(ft["test_macro_f1"].iloc[0]) * 100 if not ft.empty else math.nan
        rows.append(
            [
                label,
                fmt_pct(zero["full_accuracy"].iloc[0] if not zero.empty else None),
                fmt_pct(zero["covered_macro_f1"].iloc[0] if not zero.empty else None),
                fmt_pct(lora["test_macro_f1"].iloc[0] if not lora.empty else None),
                f"{float(lora['trainable_ratio'].iloc[0]) * 100:.2f}" if not lora.empty else "-",
                f"{ft_f1:.2f}" if not math.isnan(ft_f1) else "-",
                scratch_str,
                f"{ft_f1 - scratch:.2f}" if not math.isnan(ft_f1) else "-",
            ]
        )
    return rows


def pct_value(text: str) -> float:
    if text in {"", "-"}:
        return math.nan
    return float(str(text).split("±")[0])


def get_pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def existing_figure(filename: str) -> Path:
    primary = FIG_DIR / filename
    if primary.exists():
        return primary
    overleaf = OUT_DIR / "overleaf_jnca" / "figures" / filename
    if overleaf.exists():
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overleaf, primary)
        return primary
    return primary


def save_figure(fig, filename: str, plt_module) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt_module.close(fig)
    return path


def plot_hsta_architecture(plt_module) -> Path:
    labels = [
        "Packet\nsequence",
        "Mamba\nencoding",
        "Transition\nMLP",
        "High-level\nattention",
        "Refinement\nMLP",
        "Pooling +\nclassifier",
    ]
    colors = ["#EEF2F7", "#DCEBFA", "#E7F3EA", "#FFF2D8", "#F5E6EA", "#E9E4F4"]
    fig, ax = plt_module.subplots(figsize=(9.2, 2.2))
    ax.set_axis_off()
    x_positions = list(range(len(labels)))
    for x, label, color in zip(x_positions, labels, colors):
        box = plt_module.Rectangle(
            (x - 0.42, 0.42),
            0.84,
            0.58,
            linewidth=1.2,
            edgecolor="#39424E",
            facecolor=color,
            zorder=2,
        )
        ax.add_patch(box)
        ax.text(x, 0.71, label, ha="center", va="center", fontsize=9, color="#1F2933", zorder=3)
        if x < len(labels) - 1:
            ax.annotate(
                "",
                xy=(x + 0.56, 0.71),
                xytext=(x + 0.44, 0.71),
                arrowprops={"arrowstyle": "->", "lw": 1.4, "color": "#39424E"},
                zorder=4,
            )
    ax.text(2.5, 1.23, "HSTA Block feature extraction flow", ha="center", va="center", fontsize=10, weight="bold", color="#1F2933")
    ax.set_xlim(-0.65, len(labels) - 0.35)
    ax.set_ylim(0.18, 1.42)
    return save_figure(fig, "fig1_hsta_architecture.png", plt_module)


def plot_main_macro_f1(plt_module) -> Path:
    tasks = ["QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]
    task_keys = ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]
    series = {
        "GRU": [pct_value(model_rows(k, ["GRU"])["GRU"][1]) for k in task_keys],
        "Transformer": [pct_value(model_rows(k, ["Transformer"])["Transformer"][1]) for k in task_keys],
        "NetMamba-adapted": [pct_value(sota_rows(k)["NetMamba-adapted"][1]) for k in task_keys],
        "HSTA-Hybrid": [pct_value(model_rows(k, ["Hybrid"])["Hybrid"][1]) for k in task_keys],
    }
    colors = ["#7A7A7A", "#4C78A8", "#72B7B2", "#F58518"]
    fig, ax = plt_module.subplots(figsize=(7.2, 4.2))
    width = 0.18
    x = list(range(len(tasks)))
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for (label, values), color, offset in zip(series.items(), colors, offsets):
        ax.bar([v + offset for v in x], values, width=width, label=label, color=color)
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_ylim(84, 98.5)
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(ncol=2, frameon=False, fontsize=8)
    ax.set_title("Main Macro-F1 Comparison")
    return save_figure(fig, "fig2_main_macro_f1.png", plt_module)


def plot_ablation_macro_f1(plt_module) -> Path:
    rows = build_ablation_table()[1:]
    tasks = ["QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]
    labels = [row[0].replace("HSTA-Hybrid (Proposed)", "HSTA-Hybrid") for row in rows]
    colors = ["#9E9E9E", "#6BAED6", "#74C476", "#F58518"]
    fig, ax = plt_module.subplots(figsize=(7.2, 4.2))
    width = 0.18
    x = list(range(len(tasks)))
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for row, label, color, offset in zip(rows, labels, colors, offsets):
        values = [pct_value(v) for v in row[1:]]
        ax.bar([v + offset for v in x], values, width=width, label=label, color=color)
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_ylim(86, 98)
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(ncol=2, frameon=False, fontsize=8)
    ax.set_title("Attention-Position Ablation")
    return save_figure(fig, "fig3_ablation_macro_f1.png", plt_module)


def plot_transfer_macro_f1(plt_module) -> Path:
    rows = build_transfer_table()[1:]
    directions = [row[0].replace("→", "->") for row in rows]
    lora = [pct_value(row[3]) for row in rows]
    full_ft = [pct_value(row[5]) for row in rows]
    scratch = [pct_value(row[6]) for row in rows]
    fig, ax = plt_module.subplots(figsize=(7.6, 4.2))
    width = 0.22
    x = list(range(len(directions)))
    ax.bar([v - width for v in x], lora, width=width, label="LoRA", color="#72B7B2")
    ax.bar(x, full_ft, width=width, label="Full FT", color="#F58518")
    ax.bar([v + width for v in x], scratch, width=width, label="Scratch target", color="#4C78A8")
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_ylim(76, 99)
    ax.set_xticks(x)
    ax.set_xticklabels(directions, rotation=15, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Cross-Protocol Adaptation")
    return save_figure(fig, "fig4_transfer_macro_f1.png", plt_module)


def generate_result_figures() -> dict[str, Path]:
    legacy = FIG_DIR / "fig5_transfer_macro_f1.png"
    if legacy.exists():
        legacy.unlink()
    try:
        plt_module = get_pyplot()
        return {
            "hsta_architecture": plot_hsta_architecture(plt_module),
            "main_macro_f1": plot_main_macro_f1(plt_module),
            "ablation_macro_f1": plot_ablation_macro_f1(plt_module),
            "transfer_macro_f1": plot_transfer_macro_f1(plt_module),
        }
    except ModuleNotFoundError:
        figures = {
            "hsta_architecture": existing_figure("fig1_hsta_architecture.png"),
            "main_macro_f1": existing_figure("fig2_main_macro_f1.png"),
            "ablation_macro_f1": existing_figure("fig3_ablation_macro_f1.png"),
            "transfer_macro_f1": existing_figure("fig4_transfer_macro_f1.png"),
        }
        missing = [str(path) for path in figures.values() if not path.exists()]
        if missing:
            raise RuntimeError("matplotlib is unavailable and generated figures are missing: " + "; ".join(missing))
        return figures


def build_graphical_abstract(plt_module, figures: dict[str, Path]) -> Path:
    fig, ax = plt_module.subplots(figsize=(12, 4.5))
    ax.set_axis_off()
    blocks = [
        ("30-packet\nside-channel input", "#EEF2F7"),
        ("Mamba sequence\nencoding", "#DCEBFA"),
        ("Transition MLP\nrepresentation", "#E7F3EA"),
        ("High-level\nattention", "#FFF2D8"),
        ("Refinement +\nclassification", "#F5E6EA"),
    ]
    for idx, (label, color) in enumerate(blocks):
        x = 0.08 + idx * 0.18
        rect = plt_module.Rectangle((x, 0.48), 0.14, 0.22, linewidth=1.3, edgecolor="#39424E", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + 0.07, 0.59, label, ha="center", va="center", fontsize=10, color="#1F2933")
        if idx < len(blocks) - 1:
            ax.annotate("", xy=(x + 0.165, 0.59), xytext=(x + 0.145, 0.59), arrowprops={"arrowstyle": "->", "lw": 1.4, "color": "#39424E"})
    ax.text(0.5, 0.86, "HSTA-Hybrid for lightweight encrypted QUIC/TLS traffic classification", ha="center", va="center", fontsize=14, weight="bold", color="#1F2933")
    ax.text(0.5, 0.25, "Macro-F1: QUIC-40 91.09%, QUIC-60 90.28%, TLS-40 96.78%, TLS-60 96.29%", ha="center", va="center", fontsize=11, color="#1F2933")
    ax.text(0.5, 0.13, "Only packet size, direction, and inter-arrival time from the first 30 packets are used.", ha="center", va="center", fontsize=10, color="#4B5563")
    path = GRAPHICAL_ABSTRACT
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    fig.savefig(GRAPHICAL_ABSTRACT_TIF, dpi=300, format="tiff", bbox_inches="tight")
    plt_module.close(fig)
    figures["graphical_abstract"] = path
    figures["graphical_abstract_tif"] = GRAPHICAL_ABSTRACT_TIF
    return path


def write_figure_captions_doc(path: Path) -> None:
    doc = Document()
    set_doc_defaults(doc, "en")
    set_core_properties(doc, "Figure Captions - " + MANUSCRIPT_TITLE, "Separate figure captions and graphical abstract caption", "Submission support")
    doc.add_heading("Figure Captions", level=1)
    captions = [
        ("Figure 1", "Schematic of the five-stage HSTA Block."),
        ("Figure 2", "Macro-F1 comparison of main models on QUIC-40, QUIC-60, TLS-40, and TLS-60."),
        ("Figure 3", "Attention-position ablation comparison showing that attention is most effective after state-space transformation."),
        ("Figure 4", "Cross-protocol transfer comparison under zero-shot, LoRA adaptation, full fine-tuning, and target-domain training settings."),
        ("Graphical Abstract", "Overview of the HSTA-Hybrid encrypted traffic classification workflow and the main Macro-F1 results."),
    ]
    for label, caption in captions:
        p = doc.add_paragraph()
        run = p.add_run(f"{label}. ")
        run.bold = True
        p.add_run(caption)
    doc.save(path)


def write_figure_upload_zip(figures: dict[str, Path]) -> None:
    entries = [
        (figures["hsta_architecture"], "Figure_1_HSTA_Block.png"),
        (figures["main_macro_f1"], "Figure_2_Main_Macro_F1.png"),
        (figures["ablation_macro_f1"], "Figure_3_Attention_Ablation.png"),
        (figures["transfer_macro_f1"], "Figure_4_Cross_Protocol_Transfer.png"),
        (GRAPHICAL_ABSTRACT, "Graphical_Abstract.png"),
        (GRAPHICAL_ABSTRACT_TIF, "Graphical_Abstract.tif"),
        (FIGURE_CAPTIONS_DOCX, "Figure_Captions.docx"),
    ]
    missing = [str(source.relative_to(ROOT)) for source, _ in entries if not source.exists()]
    if missing:
        raise FileNotFoundError("Cannot build figure upload zip; missing files: " + ", ".join(missing))
    if FIGURE_UPLOAD_ZIP.exists():
        FIGURE_UPLOAD_ZIP.unlink()
    with ZipFile(FIGURE_UPLOAD_ZIP, "w", ZIP_DEFLATED) as zf:
        for source, arcname in entries:
            zf.write(source, arcname)


def extract_confusion_table() -> list[list[str]]:
    tables = source_tables()
    if 10 in tables:
        return tables[10]
    return [["Task", "True class", "Predicted class", "Errors", "Ratio (%)"]]


def extract_appendix_tables() -> tuple[list[list[str]], list[list[str]]]:
    tables = source_tables()
    return tables.get(11, []), tables.get(12, [])


def add_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def keep_table_row_intact(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = tr_pr.find(qn("w:tblHeader"))
    if tbl_header is None:
        tbl_header = OxmlElement("w:tblHeader")
        tr_pr.append(tbl_header)
    tbl_header.set(qn("w:val"), "true")


def add_borderless_note(doc: Document, text: str, italic: bool = True) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = italic
    r.font.size = Pt(9)


def set_doc_defaults(doc: Document, lang: str) -> None:
    styles = doc.styles
    styles["Normal"].font.name = "Times New Roman"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体" if lang == "cn" else "Times New Roman")
    styles["Normal"].font.size = Pt(12 if lang == "en" else 10.5)
    if lang == "en":
        styles["Normal"].paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    for style_name, size in [("Title", 16), ("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11)]:
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体" if lang == "cn" else "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)


def set_core_properties(doc: Document, title: str, subject: str, category: str) -> None:
    props = doc.core_properties
    props.title = title
    props.subject = subject
    props.author = CORE_PROPERTY_AUTHOR
    props.last_modified_by = CORE_PROPERTY_AUTHOR
    props.keywords = MANUSCRIPT_KEYWORDS
    props.category = category
    props.comments = "Generated manuscript support file; replace author metadata before final submission if required."


def set_section_margins(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.8)


def enable_continuous_line_numbers(doc: Document) -> None:
    for section in doc.sections:
        sect_pr = section._sectPr
        ln_num = sect_pr.find(qn("w:lnNumType"))
        if ln_num is None:
            ln_num = OxmlElement("w:lnNumType")
            sect_pr.append(ln_num)
        ln_num.set(qn("w:countBy"), "1")
        ln_num.set(qn("w:restart"), "continuous")


def clear_paragraph(paragraph) -> None:
    for child in list(paragraph._p):
        paragraph._p.remove(child)


def add_page_number_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def add_page_numbers(doc: Document) -> None:
    for section in doc.sections:
        section.footer.is_linked_to_previous = False
        paragraph = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
        clear_paragraph(paragraph)
        add_page_number_field(paragraph)


def suppress_line_numbers(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:suppressLineNumbers")) is None:
        p_pr.append(OxmlElement("w:suppressLineNumbers"))


def add_compact_table_trailer(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(1)
    suppress_line_numbers(p)


def apply_english_review_format(doc: Document) -> None:
    set_section_margins(doc)
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    enable_continuous_line_numbers(doc)
    add_page_numbers(doc)


def add_table(doc: Document, caption: str, rows: list[list[str]], note: str | None = None, font_size: float = 8.5) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(caption)
    r.bold = True
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    if table.rows:
        repeat_table_header(table.rows[0])
    for i, row in enumerate(rows):
        keep_table_row_intact(table.rows[i])
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = str(val)
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.keep_together = True
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                for run in para.runs:
                    run.font.size = Pt(font_size)
                    run.font.name = "Times New Roman"
            if i == 0:
                add_cell_shading(cell, "D9EAF7")
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.bold = True
    if note:
        add_borderless_note(doc, note)


def add_figure_placeholder(doc: Document, caption: str, note: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("[Editable figure placeholder]")
    r.bold = True
    r.font.color.rgb = RGBColor(88, 88, 88)
    box = doc.add_table(rows=1, cols=1)
    box.style = "Table Grid"
    cell = box.cell(0, 0)
    cell.text = note
    for para in cell.paragraphs:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(90, 90, 90)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(caption)
    r2.bold = True


def add_figure(doc: Document, caption: str, image_path: Path | None, fallback_note: str) -> None:
    if image_path and image_path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(image_path), width=Cm(15.2))
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(caption)
        r2.bold = True
        return
    add_figure_placeholder(doc, caption, fallback_note)


def add_title_page(doc: Document, lang: str) -> None:
    title_cn = "面向轻量级加密 QUIC/TLS 流量分类的混合状态空间转换与注意力建模方法"
    title_en = "Hybrid State-Space Transition-Attention Modeling for Lightweight Encrypted QUIC/TLS Traffic Classification"
    if lang == "cn":
        doc.add_paragraph(title_cn, style="Title")
        doc.add_paragraph(title_en)
        doc.add_paragraph("作者：Author One; Author Two; Author Three [占位，请替换]")
        doc.add_paragraph("单位：Affiliation 1; Affiliation 2 [占位，请替换]")
        doc.add_paragraph("通信作者：Corresponding Author, email@example.com [占位，请替换]")
        doc.add_paragraph("目标期刊：Journal of Network and Computer Applications")
    else:
        doc.add_paragraph(title_en, style="Title")
        doc.add_paragraph("Author One; Author Two; Author Three [placeholder]")
        doc.add_paragraph("Affiliation 1; Affiliation 2 [placeholder]")
        doc.add_paragraph("Corresponding author: Corresponding Author, email@example.com [placeholder]")
        doc.add_paragraph("Target journal: Journal of Network and Computer Applications")
    doc.add_section(WD_SECTION.NEW_PAGE)


CN_SECTIONS = [
    (
        "摘要",
        [
            "随着 TLS 1.3 与 QUIC 在互联网通信中的广泛部署，传统依赖端口号、明文载荷或深度包检测的流量识别方法受到显著限制。现代加密流量分类通常只能使用包大小、方向和相邻包到达时间间隔等侧信道特征，而这些特征在细粒度服务之间常呈现高度相似的行为模式。",
            "本文提出一种面向轻量级加密 QUIC/TLS 流量分类的 Hybrid State-space Transition-Attention Block（HSTA Block）。该模块将 Mamba 状态空间序列编码、Transition MLP 表示转换、高层注意力重加权和 Refinement MLP 特征重整组织为统一特征提取流程。其设计目标不是简单堆叠网络层，而是在弱侧信道输入条件下先捕获包级顺序依赖，再在更稳定的高层表示空间中突出关键判别模式。",
            "在 CESNET-QUIC22 与 CESNET-TLS22 构建的 QUIC-40、QUIC-60、TLS-40 和 TLS-60 四个任务上，HSTA-Hybrid 在三随机种子重复实验中分别取得 91.09±0.20%、90.28±0.39%、96.78±0.14% 和 96.29±0.17% 的 Macro-F1，均优于 MLP、CNN、LSTM、GRU、Transformer 以及统一轻量输入下适配的 30pktTCNET 和 NetMamba 基线。进一步的注意力位置消融、堆叠深度、复杂度、推理效率、跨协议迁移和类别级错误分析表明，性能提升主要来自状态空间序列建模、表示转换和高层注意力重加权之间的顺序协同。该研究为现代加密协议场景中的细粒度流量分类和协议自适应部署提供了可复现的轻量级建模方案。",
        ],
    ),
    (
        "关键词",
        ["加密流量分类；QUIC；TLS；Mamba；状态空间模型；跨协议迁移"],
    ),
    (
        "Highlights",
        [
            "提出 HSTA Block，将 Mamba 状态空间编码、表示转换、高层注意力和特征重整统一用于加密流量分类。",
            "在 QUIC-40、QUIC-60、TLS-40 和 TLS-60 四个任务上均取得最高平均 Macro-F1。",
            "三随机种子消融表明，注意力应后置于状态空间编码和 Transition MLP 之后。",
            "同时评估参数量、FLOPs、推理延迟、吞吐量、堆叠深度和 QUIC/TLS 跨协议迁移。",
        ],
    ),
    (
        "1 引言",
        [
            "互联网流量正在从可见协议字段和明文载荷分析快速转向加密条件下的行为识别。TLS 1.3 简化握手并强化密码套件，QUIC 则将可靠传输、多路复用、连接迁移与 TLS 加密机制整合在 UDP 之上。这些机制提升了隐私与性能，同时削弱了网络管理、安全监测和服务质量保障中传统流量识别技术的可用性。",
            "在明文不可见场景下，模型只能使用包大小、上下行方向和相邻包到达时间间隔等传输侧信道特征。此类特征具有时间顺序性，也存在噪声强、信息弱和类别间行为重叠的问题。特别是在 QUIC 与 TLS 并存的网络中，协议栈差异会进一步改变包序列形态，使单一协议上训练的模型难以直接迁移。",
            "针对上述问题，本文从网络应用场景出发设计 HSTA Block。该模块先以 Mamba 捕获包级序列中的方向切换、包长变化和突发传输，再以 Transition MLP 将状态表示转换为更适合分类的高层空间，随后通过注意力模块进行关键模式重加权，最后用 Refinement MLP 重整特征并输入分类头。本文贡献包括四点：构建 QUIC/TLS 40 类和 60 类统一任务；提出 HSTA Block 轻量混合架构；通过消融和类别级错误分析验证结构机制；从复杂度、效率和跨协议迁移角度评估部署适用性。",
        ],
    ),
    (
        "2 背景与相关工作",
        [
            "早期网络流量分类依赖端口号、协议字段、DPI 规则或人工统计特征，但动态端口、加密传输、CDN 和应用快速迭代持续降低这些方法的鲁棒性。深度学习方法将特征提取和分类器学习统一起来，可从包序列、突发模式和流级表示中自动学习判别特征。",
            "QUIC 与 TLS 是当前互联网加密通信的重要基础。TLS 通常运行于 TCP 之上，而 QUIC 运行于 UDP 并内置可靠传输、多路复用和 TLS 加密。CESNET-TLS22、CESNET-QUIC22 与 DataZoo 为真实骨干网场景下的细粒度服务分类提供了可复现实验基础。",
            "CNN、RNN、Transformer、预训练流量模型和图神经网络已被用于加密流量分类。与此同时，结构化状态空间模型和 Mamba 在长序列建模中表现出线性复杂度和选择性记忆优势。本文关注的是在仅使用 30 个包、每包三维侧信道特征的轻量在线设置下，如何结合状态空间序列建模和高层注意力选择来提升细粒度识别能力。",
        ],
    ),
    (
        "3 问题定义与方法动机",
        [
            "给定一个加密流样本，本文将其表示为长度 T=30 的包级序列 X=[x1,...,xT]，其中 xt 包含包大小、方向和相邻包到达时间间隔。若流长度超过 30 个包，则截取前 30 个包；若不足 30 个包，则在预处理阶段补齐。模型不使用明文载荷、域名字段、应用层内容或 DPI 规则特征。",
            "分类目标是学习映射 fθ:X→y，其中 y 属于 QUIC-40、QUIC-60、TLS-40 或 TLS-60 的闭集类别空间。训练阶段采用交叉熵损失，并以验证集 Macro-F1 进行模型选择和早停。由于类别不均衡和细粒度类别行为重叠，Macro-F1 被作为比 Accuracy 更核心的性能指标。",
            "设计动机来自三个观察：包级侧信道序列包含方向切换和突发传输等顺序依赖；原始低层特征噪声较强，直接前置注意力可能关注短期波动；经过状态空间编码和非线性转换后的高层表示更适合执行全局重加权。因此，HSTA Block 采用“序列编码—表示转换—高层注意力—特征重整”的顺序。",
        ],
    ),
    (
        "4 所提方法",
        [
            "整体模型由输入投影层、HSTA Block、序列池化层和独立 MLP 分类头组成。输入投影层将三维包级侧信道特征映射到隐藏空间；HSTA Block 负责混合序列特征提取；平均池化得到流级表示；分类头输出类别概率。",
            "HSTA Block 包含四个阶段。第一，连续 Mamba 模块利用选择性状态空间机制捕获包级序列依赖。第二，Transition MLP 对 Mamba 输出进行非线性变换和空间对齐。第三，注意力模块在高层表示中计算 Query、Key 和 Value 的相关性，对关键包段或特征组合赋予更大权重。第四，Refinement MLP 对重加权表示进行融合与重整，使其更适合池化和分类。",
            "训练采用批大小 512、隐藏维度 128、dropout 0.15、Mamba 状态维度 16、局部卷积核大小 4 和通道扩展因子 2。主模型采用一个 HSTA Block；深度敏感性实验比较 1、2 和 4 个 HSTA Block。所有模型使用相同输入特征、数据划分和评价指标，以保证比较公平。",
        ],
    ),
    (
        "5 实验设置",
        [
            "实验基于 CESNET-QUIC22 和 CESNET-TLS22，并通过 DataZoo 导出前 30 个包的包大小、方向和相邻包到达时间间隔。本文构建 QUIC-40、QUIC-60、TLS-40 和 TLS-60 四个任务，用以覆盖不同协议、类别规模和类别不均衡程度。",
            "比较模型包括 MLP、CNN、LSTM、GRU、Transformer、HSTA-Hybrid 以及统一轻量输入条件下适配的 30pktTCNET-adapted 和 NetMamba-adapted。需要强调的是，适配先进结构基线仅用于相同包级侧信道输入下的公平结构比较，不代表原始方法完整输入管线、预训练流程或特征工程设置下的最终性能。",
            "除单一随机种子的传统基线外，Transformer、HSTA-Hybrid、适配先进结构基线和消融变体均采用三个随机种子重复训练并报告 Mean±Std。评价指标包括 Accuracy、Macro-F1、参数量、FLOPs、前向延迟、吞吐量、显存峰值、zero-shot、LoRA 与 full fine-tuning 的跨协议迁移结果。",
        ],
    ),
    (
        "6 结果与分析",
        [
            "主实验表明，HSTA-Hybrid 在四个任务上均取得最高平均 Macro-F1。相较 NetMamba-adapted，HSTA-Hybrid 在 QUIC-40、QUIC-60、TLS-40 和 TLS-60 上分别提升约 1.21、1.32、0.57 和 0.11 个百分点；相较 30pktTCNET-adapted，分别提升约 2.06、1.43、0.72 和 1.01 个百分点。QUIC 任务收益更明显，说明复杂现代传输协议更依赖包级顺序建模与高层关键模式选择的协同。",
            "类别规模扩展实验显示，当类别数从 40 增加到 60 时，QUIC 的 Macro-F1 从 91.09±0.20% 降至 90.28±0.39%，TLS 从 96.78±0.14% 降至 96.29±0.17%。在更多低频类别加入后，模型仍保持较高 Macro-F1，体现出较好的类别规模扩展性。",
            "注意力位置消融证明，性能提升并非来自简单加入注意力模块。完整 HSTA Block 在四个任务上均优于无注意力、前置注意力和中间注意力变体，说明注意力更适合在 Mamba 序列编码和 Transition MLP 转换之后执行。复杂度和效率结果进一步显示，HSTA-Hybrid 参数量低于 Transformer，并在小批量和中等批量推理中保持较好的性能-效率折中。",
            "跨协议迁移实验显示，zero-shot 直接迁移效果较差，说明 QUIC 与 TLS 在类别集合和协议行为上存在显著分布差异。LoRA 只训练约 5.36%–5.75% 参数即可完成一定程度适配，但仍弱于 full fine-tuning。Full fine-tuning 在 QUIC→TLS 方向表现接近或略高于目标协议从头训练，而 TLS→QUIC 方向低于 QUIC 从头训练，反映出跨协议迁移的方向不对称性。",
        ],
    ),
    (
        "7 讨论",
        [
            "HSTA Block 的有效性主要来自结构顺序与加密流量特征形成过程的匹配。低层阶段捕获包级动态依赖，高层阶段选择更稳定的判别模式，Refinement MLP 再对重加权表示进行整理。该机制对 QUIC 尤其有效，可能因为 QUIC 的多路复用、连接迁移和 UDP 上可靠传输机制带来更复杂的序列行为。",
            "效率结果也提示，理论 FLOPs 不能完全等价于实际延迟。30pktTCNET-adapted 在部分 batch size 下延迟和吞吐更优，但 Macro-F1 明显低于 HSTA-Hybrid；NetMamba-adapted 理论 FLOPs 较低，却未在短序列设置下取得最低实测延迟。因此，本文更保守地将 HSTA-Hybrid 定位为分类性能优先且兼顾小批量/中等批量在线推理的折中方案。",
            "本文仍存在局限：仅使用前 30 个包的闭集分类设置，未覆盖未知类别拒识、长期时间漂移和跨采集环境泛化；推理效率主要在单一 GPU 平台测试；适配先进结构基线并不等价于原始方法完整复现。未来可进一步研究开放集识别、自监督预训练、协议自适应持续学习和真实在线部署评估。",
        ],
    ),
    (
        "8 结论",
        [
            "本文提出 HSTA Block，用于轻量级 QUIC/TLS 加密流量细粒度分类。该模块将状态空间序列编码、表示转换、高层注意力重加权和特征重整组织为统一流程，在仅依赖包大小、方向和到达时间间隔的侧信道输入下提升了四个任务的 Macro-F1。",
            "大量实验表明，HSTA-Hybrid 的优势来自结构协同而非单纯增加注意力或模型深度。消融、效率、堆叠深度、迁移和错误分析共同说明，该方法适用于现代加密协议下的细粒度服务识别，并为后续协议自适应和可部署加密流量分类研究提供了基础。",
        ],
    ),
]


EN_SECTIONS = [
    (
        "Abstract",
        [
            "TLS 1.3 and QUIC push fine-grained traffic classification toward inference from short side-channel traces rather than payload inspection. In this setting, the central question is not only which classifier reports the highest score, but how a lightweight model should transform the weak packet-size, direction, and timing evidence available before a flow is complete. We propose a Hybrid State-space Transition-Attention Block (HSTA Block) for encrypted QUIC/TLS classification under a fixed first-30-packet input. Instead of applying attention directly to raw traces, HSTA first encodes packet sequences with Mamba, transforms the representation with a Transition MLP, applies attention after the representation has become more stable, and consolidates the reweighted features with a Refinement MLP. On QUIC-40, QUIC-60, TLS-40, and TLS-60, HSTA-Hybrid achieves Macro-F1 scores of 91.09±0.20%, 90.28±0.39%, 96.78±0.14%, and 96.29±0.17%, respectively. Under the same input constraint, it outperforms MLP, CNN, LSTM, GRU, Transformer, and two adapted advanced baselines. Ablation, efficiency, depth-sensitivity, cross-protocol transfer, and error analyses indicate that the improvement comes from stage order rather than from model depth or attention alone.",
        ],
    ),
    (
        "Keywords",
        ["Encrypted traffic classification; QUIC; TLS; Mamba; state-space model; cross-protocol transfer"],
    ),
    (
        "Highlights",
        [
            "HSTA Block combines Mamba encoding, transition, attention, and refinement.",
            "HSTA-Hybrid achieves the best Macro-F1 on four QUIC/TLS tasks.",
            "Ablation shows attention works best after state-space transformation.",
            "Efficiency, depth sensitivity, and cross-protocol transfer are evaluated.",
        ],
    ),
    (
        "1 Introduction",
        [
            "Internet traffic analysis is moving from inspection of visible protocol fields and plaintext payloads to behavioral inference under encryption. TLS 1.3 and QUIC improve privacy and transport performance, but they also remove or hide many of the features that older inspection pipelines used directly. For an online monitor, this changes fine-grained classification from content recognition into early-flow behavioral inference: the model must infer service identity from packet sizes, directions, and timing before a complete flow is available. The 30-packet observation window used in this paper therefore reflects a practical early-decision constraint, not only a convenient tensor length. These signals are sequential, noisy, and often shared by multiple services, so the modeling problem is to recover stable behavior from a deliberately restricted observation window.",
            "Recent encrypted-traffic literature shows that the main risk is not a shortage of neural architectures, but weak validity framing. Representation-oriented papers first justify the traffic view being learned; fast-classification and real-time analytics papers foreground latency and throughput; multi-flow and graph-based studies clarify the traffic unit being modeled; and critical empirical studies warn that strong scores can arise from shortcut features, outdated datasets, leakage-prone splits, or narrow collection periods. Together, these papers establish a stricter reader contract: a new classifier should state what information is observable, keep the comparison input controlled, define whether the claim concerns a single flow, a group of flows, or a deployment pipeline, and explain why the observed gain follows from a plausible mechanism.",
            "Motivated by this contract, we ask a deliberately narrow mechanism question: after packet-level dynamics are encoded, is attention more useful when it is applied to a transformed and more separable representation rather than to the raw early-flow trace? We design HSTA Block as a stage-ordered feature extractor. Mamba modules capture directional changes, packet-size dynamics, and burst patterns; a Transition MLP maps the sequence representation into a higher-level space; attention then reweights discriminative traffic patterns; and a Refinement MLP consolidates the result before pooling and classification. The resulting contributions are fourfold: a reproducible QUIC/TLS early-flow evaluation under a fixed 30-packet side-channel input; a lightweight hybrid state-space-and-attention architecture; mechanism-oriented ablation and error analyses that test attention placement rather than attention presence alone; and deployment-relevant evidence on complexity, inference efficiency, depth sensitivity, and cross-protocol adaptation.",
        ],
    ),
    (
        "2 Background and Related Work",
        [
            "Early traffic classification relied on ports, protocol fields, DPI rules, or manually designed statistics. Dynamic ports, encryption, content delivery infrastructures, and rapid application evolution have progressively weakened these assumptions. Recent work can be read along three connected axes: the representation available to a monitor, the traffic unit on which the decision is made, and the validity of the evaluation environment. Deep learning studies responded by learning from packet sequences, burst patterns, flow statistics, image-like flow representations, flow clusters, graph relationships, or multimodal combinations of traffic views. The strongest papers in this line define the visibility available to the monitor, identify the traffic unit being modeled, compare against controlled baselines, and discuss whether the learned signal is likely to survive outside the collection environment.",
            "TLS and QUIC are central to current encrypted communication. TLS usually runs over TCP, whereas QUIC runs over UDP and embeds reliable transport, multiplexing, connection migration, and TLS encryption. CESNET-TLS22, CESNET-QUIC22, and DataZoo provide realistic and reproducible foundations for fine-grained service classification in backbone traffic. The year-spanning TLS dataset further illustrates why temporal stability, data curation, and collection context matter when interpreting classifier performance.",
            "CNNs, recurrent models, Transformers, pretrained traffic models, graph neural networks, image-like flow encoders, and two-phase fast classifiers have all been explored for encrypted traffic classification. Pretraining-oriented models emphasize reusable datagram, packet, or flow representations learned from large traffic corpora, while recent Mamba-based models emphasize linear-time sequence modeling and efficiency. At the same time, diagnostic work on representation learning cautions that impressive scores can collapse when shortcuts, split artifacts, or representation leakage are removed. Our setting is therefore intentionally different: it uses only three packet-level side-channel features from the first 30 packets and does not include byte content, pretraining, multi-flow aggregation, or application-layer fields. Within this constrained setting, the main design question is how to order sequence encoding, nonlinear transformation, and attention so that the model captures stable traffic behavior rather than short-lived noise.",
        ],
    ),
    (
        "3 Problem Definition and Motivation",
        [
            "An encrypted flow is represented as a packet-level sequence X=[x1,...,xT] with T=30, where each xt contains packet size, direction, and packet inter-arrival time. Flows longer than 30 packets are truncated, while shorter flows are padded during preprocessing. No plaintext payload, domain name, application-layer content, or DPI-derived feature is used.",
            "The objective is to learn a mapping fθ:X→y for closed-set classification on QUIC-40, QUIC-60, TLS-40, or TLS-60. Models are trained with cross-entropy loss, and validation Macro-F1 is used for model selection and early stopping. Because the tasks are fine-grained and class-imbalanced, Macro-F1 is treated as the primary metric.",
            "The design is motivated by three observations. First, packet-level side channels carry order-sensitive behavior such as direction switching, burst transmission, and early response patterns. Second, the raw features are low-dimensional and noisy; applying attention directly to them may emphasize incidental fluctuations rather than class-level behavior. Third, state-space encoding and nonlinear transition can produce a representation in which discriminative patterns are more stable and easier to compare globally. HSTA Block therefore follows the order of sequence encoding, representation transformation, high-level attention, and feature refinement.",
        ],
    ),
    (
        "4 Proposed Method",
        [
            "The full model consists of an input projection layer, an HSTA Block, sequence pooling, and an independent MLP classification head. The projection layer maps three-dimensional packet-level side-channel features into a hidden space. The HSTA Block extracts hybrid sequential features, mean pooling produces a flow-level representation, and the classifier outputs class probabilities.",
            "HSTA Block has four stages. First, consecutive Mamba modules capture packet-level sequential dependencies through selective state-space modeling. Second, a Transition MLP performs nonlinear transformation and representation alignment, acting as a bridge between low-level sequence encoding and global comparison. Third, the attention module computes Query-Key-Value interactions in the transformed representation space and assigns larger weights to discriminative packet segments or feature combinations. Fourth, a Refinement MLP consolidates the reweighted representation for downstream pooling and classification.",
            "All experiments use a batch size of 512, a hidden dimension of 128, dropout of 0.15, Mamba state dimension of 16, local convolution kernel size of 4, and expansion factor of 2. The main model uses one HSTA Block; depth sensitivity is evaluated with one, two, and four blocks. All models share the same input features, data splits, and metrics for fair comparison.",
        ],
    ),
    (
        "5 Experimental Setup",
        [
            "Our evaluation is intentionally framed as an early-flow, closed-set classification setting. The experiments are based on CESNET-QUIC22 and CESNET-TLS22, exported through DataZoo as the first 30 packets with packet size, direction, and inter-arrival time. We build four tasks, QUIC-40, QUIC-60, TLS-40, and TLS-60, to cover different protocols, class scales, and imbalance levels while keeping the observable feature space fixed across all models. This design makes the comparison stricter than using richer per-flow metadata, but it keeps the modeling claim aligned with lightweight online deployment.",
            "The compared models include MLP, CNN, LSTM, GRU, Transformer, HSTA-Hybrid, and two adapted advanced baselines: 30pktTCNET-adapted and NetMamba-adapted. These adapted baselines are used only for fair structural comparison under the same lightweight side-channel input, and should not be interpreted as full reproductions of the original methods with their complete input pipelines or pretraining procedures. This boundary is stated explicitly so that performance differences are read as evidence about modeling choices under a shared input constraint rather than as claims about the original systems in their full settings.",
            "The evaluation is organized as an evidence ladder rather than a single score table. Transformer, HSTA-Hybrid, the adapted advanced baselines, and the ablation variants are repeated with three random seeds and reported as mean±standard deviation. Macro-F1 is used as the primary metric because fine-grained traffic tasks are class-imbalanced; Accuracy is reported as a secondary view. Parameters, FLOPs, forward latency, throughput, and peak GPU memory test deployment cost, while zero-shot transfer, LoRA adaptation, and full fine-tuning test whether the learned representation has reusable cross-protocol structure.",
        ],
    ),
    (
        "6 Results and Analysis",
        [
            "The main results show that HSTA-Hybrid achieves the best average Macro-F1 on all four tasks. Compared with NetMamba-adapted, it improves Macro-F1 by approximately 1.21, 1.32, 0.57, and 0.11 percentage points on QUIC-40, QUIC-60, TLS-40, and TLS-60, respectively. Compared with 30pktTCNET-adapted, the corresponding improvements are approximately 2.06, 1.43, 0.72, and 1.01 percentage points. The gain is larger on QUIC, which is consistent with the intuition that irregular transport behavior leaves more value for packet-order modeling and post-encoding attention.",
            "When the number of classes increases from 40 to 60, the Macro-F1 of HSTA-Hybrid decreases from 91.09±0.20% to 90.28±0.39% on QUIC, and from 96.78±0.14% to 96.29±0.17% on TLS. The degradation is moderate despite additional low-frequency services, suggesting that the learned representation is not tuned only to the easiest high-volume classes. At the same time, the drop is larger for QUIC, which reinforces the need to treat protocol behavior and class scale as separate sources of difficulty.",
            "The attention-position ablation is the main mechanism test and acts as a negative control for a simple ``attention always helps'' explanation. The complete HSTA Block outperforms no-attention, front-attention, and middle-attention variants on all tasks. This comparison matters because it shows that attention by itself is not the contribution; the contribution is the placement of attention after Mamba sequence encoding and Transition MLP transformation. Complexity and efficiency measurements further show that HSTA-Hybrid has fewer parameters than Transformer and offers a favorable performance-efficiency trade-off for small and medium batch inference.",
            "Cross-protocol transfer is evaluated as a stress test of representation reuse rather than as a claim of protocol-invariant classification. Direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior. LoRA trains only about 5.36%–5.75% of the parameters and provides partial adaptation, but remains weaker than full fine-tuning. Full fine-tuning transfers from QUIC to TLS as well as, or slightly better than, training from scratch on TLS, whereas TLS-to-QUIC transfer remains below QUIC training from scratch. This directional asymmetry suggests that part of the learned representation is reusable, but another part remains protocol-specific.",
        ],
    ),
    (
        "7 Discussion",
        [
            "The results should not be read only as a leaderboard. The more important point is that the tables test a mechanism: whether packet-level dynamics should be encoded before attention is applied. HSTA Block works because it first compresses packet-level dynamics into a structured representation, then reweights that representation after it is sufficiently stable for global comparison. This interpretation is supported by the attention-position ablation and by the larger gains on QUIC, whose multiplexing, connection migration, and reliable transport over UDP produce more complex sequential behavior.",
            "The efficiency results also show that theoretical FLOPs do not fully determine practical latency. 30pktTCNET-adapted has lower latency or higher throughput in some batch settings, but its Macro-F1 is clearly lower than that of HSTA-Hybrid. NetMamba-adapted has fewer theoretical FLOPs, but does not achieve the lowest measured latency in this short-sequence setting. We therefore position HSTA-Hybrid as a performance-oriented model that still maintains a practical trade-off for online or medium-batch inference rather than as the most latency-minimal option.",
            "The evidence remains bounded. The experiments support a stage-order claim under a controlled first-30-packet side-channel setting; they do not prove that HSTA-Hybrid would dominate feature-rich, byte-level, pretrained, multi-flow, open-set, multi-Gbps, or temporally shifted deployments. This distinction is important because recent diagnostic and robustness studies show that encrypted-traffic models may rely on dataset artifacts, change behavior across environments, or age poorly when protocol behavior changes. For that reason, the proposed model should be interpreted as a reproducible mechanism study and a strong lightweight baseline, not as a complete production traffic-intelligence system.",
        ],
    ),
    (
        "8 Threats to Validity",
        [
            "The evaluation boundary is part of the contribution, but it is also a threat to validity. By fixing the first-30-packet side-channel input, the experiments avoid mixing architectural effects with richer metadata, byte content, pretraining, or application-layer features. The resulting comparison is controlled, but it should not be read as a claim that the same ranking would hold under feature-rich pipelines or large-scale pretraining.",
            "External validity is limited by the datasets, time periods, and closed-set label spaces. CESNET-QUIC22 and CESNET-TLS22 provide realistic backbone traffic, yet the manuscript does not test unknown-class rejection, month-to-month temporal drift, multi-flow context, TCP-aware augmentation, or cross-collection generalization. Year-spanning TLS, robustness, and real-world drift studies show that temporal and environmental coverage can change how classifier performance should be interpreted, and recent shortcut analyses further show that split design can strongly affect apparent representation quality. Future evaluation should therefore include time-aware splits, independent collections, explicit shortcut checks, and robustness tests across capture environments.",
            "Construct validity is limited by the chosen metrics and deployment measurements. Macro-F1 is appropriate for class imbalance, but it does not capture calibration, rejection behavior, or operator cost. Efficiency is measured on one GPU platform, and the adapted advanced baselines are structural comparisons under a shared input constraint rather than full reproductions of their original systems. These limitations motivate open-set recognition, self-supervised pretraining, protocol-adaptive continual learning, and real online deployment studies.",
        ],
    ),
    (
        "9 Conclusion",
        [
            "This paper presented HSTA Block as a stage-ordered hybrid state-space and attention model for lightweight encrypted QUIC/TLS traffic classification. By aligning sequence encoding, representation transformation, attention reweighting, and refinement with the residual structure available in packet size, direction, and inter-arrival time, the model improves Macro-F1 on four controlled tasks under the same 30-packet input.",
            "The main takeaway is that stage order matters. Accuracy alone would be an incomplete story; the ablation, efficiency, depth, transfer, and error analyses show why the gain is tied to the interaction of modeling choices rather than to depth or attention alone. HSTA Block therefore provides a reproducible and practically bounded basis for fine-grained service identification under modern encrypted protocols, while leaving open-set, time-aware, and cross-collection robustness as the next research targets.",
        ],
    ),
]


REFERENCES = [
    "J. Iyengar and M. Thomson, “QUIC: A UDP-Based Multiplexed and Secure Transport,” RFC 9000, Internet Engineering Task Force, 2021.",
    "E. Rescorla, “The Transport Layer Security (TLS) Protocol Version 1.3,” RFC 8446, Internet Engineering Task Force, 2018.",
    "J. Luxemburk and T. Čejka, “Fine-grained TLS services classification with reject option,” Computer Networks, vol. 220, article 109467, 2023.",
    "A. Azab, M. Khasawneh, S. Alrabaee, K.-K. R. Choo, and M. Sarsour, “Network traffic classification: Techniques, datasets, and challenges,” Digital Communications and Networks, vol. 10, no. 3, pp. 676-692, 2024.",
    "A. Sharma and A. H. Lashkari, “A survey on encrypted network traffic: identification/classification techniques, challenges, and future directions,” Computer Networks, vol. 257, article 110984, 2025.",
    "J. Luxemburk and K. Hynek, “DataZoo: Streamlining Traffic Classification Experiments,” CoNEXT SAFE Workshop, 2023.",
    "J. Luxemburk, K. Hynek, T. Čejka, A. Lukačovič, and P. Šiška, “CESNET-QUIC22: A Large One-Month QUIC Network Traffic Dataset from Backbone Lines,” Data in Brief, vol. 46, article 108888, 2023.",
    "E. Papadogiannaki and S. Ioannidis, “A Survey on Encrypted Network Traffic Analysis Applications, Techniques, and Countermeasures,” ACM Computing Surveys, vol. 54, no. 6, article 124, 2022.",
    "H. Zhang et al., “TFE-GNN: A Temporal Fusion Encoder Using Graph Neural Networks for Fine-grained Encrypted Traffic Classification,” WWW, pp. 2066-2075, 2023.",
    "R. Zhao et al., “MT-FlowFormer: A Semi-Supervised Flow Transformer for Encrypted Traffic Classification,” KDD, 2022.",
    "M. Lotfollahi et al., “Deep Packet: A Novel Approach for Encrypted Traffic Classification Using Deep Learning,” Soft Computing, vol. 24, pp. 1999-2012, 2020.",
    "R. Zhao et al., “Yet Another Traffic Classifier: A Masked Autoencoder Based Traffic Transformer with Multi-Level Flow Representation,” AAAI, vol. 37, no. 4, pp. 5420-5427, 2023.",
    "X. Meng et al., “Packet Representation Learning for Traffic Classification,” KDD, 2022.",
    "T. Wang et al., “NetMamba: Efficient Network Traffic Classification via Pre-training Unidirectional Mamba,” IEEE ICNP, 2024.",
    "X. Li et al., “Listen to Minority: Encrypted Traffic Classification for Class Imbalance with Contrastive Pre-Training,” IEEE SECON, 2023.",
    "X. Lin et al., “ET-BERT: A Contextualized Datagram Representation with Pre-training Transformers for Encrypted Traffic Classification,” WWW, pp. 633-642, 2022.",
    "N. Wickramasinghe, A. Shaghaghi, G. Tsudik, and S. Jha, “SoK: Decoding the Enigma of Encrypted Network Traffic Classifiers,” arXiv:2503.20093, 2025.",
    "B. Gahtan, R. J. Shahla, A. M. Bronstein, and R. Cohen, “Exploring QUIC Dynamics: A Large-Scale Dataset for Encrypted Traffic Analysis,” arXiv:2410.03728, 2024.",
    "J. Luxemburk, K. Hynek, R. Plný, and T. Čejka, “Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining,” arXiv:2502.12930, 2025.",
    "A. Vaswani et al., “Attention Is All You Need,” Advances in Neural Information Processing Systems, pp. 5998-6008, 2017.",
    "S. Hochreiter and J. Schmidhuber, “Long Short-Term Memory,” Neural Computation, vol. 9, no. 8, pp. 1735-1780, 1997.",
    "K. Cho et al., “Learning Phrase Representations Using RNN Encoder-Decoder for Statistical Machine Translation,” EMNLP, pp. 1724-1734, 2014.",
    "T. Dao and A. Gu, “Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality,” ICML, 2024.",
    "A. Gu, K. Goel, and C. Ré, “Efficiently Modeling Long Sequences with Structured State Spaces,” ICLR, 2022.",
    "A. Gu and T. Dao, “Mamba: Linear-Time Sequence Modeling with Selective State Spaces,” arXiv:2312.00752, 2023.",
    "E. J. Hu et al., “LoRA: Low-Rank Adaptation of Large Language Models,” ICLR, 2022.",
    "G. Zhou et al., “TrafficFormer: An Efficient Pre-trained Model for Traffic Data,” IEEE Symposium on Security and Privacy, 2025.",
    "K. Hynek et al., “CESNET-TLS-Year22: A Year-Spanning TLS Network Traffic Dataset from Backbone Lines,” Scientific Data, vol. 11, article 1156, 2024.",
    "G. Aceto, D. Ciuonzo, A. Montieri, and A. Pescapé, “Mobile Encrypted Traffic Classification Using Deep Learning: Experimental Evaluation, Lessons Learned, and Challenges,” IEEE Transactions on Network and Service Management, vol. 16, no. 2, pp. 445-458, 2019.",
    "G. Aceto, D. Ciuonzo, A. Montieri, V. Persico, and A. Pescapé, “DISTILLER: Encrypted Traffic Classification via Multimodal Multitask Deep Learning,” Journal of Network and Computer Applications, vol. 183, article 102985, 2021.",
    "X. Lin et al., “A Novel Multimodal Deep Learning Framework for Encrypted Traffic Classification,” IEEE/ACM Transactions on Networking, vol. 31, no. 3, pp. 1369-1384, 2023.",
    "A. Malekghaini, K. M. Ispoglou, D. Choffnes, and A. Mahanti, “Deep Learning for Encrypted Traffic Classification in the Face of Data Drift: An Empirical Study,” Computer Networks, vol. 225, article 109648, 2023.",
    "R. Zhao et al., “The Sweet Danger of Sugar: Debunking Representation Learning Based Network Traffic Classification,” ACM SIGCOMM, 2025.",
    "T. Shapira and Y. Shavitt, “FlowPic: A Generic Representation for Encrypted Traffic Classification and Applications Identification,” IEEE Transactions on Network and Service Management, 2021.",
    "Y. Wang, H. He, Y. Lai, and A. X. Liu, “A Two-Phase Approach to Fast and Accurate Classification of Encrypted Traffic,” IEEE/ACM Transactions on Networking, 2023.",
    "Z. Chen, G. Cheng, Z. Wei, D. Niu, and N. Fu, “Classify Traffic Rather Than Flow: Versatile Multi-Flow Encrypted Traffic Classification With Flow Clustering,” IEEE Transactions on Network and Service Management, 2024.",
    "C. Kattadige, K. N. Choi, A. Wijesinghe, A. Nama, K. Thilakarathna, S. Seneviratne, and G. Jourjon, “SETA++: Real-Time Scalable Encrypted Traffic Analytics in Multi-Gbps Networks,” IEEE Transactions on Network and Service Management, 2021.",
    "R. Xie et al., “Rosetta: Enabling Robust TLS Encrypted Traffic Classification in Diverse Network Environments with TCP-Aware Traffic Augmentation,” Proceedings of the ACM Turing Award Celebration Conference - China, 2023.",
    "Z. Li, H. Zhao, J. Zhao, Y. Jiang, and F. Bu, “SAT-Net: A Staggered Attention Network Using Graph Neural Networks for Encrypted Traffic Classification,” Journal of Network and Computer Applications, article 104069, 2025.",
]


def add_core_tables_and_figures(doc: Document, lang: str, figures: dict[str, Path]) -> None:
    tables = source_tables()
    if lang == "cn":
        add_table(doc, "表1  数据集和任务统计", tables[1])
        add_table(doc, "表2  适配先进结构基线的统一输入设置", tables[2])
        cap40 = "表3  40 类任务主实验与适配先进结构基线结果（单位：%）"
        cap60 = "表4  60 类任务主实验与适配先进结构基线结果（单位：%）"
        scaling = "表5  HSTA-Hybrid 从 40 类到 60 类的性能变化（Macro-F1，单位：%）"
        ablation = "表6  注意力位置消融实验结果（Macro-F1，单位：%）"
        eff = "表7  核心模型与适配先进结构基线复杂度及推理效率"
        depth = "表8  HSTA Block 堆叠深度敏感性实验（Macro-F1，单位：%）"
        transfer = "表9  跨协议迁移结果总览（单位：%）"
        confusion = "表10  HSTA-Hybrid 主要混淆类别对"
        note = "注：30pktTCNET-adapted 和 NetMamba-adapted 均为统一轻量包级侧信道输入下的适配版本。"
        fig_note = "图件源文件位于 paper/论文全部图_精修可编辑.drawio；当前生成稿保留可编辑替换位置。"
    else:
        doc.add_page_break()
        add_table(doc, "Table 1 Dataset and task statistics", translate_header_rows(tables[1]))
        add_table(doc, "Table 2 Adapted advanced baselines under the unified input setting", translate_header_rows(tables[2]))
        cap40 = "Table 3 Main results on 40-class tasks and adapted advanced baselines (%)"
        cap60 = "Table 4 Main results on 60-class tasks and adapted advanced baselines (%)"
        scaling = "Table 5 Performance change from 40 to 60 classes (Macro-F1, %)"
        ablation = "Table 6 Attention-position ablation results (Macro-F1, %)"
        eff = "Table 7 Complexity and measured inference efficiency"
        depth = "Table 8 Depth sensitivity of HSTA Block (Macro-F1, %)"
        transfer = "Table 9 Cross-protocol transfer results (%)"
        confusion = "Table 10 Major confused class pairs of HSTA-Hybrid"
        note = "Note: 30pktTCNET-adapted and NetMamba-adapted are adapted to the same lightweight packet-level side-channel input."
        fig_note = "The editable source is paper/论文全部图_精修可编辑.drawio; this manuscript keeps editable replacement positions."
    rows40, rows60 = build_main_result_tables()
    add_table(doc, cap40, rows40, note)
    add_figure(
        doc,
        "图2  主要模型在四个任务上的 Macro-F1 对比" if lang == "cn" else "Figure 2 Macro-F1 comparison of main models on four tasks",
        figures.get("main_macro_f1"),
        fig_note,
    )
    add_table(doc, cap60, rows60, note)
    add_table(doc, scaling, build_scaling_table())
    add_table(doc, ablation, build_ablation_table())
    add_figure(
        doc,
        "图3  注意力位置消融实验对比" if lang == "cn" else "Figure 3 Attention-position ablation comparison",
        figures.get("ablation_macro_f1"),
        fig_note,
    )
    add_table(doc, eff, build_efficiency_table())
    add_table(doc, depth, build_depth_table())
    add_table(doc, transfer, build_transfer_table())
    add_figure(
        doc,
        "图4  跨协议迁移结果对比" if lang == "cn" else "Figure 4 Cross-protocol transfer comparison",
        figures.get("transfer_macro_f1"),
        fig_note,
    )
    confusion_rows = extract_confusion_table()
    add_table(doc, confusion, translate_header_rows(confusion_rows) if lang == "en" else confusion_rows)


def translate_header_rows(rows: list[list[str]]) -> list[list[str]]:
    mapping = {
        "任务": "Task",
        "协议": "Protocol",
        "类数": "Classes",
        "序列长": "Seq. length",
        "流数(k)": "Flows (k)",
        "划分(k)": "Split (k)",
        "包记录(M)": "Packet records (M)",
        "每类流(k)": "Flows/class (k)",
        "适配基线": "Adapted baseline",
        "保留的核心思想": "Core idea retained",
        "本文统一适配方式与公平比较设置": "Unified adaptation and fair-comparison setting",
        "时间卷积建模与局部时序模式提取": "Temporal convolution modeling and local sequential pattern extraction",
        "Mamba-style 状态空间序列建模": "Mamba-style state-space sequence modeling",
        "将输入统一为每条流前 30 个包的包大小、方向和相邻包到达时间间隔三维侧信道特征；采用相同数据划分、训练协议和评价指标，用于比较时间卷积结构在相同部署假设下的适配效果。": "Uses the same three packet-level side-channel features from the first 30 packets of each flow: packet size, direction, and inter-arrival time. The same data splits, training protocol, and metrics are used to compare temporal convolution under the same deployment assumption.",
        "使用相同 30×3 包级侧信道输入、相同隐藏维度设置、训练协议和评价指标；用于比较纯状态空间序列建模与本文 HSTA Block 混合结构的差异。": "Uses the same 30 x 3 packet-level side-channel input, hidden-dimension setting, training protocol, and metrics to compare pure state-space sequence modeling with the proposed HSTA hybrid structure.",
        "结构变体": "Variant",
        "迁移方向": "Direction",
        "重叠类 F1": "Covered F1",
        "LoRA 参数%": "LoRA params (%)",
        "从头训练 F1": "From-scratch F1",
        "目标从头训练 F1": "Target scratch F1",
        "FT-从头训练": "FT - scratch",
        "真实类别（名称）": "True class (name)",
        "预测类别（名称）": "Predicted class (name)",
        "错误数量": "Errors",
        "占真实类别比例（%）": "Ratio within true class (%)",
        "DataZoo 标签": "DataZoo label",
        "是否属于40类": "In 40-class task",
        "流量名称": "Traffic name",
        "服务类别": "Service category",
        "是": "Yes",
        "否": "No",
    }
    return [[mapping.get(cell, cell).replace("（", " (").replace("）", ")") for cell in row] for row in rows]


def add_declarations(doc: Document, lang: str) -> None:
    if lang == "cn":
        doc.add_heading("声明", level=1)
        items = CN_STATEMENTS
    else:
        doc.add_heading("Declarations", level=1)
        items = EN_STATEMENTS
    for title, text in items:
        p = doc.add_paragraph()
        r = p.add_run(title + ": ")
        r.bold = True
        p.add_run(text)


def add_references(doc: Document, lang: str) -> None:
    doc.add_heading("参考文献" if lang == "cn" else "References", level=1)
    for i, ref in enumerate(REFERENCES, start=1):
        doc.add_paragraph(f"[{i}] {ref}")


def add_appendices(doc: Document, lang: str) -> None:
    quic, tls = extract_appendix_tables()
    if not quic or not tls:
        return
    doc.add_page_break()
    doc.add_heading("附录 A：QUIC 标签编号与流量名称映射" if lang == "cn" else "Appendix A. QUIC label-to-service mapping", level=1)
    add_table(doc, "表A1  QUIC 标签编号与流量名称映射" if lang == "cn" else "Table A1 QUIC label-to-service mapping", translate_header_rows(quic) if lang == "en" else quic, font_size=8.0)
    doc.add_heading("附录 B：TLS 标签编号与流量名称映射" if lang == "cn" else "Appendix B. TLS label-to-service mapping", level=1)
    add_table(doc, "表B1  TLS 标签编号与流量名称映射" if lang == "cn" else "Table B1 TLS label-to-service mapping", translate_header_rows(tls) if lang == "en" else tls, font_size=8.0)
    add_compact_table_trailer(doc)


WORD_CITATIONS = {
    "1 Introduction": {0: " [1,2,35,37]", 1: " [4,5,17,27,29,30,32,33,34,35,36,37,39]"},
    "1 引言": {0: " [1,2]"},
    "2 Background and Related Work": {
        0: " [4,5,8,29,30,31,34,36,39]",
        1: " [3,6,7]",
        2: " [16,20,24,25,33,34,35,39]",
    },
    "2 背景与相关工作": {
        0: " [4,5,8]",
        1: " [3,6,7]",
        2: " [16,20,24,25]",
    },
    "5 Experimental Setup": {
        0: " [3,6,7]",
        1: " [14]",
    },
    "5 实验设置": {
        0: " [3,6,7]",
        1: " [14]",
    },
    "6 Results and Analysis": {3: " [26]"},
    "6 结果与分析": {3: " [26]"},
    "7 Discussion": {2: " [17,32,33,36,37,38]"},
    "8 Threats to Validity": {1: " [28,32,33,38]"},
    "7 讨论": {2: " [28]"},
}


def add_word_citation(title: str, index: int, text: str) -> str:
    if title == "5 Experimental Setup" and index == 1:
        return text.replace("NetMamba-adapted.", "NetMamba-adapted [14].", 1)
    return text + WORD_CITATIONS.get(title, {}).get(index, "")


def build_doc(lang: str, out_path: Path, figures: dict[str, Path]) -> None:
    doc = Document()
    set_doc_defaults(doc, lang)
    set_core_properties(
        doc,
        MANUSCRIPT_TITLE if lang == "en" else "面向轻量级加密 QUIC/TLS 流量分类的混合状态空间转换与注意力建模方法",
        "English JNCA manuscript draft" if lang == "en" else "Chinese companion manuscript draft",
        "Manuscript",
    )
    add_title_page(doc, lang)
    sections = CN_SECTIONS if lang == "cn" else EN_SECTIONS
    for title, paras in sections:
        level = 1 if re.match(r"^\d+ |^(摘要|关键词|Abstract|Keywords|Highlights)", title) else 2
        doc.add_heading(title, level=level)
        for index, para in enumerate(paras):
            p = doc.add_paragraph(add_word_citation(title, index, para))
            p.paragraph_format.first_line_indent = Cm(0.74) if lang == "cn" and title not in ["关键词"] else None
        if title in ["4 所提方法", "4 Proposed Method"]:
            add_figure(
                doc,
                "图1  HSTA Block 五层混合特征提取模块示意图" if lang == "cn" else "Figure 1 Schematic of the five-stage HSTA Block",
                figures.get("hsta_architecture"),
                "Use the editable draw.io source to replace this placeholder before final submission.",
            )
        if title in ["6 结果与分析", "6 Results and Analysis"]:
            add_core_tables_and_figures(doc, lang, figures)
    add_declarations(doc, lang)
    add_references(doc, lang)
    add_appendices(doc, lang)
    if lang == "en":
        apply_english_review_format(doc)
    doc.save(out_path)


def build_highlights_doc(out_path: Path) -> None:
    doc = Document()
    set_doc_defaults(doc, "en")
    set_core_properties(doc, "Highlights - " + MANUSCRIPT_TITLE, "Elsevier-style highlights", "Submission support")
    doc.add_heading("Highlights", level=1)
    for item in dict(EN_SECTIONS)["Highlights"]:
        doc.add_paragraph(item, style="List Bullet")
    doc.save(out_path)


def build_author_statements_doc(out_path: Path) -> None:
    doc = Document()
    set_doc_defaults(doc, "en")
    set_core_properties(doc, "Author Statements - " + MANUSCRIPT_TITLE, "Author contribution and declaration placeholders", "Submission support")
    doc.add_heading("Author Statements", level=1)
    doc.add_paragraph("This file is generated as a submission-support document. Replace all placeholders and confirm all author roles before formal submission.")
    for title, text in EN_STATEMENTS:
        doc.add_heading(title, level=2)
        doc.add_paragraph(text)
    doc.save(out_path)


def build_declaration_of_interest_doc(out_path: Path) -> None:
    doc = Document()
    set_doc_defaults(doc, "en")
    set_core_properties(doc, "Declaration of Interest - " + MANUSCRIPT_TITLE, "Declaration of interest placeholder", "Submission support")
    doc.add_heading("Declaration of Interest Statement", level=1)
    doc.add_paragraph(
        "The authors declare that they have no known competing financial interests or personal relationships "
        "that could have appeared to influence the work reported in this paper. "
        "[placeholder; confirm with all authors before submission]"
    )
    doc.add_paragraph(
        "If any competing interest exists, replace this statement with a complete disclosure before formal submission."
    )
    doc.save(out_path)


def build_cover_letter_doc(out_path: Path) -> None:
    doc = Document()
    set_doc_defaults(doc, "en")
    set_core_properties(doc, "Cover Letter - " + MANUSCRIPT_TITLE, "Cover letter draft for JNCA submission", "Submission support")
    doc.add_paragraph("[Date]")
    doc.add_paragraph("Dear Editor-in-Chief / Handling Editor,")
    doc.add_paragraph(
        "Please consider our manuscript entitled \"Hybrid State-Space Transition-Attention Modeling for Lightweight Encrypted QUIC/TLS Traffic Classification\" "
        "for publication as a full research article in Journal of Network and Computer Applications."
    )
    doc.add_paragraph(
        "The manuscript addresses fine-grained encrypted QUIC/TLS traffic classification under a lightweight packet-level side-channel setting. "
        "It proposes an HSTA Block that combines Mamba-based state-space sequence encoding, representation transition, high-level attention, and refinement, "
        "and evaluates the method on four tasks derived from CESNET-QUIC22 and CESNET-TLS22."
    )
    doc.add_paragraph(
        "The work is positioned for the journal's audience because it concerns network traffic analysis, encrypted transport protocols, and deployable network monitoring methods. "
        "The manuscript includes main results, adapted-baseline comparisons, ablation, efficiency, depth-sensitivity, transfer, and class-level error analyses."
    )
    doc.add_paragraph(
        "All authors have approved the submission and agree with its submission to Journal of Network and Computer Applications. "
        "The manuscript is not under consideration elsewhere. [placeholder; confirm before submission]"
    )
    doc.add_paragraph(
        "The authors declare no known competing financial interests or personal relationships that could have influenced the work reported in this paper. "
        "[placeholder; confirm before submission]"
    )
    doc.add_paragraph("Suggested reviewers, opposed reviewers, funding information, and final corresponding-author details should be completed in the submission system if required. [placeholder]")
    doc.add_paragraph("Sincerely,")
    doc.add_paragraph("Corresponding Author [placeholder]\nAffiliation [placeholder]\nEmail: email@example.com [placeholder]")
    doc.save(out_path)


def write_upload_bundle(bundle_path: Path) -> None:
    entries = [
        (OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.docx", "JNCA_HSTA_Encrypted_Traffic_EN.docx"),
        (OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.pdf", "JNCA_HSTA_Encrypted_Traffic_EN.pdf"),
        (OUT_DIR / "Highlights.docx", "Highlights.docx"),
        (OUT_DIR / "Author_Statements.docx", "Author_Statements.docx"),
        (OUT_DIR / "Declaration_of_Interest_Statement.docx", "Declaration_of_Interest_Statement.docx"),
        (OUT_DIR / "Cover_Letter.docx", "Cover_Letter.docx"),
        (FIGURE_CAPTIONS_DOCX, "Figure_Captions.docx"),
        (GRAPHICAL_ABSTRACT, "Graphical_Abstract.png"),
        (GRAPHICAL_ABSTRACT_TIF, "Graphical_Abstract.tif"),
        (FIGURE_UPLOAD_ZIP, "FIGURES_FOR_UPLOAD.zip"),
        (OUT_DIR / "submission_upload_manifest.md", "submission_upload_manifest.md"),
        (OUT_DIR / "submission_checklist.md", "submission_checklist.md"),
        (OUT_DIR / "submission_format_audit.md", "submission_format_audit.md"),
        (GFA_COMPLIANCE_CHECK, "JNCA_GFA_COMPLIANCE_CHECK.md"),
        (PLACEHOLDER_REPLACEMENT_CHECK, "FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md"),
        (IMPORT_FORMAT_CHECK, "SUBMISSION_IMPORT_FORMAT_CHECK.md"),
        (LATEX_TROUBLESHOOTING, "LATEX_IMPORT_TROUBLESHOOTING.md"),
        (OVERLEAF_IMPORT_GUIDE, "OVERLEAF_IMPORT_GUIDE.md"),
        (OVERLEAF_DIRECT_ZIP, "UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip"),
        (EDITORIAL_SOURCE_ZIP, "JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip"),
    ]
    missing = [str(source.relative_to(ROOT)) for source, _ in entries if not source.exists()]
    if missing:
        raise FileNotFoundError("Cannot build upload bundle; missing files: " + ", ".join(missing))
    if bundle_path.exists():
        bundle_path.unlink()
    with ZipFile(bundle_path, "w", ZIP_DEFLATED) as zf:
        for source, arcname in entries:
            zf.write(source, arcname)


def write_overleaf_import_guide(path: Path) -> None:
    lines = [
        "# Overleaf Import Guide\n\n",
        "Use this note to avoid the common import mistake that causes many immediate Overleaf errors.\n\n",
        "## Why Many Errors Usually Appear\n",
        "- Overleaf errors usually come from uploading the mixed handoff bundle instead of the direct source zip.\n",
        "- Editorial Manager errors usually come from LaTeX files that still reference figure subfolders.\n",
        "- CJK or `ctexart` errors usually mean the Chinese XeLaTeX package is being compiled with pdfLaTeX.\n\n",
        "- `elsarticle.cls not found` means the compile environment lacks the Elsevier class; Overleaf normally provides it, while some submission systems may need their LaTeX environment updated or the official Elsevier template bundle handled by the portal.\n\n",
        "- `Undefined control sequence \\affiliation` should not appear in the regenerated English package because author affiliations use legacy-compatible `\\address[...]` markers.\n\n",
        "## First Fatal Error Map\n",
        "- Do not count the full error cascade as separate manuscript defects. First identify the first fatal log line, then apply the matching fix below.\n",
        "- `main.tex` not found: the wrong zip was uploaded, or the zip was re-packed with an extra top-level folder. Upload the generated `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` unchanged.\n",
        "- `elsarticle.cls not found`: the platform is missing the Elsevier class. This repository has the official template sources (`elsarticle.dtx` and `elsarticle.ins`) but no generated `elsarticle.cls`; use Overleaf or a portal/template environment that provides the class.\n",
        "- `Undefined control sequence \\affiliation`: use the regenerated package; its English `main.tex` uses `\\address[...]` affiliations for older Elsevier-class compatibility.\n",
        "- `File ...fig... not found`: use the Overleaf package for Overleaf, or the flat `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` for portals that reject subfolders.\n",
        "- `ctexart` or CJK package errors: the Chinese package or bilingual archive is being compiled with pdfLaTeX. Use the English package with pdfLaTeX, or compile the Chinese package with XeLaTeX.\n",
        "- Citation question marks after the first pass are not import-format errors; run BibTeX and the normal repeated LaTeX passes.\n\n",
        "## Upload This To Overleaf\n",
        "- `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` in this folder, or the identical source package `../jnca_english_overleaf_package.zip`.\n",
        "- Main file: `main.tex`.\n",
        "- Compiler: pdfLaTeX.\n",
        "- Bibliography: BibTeX with `elsarticle-num.bst`.\n\n",
        "- Zip hygiene: generated source zips use clean ASCII relative paths and exclude hidden/system files, absolute paths, and path traversal entries.\n\n",
        "- If Overleaf or the submission portal throws a long cascade of errors on import, open `LATEX_IMPORT_TROUBLESHOOTING.md` first.\n\n",
        "## Upload This To Editorial Manager / Elsevier Source Upload\n",
        "- `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` is a flat LaTeX source package for submission systems that reject figure subfolders or mixed bundles.\n",
        "- It contains root-level `main.tex`, `references.bib`, `elsarticle-num.bst`, `latexmkrc`, README, and the PNG figures referenced directly from `main.tex`.\n\n",
        "## Do Not Upload This To Overleaf\n",
        "- `JNCA_recommended_upload_bundle.zip` is a handoff/submission bundle, not a direct Overleaf source package.\n",
        "- It contains Word/PDF/support files and a nested Overleaf zip, so importing the whole bundle as an Overleaf project can produce many missing-main-file or wrong-file errors.\n",
        "- `../jnca_chinese_xelatex_package.zip` is only for checking the Chinese companion manuscript and must use XeLaTeX.\n\n",
        "## Quick Diagnosis\n",
        "- If Overleaf cannot find `main.tex`, you probably uploaded the handoff bundle instead of `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n",
        "- If `elsarticle.cls` is missing, the issue is the platform TeX installation or template support, not the manuscript body; try Overleaf first or contact the submission-system support team.\n",
        "- If Overleaf reports many CJK or `ctexart` errors, the Chinese package is being compiled with pdfLaTeX; switch that project to XeLaTeX.\n",
        "- If bibliography entries show as question marks after the first run, run BibTeX or let Overleaf finish the normal multi-pass compilation.\n",
    ]
    path.write_text("".join(lines), encoding="utf-8")


def write_import_format_check(path: Path) -> None:
    lines = [
        "# Submission Import Format Check\n\n",
        "This generated check separates the packages by platform so a mixed bundle is not imported as a LaTeX project.\n\n",
        "## Direct Overleaf Package\n",
        "- File to import: `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n",
        "- Required root files: `main.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, and `latexmkrc`.\n",
        "- Figure layout: PNG figures stay under `figures/`, and `main.tex` references the same `figures/...` paths.\n",
        "- Compiler settings: `main.tex`, pdfLaTeX, BibTeX.\n",
        "- Frontmatter compatibility: author affiliations use `\\address[...]`, not structured `\\affiliation[...]` fields.\n",
        "- Template dependency: `elsarticle-num.bst` is packaged from the official Elsevier template bundle; `elsarticle.cls` is expected from the platform TeX installation.\n",
        "- Zip-entry hygiene: clean ASCII relative paths only; no hidden/system files, absolute paths, backslash separators, or path traversal entries.\n",
        "- Expected use: Overleaf preview/editing of the English manuscript.\n\n",
        "## Editorial Manager Flat Source Package\n",
        "- File to upload when LaTeX source is requested: `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`.\n",
        "- Required layout: all `.tex`, `.bib`, `.bst`, `latexmkrc`, README, and PNG figures are at the zip root.\n",
        "- Figure layout: `main.tex` references PNG figures without `figures/` or any other subfolder prefix.\n",
        "- Template dependency: `elsarticle-num.bst` is packaged from the official Elsevier template bundle; `elsarticle.cls` is expected from the platform TeX installation.\n",
        "- Zip-entry hygiene: clean ASCII relative paths only; no hidden/system files, absolute paths, backslash separators, or path traversal entries.\n",
        "- The graphical abstract TIFF is supplied separately and is not referenced by `\\includegraphics`.\n\n",
        "## Do Not Upload As A LaTeX Project\n",
        "- `JNCA_recommended_upload_bundle.zip` is a handoff bundle, not a direct Overleaf or Editorial Manager LaTeX source project.\n",
        "- It contains Word/PDF/support documents and nested source zips; importing it as a LaTeX project can create many missing-entry and wrong-main-file errors.\n",
        "- `FIGURES_FOR_UPLOAD.zip` is only for separate artwork upload, not for compiling the manuscript.\n",
        "- `Graphical_Abstract.tif` is an artwork candidate, not a figure included from `main.tex`.\n\n",
        "## Error Triage\n",
        "- Start from the first fatal line in the compile log; later messages are often cascade errors.\n",
        "- `main.tex` not found: upload `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, not the handoff bundle.\n",
        "- Extra top-level folder after upload: import the generated zip directly instead of re-zipping the extracted folder.\n",
        "- Missing figures in Editorial Manager: upload `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` so images are root-level.\n",
        "- `elsarticle.cls not found`: use Overleaf first if possible, or confirm that the submission system's LaTeX environment supports Elsevier `elsarticle`.\n",
        "- `Undefined control sequence \\affiliation`: regenerate and upload the current source zip; current English sources use `\\address[...]` affiliations.\n",
        "- Many CJK or `ctexart` errors: use the English package with pdfLaTeX, or switch the Chinese package to XeLaTeX.\n",
        "- If the first error is buried under many follow-on messages, read `LATEX_IMPORT_TROUBLESHOOTING.md` and focus on the first fatal line in the log.\n",
        "- Question marks for citations/references after the first run: let Overleaf finish BibTeX and repeated LaTeX passes.\n",
    ]
    path.write_text("".join(lines), encoding="utf-8")


def write_latex_troubleshooting(path: Path) -> None:
    lines = [
        "# LaTeX Import Troubleshooting\n\n",
        "Use this file when Overleaf or a journal portal reports many errors immediately after import. The package has separate zips for separate platforms; most cascaded errors come from using the wrong zip or the wrong compiler.\n\n",
        "## Fast Decision\n",
        "- For Overleaf English preview/editing, import `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n",
        "- For Elsevier/Editorial Manager LaTeX source upload, use `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`.\n",
        "- Do not import `JNCA_recommended_upload_bundle.zip` as a LaTeX project; it is a mixed handoff bundle.\n",
        "- Do not import `FIGURES_FOR_UPLOAD.zip` to compile the manuscript; it is only for separate artwork upload.\n\n",
        "## Required Settings\n",
        "- English Overleaf package: main file `main.tex`, compiler pdfLaTeX, bibliography BibTeX.\n",
        "- Chinese companion package: main file `main.tex`, compiler XeLaTeX.\n",
        "- Editorial Manager flat package: keep every file at the zip root; images are referenced without a `figures/` prefix.\n\n",
        "## Error Triage\n",
        "- Judge the first fatal log line, not the number of follow-on cascade errors.\n",
        "- `main.tex not found`: the mixed handoff bundle or figure bundle was imported instead of `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n",
        "- Extra top-level folder: upload the generated zip unchanged; do not unzip and re-zip it through desktop or cloud-drive tools.\n",
        "- `ctexart` or CJK errors under pdfLaTeX: the Chinese package or bilingual archive is being compiled with the English compiler.\n",
        "- `File ... not found` for figures in a journal portal: use `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, because it is flat and avoids subfolders.\n",
        "- `elsarticle.cls not found`: the platform TeX installation lacks the Elsevier class. The official template bundle in this repository contains `elsarticle.dtx` and `elsarticle.ins`, not a pre-extracted `elsarticle.cls`; because no local TeX engine is available here, the package does not fabricate the class file.\n",
        "- `Undefined control sequence \\affiliation`: upload the regenerated English package; it uses `\\address[...]` affiliations for legacy Elsevier compatibility.\n",
        "- Citation question marks after the first compile are normal until BibTeX and repeated LaTeX passes finish.\n\n",
        "## Local Validation Boundary\n",
        "- The validator checks Word/PDF structure, source text hygiene, frontmatter order, labels, floats, graphics paths, BibTeX integrity, README/package consistency, zip-entry hygiene, and package layout.\n",
        "- The validator checks that English `elsarticle` frontmatter uses legacy-compatible `\\address[...]` affiliations and does not use structured `\\affiliation[...]` fields.\n",
        "- This machine has no local TeX engine in the checked Windows/WSL environments, so true LaTeX PDF compilation must be verified in Overleaf or another TeX installation.\n",
        "- If Overleaf still reports errors after using `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, export or copy the first 20 log lines before the first fatal error; later errors are often cascade noise.\n\n",
        "## Official-Template Note\n",
        "- The package includes `elsarticle-num.bst` from the official Elsevier template bundle and the validator checks it byte-for-byte.\n",
        "- `elsarticle.cls` is expected from Overleaf or the submission-system TeX environment. If a portal cannot provide it, the portal/template environment must be fixed or supplied through the portal's supported template mechanism.\n",
    ]
    path.write_text("".join(lines), encoding="utf-8")


def extract_section_text(doc: Document, heading: str) -> list[str]:
    capture = False
    items: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style.name.startswith("Heading"):
            if text == heading:
                capture = True
                continue
            if capture:
                break
        elif capture:
            items.append(text)
    return items


def image_size(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ModuleNotFoundError:
        return None
    with Image.open(path) as img:
        return img.size


def write_gfa_compliance_check(path: Path, en_doc_path: Path) -> None:
    doc = Document(str(en_doc_path))
    abstract_text = " ".join(extract_section_text(doc, "Abstract"))
    keywords_text = " ".join(extract_section_text(doc, "Keywords"))
    highlights = extract_section_text(doc, "Highlights")
    keywords = [item.strip() for item in keywords_text.split(";") if item.strip()]
    abstract_words = len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", abstract_text))
    highlight_lengths = [len(item) for item in highlights]
    png_size = image_size(GRAPHICAL_ABSTRACT)
    tif_size = image_size(GRAPHICAL_ABSTRACT_TIF)
    lines = [
        "# JNCA Guide-for-Authors Compliance Check\n\n",
        "This generated check maps the current submission package to common Journal of Network and Computer Applications / Elsevier author-guide requirements. It is a pre-upload audit, not a substitute for final portal-side validation.\n\n",
        "## Editable Source And Upload Files\n",
        "- Main editable Word file: `JNCA_HSTA_Encrypted_Traffic_EN.docx`.\n",
        "- PDF preview/check file: `JNCA_HSTA_Encrypted_Traffic_EN.pdf`.\n",
        "- Direct Overleaf source zip: `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` with root-level `main.tex`, pdfLaTeX, and BibTeX.\n",
        "- Flat LaTeX source zip for Editorial Manager-style upload: `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`.\n",
        "- Import-format check: `SUBMISSION_IMPORT_FORMAT_CHECK.md` records which package belongs to Overleaf, Editorial Manager, and separate artwork upload.\n",
        "- Do not import `JNCA_recommended_upload_bundle.zip` directly into Overleaf; it is a mixed handoff bundle.\n\n",
        "## Manuscript Text Checks\n",
        f"- Abstract word count: {abstract_words} words; target: not more than 250 words.\n",
        f"- Keywords: {len(keywords)} item(s); target: 1-6 keywords.\n",
        f"- Highlights: {len(highlights)} bullet(s); target: 3-5 bullets.\n",
        f"- Highlight lengths: {', '.join(str(length) for length in highlight_lengths)} characters; target: each bullet not more than 85 characters.\n",
        "- Author, affiliation, funding, repository, acknowledgements, CRediT roles, and corresponding-author details remain placeholders and must be finalized before formal submission.\n\n",
        "## Figure And Graphical Abstract Checks\n",
        "- Main manuscript figures are cited and numbered continuously as Figure 1-4.\n",
        "- Separate figure captions are available in `Figure_Captions.docx`.\n",
        "- Separate figure upload bundle is available in `FIGURES_FOR_UPLOAD.zip`.\n",
    ]
    if png_size:
        lines.append(f"- Graphical abstract PNG: `Graphical_Abstract.png`, {png_size[0]} x {png_size[1]} px.\n")
    else:
        lines.append("- Graphical abstract PNG: `Graphical_Abstract.png`, size not inspected because Pillow is unavailable.\n")
    if tif_size:
        lines.append(f"- Graphical abstract TIFF: `Graphical_Abstract.tif`, {tif_size[0]} x {tif_size[1]} px; target minimum is 1328 x 531 px.\n")
    else:
        lines.append("- Graphical abstract TIFF: `Graphical_Abstract.tif`, size not inspected because Pillow is unavailable.\n")
    lines.extend(
        [
            "\n## Required Manual Checks Before Upload\n",
            "- Replace all placeholders and confirm whether review should be anonymized.\n",
            "- Confirm the current submission portal's graphical abstract policy before uploading the optional graphical abstract.\n",
            "- Compile the English LaTeX package in Overleaf because no local TeX engine is available in this environment.\n",
            "- Recheck final figure placement and table wrapping after author metadata and any final draw.io artwork are replaced.\n",
        ]
    )
    path.write_text("".join(lines), encoding="utf-8")


def docx_plain_text(path: Path) -> str:
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def write_placeholder_replacement_check(path: Path) -> None:
    files_to_scan = [
        OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.docx",
        OUT_DIR / "Author_Statements.docx",
        OUT_DIR / "Declaration_of_Interest_Statement.docx",
        OUT_DIR / "Cover_Letter.docx",
        OUT_DIR / "submission_checklist.md",
        OUT_DIR / "submission_upload_manifest.md",
        OUT_DIR / "submission_format_audit.md",
        GFA_COMPLIANCE_CHECK,
        OUT_DIR / "overleaf_jnca" / "main.tex",
        OUT_DIR / "overleaf_jnca" / "JNCA_HSTA_Encrypted_Traffic_EN.tex",
        OUT_DIR / "editorial_manager_latex_source" / "main.tex",
        OUT_DIR / "editorial_manager_latex_source" / "JNCA_HSTA_Encrypted_Traffic_EN.tex",
    ]
    placeholder_rows: list[tuple[str, int]] = []
    scanned_texts: list[tuple[str, str]] = []
    for source in files_to_scan:
        if not source.exists():
            placeholder_rows.append((source.name, -1))
            continue
        text = docx_plain_text(source) if source.suffix.lower() == ".docx" else source.read_text(encoding="utf-8")
        count = len(re.findall(r"\bplaceholder\b|\[placeholder|占位", text, flags=re.I))
        label = str(source.relative_to(OUT_DIR)).replace("\\", "/")
        placeholder_rows.append((label, count))
        scanned_texts.append((label, text))
    token_patterns = [
        ("Author One", r"\bAuthor One\b"),
        ("Author Two", r"\bAuthor Two\b"),
        ("Author Three", r"\bAuthor Three\b"),
        ("Corresponding Author", r"\bCorresponding Author\b"),
        ("email@example.com", r"email@example\.com"),
        ("Affiliation 1", r"\bAffiliation 1\b"),
        ("Affiliation 2", r"\bAffiliation 2\b"),
        ("City", r"\bCity\b"),
        ("Country", r"\bCountry\b"),
        ("Funding information is to be completed", r"Funding information is to be completed"),
        ("To be completed", r"To be completed"),
        ("repository policy/link", r"repository (?:policy|link)|repository;|repository,|repository\]"),
        ("[placeholder]", r"\[placeholder"),
        ("placeholder", r"\bplaceholder\b"),
        ("占位", r"占位"),
    ]
    token_rows: list[tuple[str, int, list[str]]] = []
    for token, pattern in token_patterns:
        total = 0
        locations: list[str] = []
        for label, text in scanned_texts:
            count = len(re.findall(pattern, text, flags=re.I))
            if count:
                total += count
                locations.append(f"{label} ({count})")
        token_rows.append((token, total, locations))
    lines = [
        "# Final Placeholder Replacement Check\n\n",
        "Use this file immediately before formal submission. It intentionally lists remaining manual decisions; do not treat the package as a final signed submission until every applicable item below is resolved.\n\n",
        "## Required Metadata Replacement\n",
        "- Replace `Author One`, `Author Two`, `Author Three` with final author names and ordering.\n",
        "- Replace `Affiliation 1`, `Affiliation 2`, city, country, and department/lab names.\n",
        "- Replace `Corresponding Author` and `email@example.com` with the final corresponding-author details.\n",
        "- Replace or confirm funding text; if no funding exists, state that explicitly.\n",
        "- Replace or confirm acknowledgements.\n",
        "- Confirm CRediT roles for every author.\n",
        "- Confirm declaration of competing interest with all authors.\n",
        "- Confirm data/code availability wording and repository link policy.\n",
        "- Confirm cover-letter date, editor salutation, originality/no-concurrent-submission statement, and optional reviewer information.\n\n",
        "## Anonymous Review Decision\n",
        "- If the portal requires anonymized review, create an anonymized manuscript variant before upload.\n",
        "- Remove author names, affiliations, corresponding email, acknowledgements, repository links, and other identifying metadata from the anonymized variant.\n",
        "- Keep `Cover_Letter.docx` and author statements separate from any anonymized main manuscript if the portal asks for blinded review.\n\n",
        "## Scanned Source Files\n",
        "- The scan covers the English Word manuscript, declaration/support Word files, checklist/manifest/audit files, the direct Overleaf `main.tex` and `JNCA_HSTA_Encrypted_Traffic_EN.tex`, and the flat Editorial Manager `main.tex` and `JNCA_HSTA_Encrypted_Traffic_EN.tex`.\n",
        "- The scan is an inventory for manual replacement; placeholder presence is expected in this draft package and is not itself a validation failure.\n\n",
        "## Placeholder Scan\n",
    ]
    for filename, count in placeholder_rows:
        if count < 0:
            lines.append(f"- `{filename}`: missing during scan.\n")
        else:
            lines.append(f"- `{filename}`: {count} placeholder marker(s) detected.\n")
    lines.append("\n## Token Inventory\n")
    for token, total, locations in token_rows:
        location_text = "; ".join(locations) if locations else "not detected"
        lines.append(f"- `{token}`: {total} occurrence(s); {location_text}.\n")
    lines.extend(
        [
            "\n## LaTeX Source Placeholder Handling\n",
            "- Replace author, affiliation, corresponding-email, funding, acknowledgement, and data/code availability placeholders in both Word and LaTeX source files before final submission.\n",
            "- After replacing LaTeX placeholders, rebuild the Overleaf and Editorial Manager zips instead of editing only the zip contents by hand.\n",
            "- If preparing an anonymized review version, create a separate anonymized Word/LaTeX package and keep the signed author statements and cover letter outside the blinded manuscript upload.\n",
        ]
    )
    lines.extend(
        [
            "\n## Final Upload Choice\n",
            "- For Word/PDF submission: upload `JNCA_HSTA_Encrypted_Traffic_EN.docx` and use `JNCA_HSTA_Encrypted_Traffic_EN.pdf` as the checked preview.\n",
            "- For Overleaf preview/editing: import `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, set `main.tex`, and use pdfLaTeX + BibTeX.\n",
            "- For Editorial Manager LaTeX source upload: use `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` if subfolders are rejected.\n",
            "- Do not upload `JNCA_recommended_upload_bundle.zip` as a direct Overleaf project.\n",
        ]
    )
    path.write_text("".join(lines), encoding="utf-8")


def export_pdf(docx_path: Path, pdf_path: Path) -> tuple[bool, str]:
    ps = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open('{docx_path}')
$doc.ExportAsFixedFormat('{pdf_path}', 17)
$doc.Close($false)
$word.Quit()
"""
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], capture_output=True, text=True)
    if result.returncode == 0 and pdf_path.exists():
        return True, "PDF exported through Microsoft Word COM."
    return False, (result.stderr or result.stdout or "Unknown Word COM export failure").strip()


def write_checklist(path: Path, pdf_ok: bool, pdf_message: str, figures: dict[str, Path]) -> None:
    pdf_path = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.pdf"
    pdf_magic_ok = pdf_path.exists() and pdf_path.read_bytes()[:5] == b"%PDF-"
    checks = []
    rows40, rows60 = build_main_result_tables()
    checks.append("# JNCA Submission Checklist\n")
    checks.append("## Generated artifacts\n")
    checks.append("- `JNCA_HSTA_Encrypted_Traffic_CN.docx`\n")
    checks.append("- `JNCA_HSTA_Encrypted_Traffic_EN.docx`\n")
    checks.append(f"- `JNCA_HSTA_Encrypted_Traffic_EN.pdf`: {'generated' if pdf_ok else 'not generated'} ({pdf_message}; PDF header check: {'ok' if pdf_magic_ok else 'failed'}; validator also checks EOF marker, page objects, content streams, font/image resources, decodable streams, obvious raw metadata/tool markers, and PDF/Word timestamp sync.)\n")
    checks.append("- `Highlights.docx`: generated as a separate Elsevier-style highlights file; each bullet is under 85 characters.\n")
    checks.append("- `Author_Statements.docx`: generated as a separate submission-support file for CRediT roles, funding, competing interests, data/code availability, and acknowledgements.\n")
    checks.append("- `Declaration_of_Interest_Statement.docx`: generated as a separate no-competing-interest statement placeholder for submission systems that request it as an individual file.\n")
    checks.append("- `Cover_Letter.docx`: generated as a draft cover letter with submission, originality, fit, and conflict-of-interest placeholders.\n")
    checks.append("- `Figure_Captions.docx`: generated as a separate figure-caption file for journal upload systems that request captions independently.\n")
    checks.append("- `Graphical_Abstract.png` and `Graphical_Abstract.tif`: generated as graphical-abstract candidates; TIFF is included for Elsevier-preferred artwork upload.\n")
    checks.append("- `FIGURES_FOR_UPLOAD.zip`: generated as a separate figure-upload bundle containing Figure 1-4 PNGs, graphical abstract, and captions.\n")
    checks.append("- `submission_upload_manifest.md`: generated as an upload-oriented file map and final manual-check list.\n")
    checks.append("- `submission_format_audit.md`: generated as a Word/PDF/Overleaf format audit for final package inspection.\n")
    checks.append("- `JNCA_GFA_COMPLIANCE_CHECK.md`: generated as a Guide-for-Authors compliance audit covering source files, abstract length, keywords, Highlights, graphical abstract size, and manual checks.\n")
    checks.append("- `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: generated as the final metadata, anonymity, and placeholder replacement checklist before upload.\n")
    checks.append("- `SUBMISSION_IMPORT_FORMAT_CHECK.md`: generated as the Overleaf/Editorial Manager import-format checklist.\n")
    checks.append("- `LATEX_IMPORT_TROUBLESHOOTING.md`: generated as a first-response guide for cascaded Overleaf or journal-portal LaTeX errors.\n")
    checks.append("- `OVERLEAF_IMPORT_GUIDE.md`: generated as a short guide that separates the direct Overleaf source zip from the handoff bundle.\n")
    checks.append("- `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`: generated as the direct English Overleaf import zip inside the submission folder.\n")
    checks.append("- `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`: generated as a flat LaTeX source zip for Elsevier/Editorial Manager-style source upload.\n")
    checks.append("- `JNCA_recommended_upload_bundle.zip`: generated as the recommended upload bundle containing the main manuscript, PDF, Highlights, author statements, declaration of interest, cover letter, upload/checklist/audit notes, and English Overleaf source zip.\n")
    checks.append("\n## Journal fit\n")
    checks.append("- Target journal: Journal of Network and Computer Applications, ISSN 1084-8045.\n")
    checks.append("- Scope fit: the Elsevier journal page exposes scope terms including computer networks, network protocols, and security; encrypted QUIC/TLS traffic classification is positioned under these topics.\n")
    checks.append("- Article type assumed: full research article.\n")
    checks.append("\n## Text and structure checks\n")
    checks.append("- Rebuilt the manuscript around the QUIC/TLS problem, lightweight packet-level side-channel input, HSTA Block, ablation, efficiency, transfer, and error analysis.\n")
    checks.append("- Strengthened the English manuscript as a full SCI-style research article rather than a compact submission skeleton.\n")
    checks.append("- Added Highlights, Declarations, CRediT-style author contributions placeholder, Funding placeholder, Conflict-of-interest statement placeholder, Data/code availability, References, and appendices.\n")
    checks.append("- Highlights use four concise English bullets and stay within the usual Elsevier 85-character limit.\n")
    checks.append("- English LaTeX sources use the Elsevier `highlights` environment instead of placing Highlights as a body section.\n")
    checks.append("- English LaTeX sources load `lineno` before `hyperref` to keep a conservative Elsevier/Overleaf package order.\n")
    checks.append("- English LaTeX sources are checked for Elsevier frontmatter order: title, abstract, Highlights, and keywords stay inside `frontmatter`, followed by `\\linenumbers` and the first section.\n")
    checks.append("- English LaTeX author affiliations use legacy-compatible `\\address[...]` markers instead of newer structured `\\affiliation[...]` fields to reduce old Elsevier-class import errors.\n")
    checks.append("- English LaTeX and BibTeX source files are checked for UTF-8/ASCII-safe source text hygiene, including no BOM, no NUL bytes, and no mixed newline styles.\n")
    checks.append("- English LaTeX labels are checked for uniqueness, portable names, and standard `fig:`/`tab:` prefixes.\n")
    checks.append("- English LaTeX table and figure floats are checked for nonempty captions, one label per float, labels after captions, and expected table/figure bodies.\n")
    checks.append("- Abstract length and keyword count are checked against common JNCA/Elsevier requirements in `JNCA_GFA_COMPLIANCE_CHECK.md` and by `scripts/validate_jnca_submission.py`.\n")
    checks.append("- English keywords are capped at 6 items in both Word and LaTeX outputs.\n")
    checks.append("- English Word and LaTeX outputs are cross-checked for aligned title, keywords, Highlights, abstract result markers, and main section titles.\n")
    checks.append("- Removed duplicated method paragraphs found in the source draft and rewrote the English manuscript in SCI style rather than literal translation.\n")
    checks.append("- English narrative was refined against representative encrypted-traffic papers so the manuscript foregrounds validity pressure, controlled inputs, mechanism evidence, and conservative claim boundaries.\n")
    checks.append("- Formula-sensitive text in Section 3 was rewritten as inline mathematical notation to avoid empty formula-object extraction artifacts.\n")
    checks.append("- Word/PDF manuscripts include in-text numerical citation markers for protocol standards, datasets, related work, LoRA adaptation, and drift/generalization limitations.\n")
    checks.append("- BibTeX entries are validated for unique keys, required fields, valid four-digit years, no placeholder-like text, and synchronized `references.bib` copies across LaTeX folders and zips.\n")
    checks.append("- Elsevier template dependency is audited: packaged `elsarticle-num.bst` must match the official template copy, while `elsarticle.cls` is expected from the Overleaf or submission-system TeX environment.\n")
    checks.append("- English Word review format is generated with 12 pt Times New Roman Normal style, double spacing, continuous line numbering, footer page-number fields, repeated table header rows, and non-splitting table rows.\n")
    checks.append("- English Word structure hygiene is checked for the expected title, heading sequence, continuous table captions, no duplicate table captions, no CJK characters, no editable figure placeholder text, and no repeated plain spaces.\n")
    checks.append("- Appendices start on a new Word/PDF page after the reference list so appendix headings and mapping tables are not stranded at the bottom of the final reference page.\n")
    checks.append("- Word core document properties are set to controlled placeholder metadata instead of default generator metadata.\n")
    checks.append("- Author, affiliation, funding, acknowledgements, CRediT roles, and corresponding-author fields remain placeholders and must be replaced or confirmed before submission; see `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`.\n")
    checks.append("\n## Data consistency checks\n")
    checks.append(f"- 40-class table rows: {len(rows40)-1}; 60-class table rows: {len(rows60)-1}.\n")
    checks.append("- Main, adapted SOTA, ablation, transfer, depth, and efficiency tables were recomputed from CSV files under `results/`.\n")
    checks.append("- Dataset statistics, adapted-baseline descriptions, confusion pairs, and appendix label maps were extracted from the source Word file.\n")
    checks.append("\n## Figure status\n")
    if DRAWIO.exists():
        checks.append(f"- Editable figure source exists: `{DRAWIO.relative_to(ROOT)}`.\n")
    for key, fig_path in figures.items():
        status = "generated" if fig_path.exists() else "missing"
        checks.append(f"- `{fig_path.relative_to(ROOT)}`: {status} ({key}).\n")
    checks.append("- Figure 1 HSTA architecture overview is generated as `fig1_hsta_architecture.png` and embedded in the Word/LaTeX manuscripts for stable preview.\n")
    checks.append("- Result figures are generated automatically from existing CSV summaries and embedded in the Word manuscript with continuous Figure 1-4 numbering.\n")
    checks.append("- Separate figure-upload material is available through `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, including PNG and TIFF graphical abstract candidates.\n")
    checks.append("- Figure artwork validation checks PNG/TIFF headers, minimum pixel dimensions, graphical-abstract PNG/TIFF dimension alignment, and byte-for-byte synchronization between generated artwork files and `FIGURES_FOR_UPLOAD.zip` entries.\n")
    checks.append("- The HSTA architecture figure can still be replaced with polished draw.io artwork before final journal upload.\n")
    checks.append("- Recommended direct Overleaf upload inside the submission folder: `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n")
    checks.append("- Recommended flat LaTeX source upload for Editorial Manager-style systems: `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`.\n")
    checks.append("- Equivalent source package: `paper/jnca_english_overleaf_package.zip`; fallback package: `paper/submission_jnca/overleaf_jnca_package.zip`.\n")
    checks.append("- Recommended one-file handoff bundle: `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`; do not import this full handoff bundle directly into Overleaf.\n")
    checks.append("- Overleaf package should contain root-level `main.tex`, `latexmkrc`, `references.bib`, `elsarticle-num.bst`, `README.md`, and generated figures under `figures/`.\n")
    checks.append("- Editorial Manager flat source package should contain root-level `main.tex`, `references.bib`, `elsarticle-num.bst`, `latexmkrc`, README, and all referenced PNG figures without subdirectories.\n")
    checks.append("- Source, figure, and handoff zips are validated for clean ASCII relative entry paths without hidden/system files, absolute paths, backslash separators, path traversal entries, or template dependency drift.\n")
    checks.append("- `SUBMISSION_IMPORT_FORMAT_CHECK.md` records common wrong-package import symptoms and the expected package for each platform.\n")
    checks.append("- `LATEX_IMPORT_TROUBLESHOOTING.md` maps common first LaTeX errors to package, compiler, class-file, and figure-path fixes.\n")
    checks.append("- If the Overleaf package is used, set main file to `main.tex` and compile with pdfLaTeX + BibTeX after replacing final author placeholders.\n")
    checks.append("- If importing the Chinese companion package, use `paper/jnca_chinese_xelatex_package.zip` and switch Overleaf to XeLaTeX; pdfLaTeX will produce many CJK/ctex errors.\n")
    checks.append("- Run `scripts/validate_jnca_submission.py` after regeneration to check PDF header/EOF/page objects/content streams/font-image resources/raw metadata markers/timestamp sync, Word table/image counts, English Word review format, English Word structure hygiene, English Word result-table contents against generated CSV-derived tables, abstract/keyword/Highlights limits, Word/LaTeX title-keyword-highlight-section alignment, BibTeX integrity, LaTeX package order, Elsevier frontmatter order, table/figure caption-label hygiene, source text hygiene, Elsevier template dependency, LaTeX label hygiene, README/package consistency, graphical abstract files, figure artwork dimensions and upload-zip synchronization, declaration files, declaration of interest, format audit, compliance audit, LaTeX references/figures, upload bundle, zip contents, and zip-entry hygiene.\n")
    checks.append("\n## Remaining author-side actions\n")
    checks.append("- Replace all placeholders for authors, affiliations, emails, funding, acknowledgements, repository links, and author contributions.\n")
    checks.append("- Replace cover-letter placeholders and confirm originality/no-concurrent-submission wording before upload.\n")
    checks.append("- Confirm the CRediT author roles and competing-interest statement with all authors before upload.\n")
    checks.append("- Confirm whether the journal submission system requires anonymized manuscript files; if yes, remove identifiable author metadata from the main manuscript.\n")
    checks.append("- Run a final human review of formulas and exported figures after replacing placeholders.\n")
    path.write_text("".join(checks), encoding="utf-8")


def write_format_audit(path: Path, pdf_ok: bool, pdf_message: str, figures: dict[str, Path]) -> None:
    en_doc = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.docx"
    cn_doc = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_CN.docx"
    pdf_path = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.pdf"
    pdf_magic_ok = pdf_path.exists() and pdf_path.read_bytes()[:5] == b"%PDF-"
    lines = [
        "# JNCA Format Audit\n\n",
        "This audit is generated from the current submission package. It is intended to catch common Word, PDF, and Overleaf upload mistakes before formal submission.\n\n",
        "## Word/PDF Structure\n",
    ]
    for label, doc_path in [("English manuscript", en_doc), ("Chinese companion", cn_doc)]:
        if doc_path.exists():
            doc = Document(str(doc_path))
            section = doc.sections[0]
            margins = ", ".join(
                f"{name}={value.cm:.2f} cm"
                for name, value in [
                    ("top", section.top_margin),
                    ("bottom", section.bottom_margin),
                    ("left", section.left_margin),
                    ("right", section.right_margin),
                ]
            )
            headings = [p.text.strip() for p in doc.paragraphs if p.style.name.startswith("Heading") and p.text.strip()]
            lines.append(f"- {label}: {len(doc.tables)} tables, {len(doc.inline_shapes)} embedded figures, margins {margins}.\n")
            if label == "English manuscript":
                normal = doc.styles["Normal"]
                size = normal.font.size.pt if normal.font.size is not None else None
                size_label = f"{size:g}" if size is not None else "unset"
                with ZipFile(doc_path) as zf:
                    body_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
                    footer_xml = "\n".join(
                        zf.read(name).decode("utf-8", errors="ignore")
                        for name in zf.namelist()
                        if name.startswith("word/footer") and name.endswith(".xml")
                    )
                line_numbering = "continuous line numbering" if 'w:lnNumType' in body_xml and 'w:restart="continuous"' in body_xml else "line numbering not detected"
                page_number = "page-number field" if "PAGE" in footer_xml and "fldCharType" in footer_xml else "page-number field not detected"
                spacing = "double spacing" if normal.paragraph_format.line_spacing_rule == WD_LINE_SPACING.DOUBLE else "line spacing not detected as double"
                lines.append(f"- {label} review format: Times New Roman, {size_label} pt Normal style, {spacing}, {line_numbering}, {page_number}.\n")
            lines.append(f"- {label} headings: {'; '.join(headings[:16])}.\n")
        else:
            lines.append(f"- {label}: missing.\n")
    lines.extend(
        [
            f"- English PDF export: {'generated' if pdf_ok else 'not generated'} ({pdf_message}; PDF header check: {'ok' if pdf_magic_ok else 'failed'}).\n",
            "- English PDF validation includes header, EOF marker, page-object count, content streams, font/image resources, decodable streams, obvious raw metadata/tool markers, and PDF/Word timestamp sync.\n",
            "- Word manuscripts include in-text numerical citation markers matching the generated reference list.\n",
            "- Word tables are generated with repeated header rows and non-splitting rows so result labels are not split across page breaks.\n",
            "- Word/PDF appendices start on a new page after the reference list to avoid stranded appendix headings or mapping tables.\n",
            "- Word core document properties use controlled placeholder metadata rather than default generator metadata.\n",
            "\n## Separate Submission Files\n",
            "- Highlights: `Highlights.docx`; four bullets, each under 85 characters.\n",
            "- English LaTeX source: four Highlights are placed in the Elsevier `highlights` environment before keywords, not as a numbered or unnumbered body section.\n",
            "- English LaTeX package order: `lineno` is loaded before `hyperref` for conservative Overleaf/Elsevier compatibility.\n",
            "- English LaTeX frontmatter order: title, abstract, Highlights, and keywords remain inside `frontmatter`, followed by `\\linenumbers` and the first section.\n",
            "- English LaTeX affiliation format: author affiliations use legacy-compatible `\\address[...]` markers, not newer structured `\\affiliation[...]` fields.\n",
            "- English source text hygiene: LaTeX and BibTeX sources are checked for UTF-8 decoding, no BOM, no NUL bytes, no mixed newline styles, and ASCII-safe English source text.\n",
            "- English LaTeX label hygiene: labels are checked for uniqueness, portable names, and standard `fig:`/`tab:` prefixes.\n",
            "- English LaTeX table/figure hygiene: floats are checked for captions, labels, label-after-caption order, figure images, and table bodies.\n",
            "- English Word structure hygiene: title, heading sequence, table-caption sequence, duplicate table captions, CJK characters, editable figure placeholders, and repeated plain spaces are checked by the validator.\n",
            "- Word/LaTeX consistency: title, keywords, Highlights, abstract result markers, and main section titles are cross-checked by the validator.\n",
            "- BibTeX integrity: reference keys, required fields, years, placeholder-like text, and synchronized `references.bib` copies are cross-checked by the validator.\n",
            "- Elsevier template dependency: packaged `elsarticle-num.bst` is checked against the official template copy, and `elsarticle.cls` is treated as a platform TeX dependency.\n",
            "- Author statements: `Author_Statements.docx`; includes CRediT, funding, competing interest, data/code availability, and acknowledgements placeholders.\n",
            "- Declaration of interest: `Declaration_of_Interest_Statement.docx`; separate no-competing-interest statement placeholder for Elsevier-style upload systems.\n",
            "- Cover letter: `Cover_Letter.docx`; includes journal fit and originality/no-concurrent-submission placeholders.\n",
            "- Figure captions: `Figure_Captions.docx`; separate captions for Figure 1-4 and the graphical abstract.\n",
            "- Graphical abstract: `Graphical_Abstract.png` and `Graphical_Abstract.tif`; optional Elsevier-style graphical abstract candidates.\n",
            "- Figure upload bundle: `FIGURES_FOR_UPLOAD.zip`; independent figure PNGs plus captions for upload systems that request separate artwork files.\n",
            "- Figure artwork integrity: manuscript PNG figures, graphical abstract PNG/TIFF files, and `FIGURES_FOR_UPLOAD.zip` entries are checked for headers, minimum dimensions, graphical abstract dimension alignment, and byte-for-byte synchronization.\n",
            "- Guide-for-Authors compliance audit: `JNCA_GFA_COMPLIANCE_CHECK.md`; records abstract length, keyword count, Highlights length, graphical abstract size, and upload-package guidance.\n",
            "- Final placeholder replacement check: `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`; lists metadata, anonymity, and placeholder decisions before upload.\n",
            "- Submission import-format check: `SUBMISSION_IMPORT_FORMAT_CHECK.md`; separates Overleaf, Editorial Manager, handoff, and artwork-upload package use.\n",
            "- LaTeX import troubleshooting: `LATEX_IMPORT_TROUBLESHOOTING.md`; maps common immediate compile errors to package, compiler, class-file, and figure-path fixes.\n",
            "- Direct Overleaf import guide: `OVERLEAF_IMPORT_GUIDE.md`; explains which zip should and should not be imported into Overleaf.\n",
            "\n## Figure And Source Package Checks\n",
        ]
    )
    for key, fig_path in figures.items():
        lines.append(f"- {key}: `{fig_path.relative_to(ROOT)}` {'exists' if fig_path.exists() else 'missing'}.\n")
    lines.extend(
        [
            "- Recommended direct English Overleaf source: `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.\n",
            "- Recommended flat Editorial Manager source: `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`.\n",
            "- Equivalent English Overleaf source: `paper/jnca_english_overleaf_package.zip`.\n",
            "- Recommended one-file handoff bundle: `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`.\n",
            "- The handoff bundle is not a direct Overleaf project zip because it contains Word/PDF/support files plus a nested source zip.\n",
            "- English Overleaf settings: `main.tex`, pdfLaTeX, BibTeX.\n",
            "- English LaTeX package order: `lineno` is loaded before `hyperref` to reduce line-numbering and hyperlink conflicts.\n",
            "- English LaTeX author-affiliation format uses legacy-compatible `\\address[...]` markers for old/new Elsevier class compatibility.\n",
            "- English source text hygiene: zipped `main.tex` and `references.bib` are validated for ASCII/UTF-8 safety before upload.\n",
            "- English source-package README consistency: each source zip is checked so its README matches the actual root files, compiler, figure layout, and package-use warnings.\n",
            "- Elsevier template dependency: packaged `elsarticle-num.bst` is verified against the official template copy; `elsarticle.cls` must be provided by Overleaf or the submission-system TeX environment.\n",
            "- Editorial Manager source settings: flat root-level `main.tex`, pdfLaTeX, BibTeX; figures are referenced without subfolders.\n",
            "- Source, figure, and handoff zips are generated and validated with clean ASCII relative entry paths; hidden/system files, absolute paths, backslash separators, and path traversal entries are treated as import-format failures.\n",
            "- Chinese companion settings: `main.tex` in `paper/jnca_chinese_xelatex_package.zip`, XeLaTeX.\n",
            "- Common import-error triage is recorded in `SUBMISSION_IMPORT_FORMAT_CHECK.md`, `LATEX_IMPORT_TROUBLESHOOTING.md`, and `OVERLEAF_IMPORT_GUIDE.md`.\n",
            "\n## Remaining Manual Formatting Checks\n",
            "- Replace all author, affiliation, email, funding, acknowledgement, repository, and contribution placeholders.\n",
            "- Confirm whether the journal requires anonymized review files; if yes, prepare a separate anonymized manuscript and cover-letter variant.\n",
            "- Compile the English LaTeX package in Overleaf because no local TeX engine is available in the current environment.\n",
            "- Recheck table wrapping, figure placement, and references after metadata replacement and any final draw.io figure export.\n",
            "- Confirm whether JNCA requires or permits a graphical abstract in the current submission system before uploading `Graphical_Abstract.png` or `Graphical_Abstract.tif`.\n",
        ]
    )
    path.write_text("".join(lines), encoding="utf-8")


def write_upload_manifest(path: Path) -> None:
    lines = [
        "# JNCA Upload Manifest\n\n",
        "Use this file as a practical upload map for the current generated submission package.\n\n",
        "## Recommended Upload Files\n",
        "- Main manuscript: `JNCA_HSTA_Encrypted_Traffic_EN.docx`\n",
        "- PDF preview/check file: `JNCA_HSTA_Encrypted_Traffic_EN.pdf`\n",
        "- Highlights: `Highlights.docx`\n",
        "- Author statements: `Author_Statements.docx`\n",
        "- Declaration of interest statement: `Declaration_of_Interest_Statement.docx`\n",
        "- Cover letter draft: `Cover_Letter.docx`\n",
        "- Figure captions: `Figure_Captions.docx`\n",
        "- Figure upload bundle: `FIGURES_FOR_UPLOAD.zip`\n",
        "- Optional graphical abstract candidates: `Graphical_Abstract.png`, `Graphical_Abstract.tif`\n",
        "- Guide-for-Authors compliance audit: `JNCA_GFA_COMPLIANCE_CHECK.md`\n",
        "- Final placeholder replacement check: `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`\n",
        "- Import-format check: `SUBMISSION_IMPORT_FORMAT_CHECK.md`\n",
        "- LaTeX import troubleshooting guide: `LATEX_IMPORT_TROUBLESHOOTING.md`\n",
        "- Overleaf/LaTeX source package: `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`\n",
        "- Flat LaTeX source package for Editorial Manager-style upload: `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`\n",
        "- Equivalent source package outside this folder: `../jnca_english_overleaf_package.zip`\n",
        "- One-file handoff bundle: `JNCA_recommended_upload_bundle.zip`\n\n",
        "## Optional / Internal Support Files\n",
        "- Chinese companion manuscript: `JNCA_HSTA_Encrypted_Traffic_CN.docx`\n",
        "- Fallback English Overleaf package: `overleaf_jnca_package.zip`\n",
        "- Bilingual LaTeX archive: `../jnca_bilingual_latex_package.zip`\n",
        "- Chinese XeLaTeX checking package: `../jnca_chinese_xelatex_package.zip`\n",
        "- Submission checklist: `submission_checklist.md`\n",
        "- Format audit: `submission_format_audit.md`\n\n",
        "## Final Manual Checks Before Upload\n",
        "- Replace author names, affiliations, email, funding, acknowledgements, and repository placeholders.\n",
        "- Confirm CRediT roles and competing-interest wording with all authors.\n",
        "- Confirm whether the submission should be anonymized; if yes, remove identifying metadata from the manuscript and cover letter.\n",
        "- Replace Figure 1 with polished draw.io artwork if final journal artwork is required.\n",
        "- Confirm whether the submission portal asks for a graphical abstract; upload `Graphical_Abstract.tif` or `Graphical_Abstract.png` only if requested or allowed.\n",
        "- Compile `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` with `main.tex`, pdfLaTeX, and BibTeX if LaTeX source upload is required.\n",
        "- Use `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` instead if the submission system rejects figure subfolders or mixed Overleaf project files.\n",
        "- Read `SUBMISSION_IMPORT_FORMAT_CHECK.md` before importing any zip; it maps each package to the correct platform.\n",
        "- Read `LATEX_IMPORT_TROUBLESHOOTING.md` if Overleaf or the journal portal reports many immediate LaTeX errors.\n",
        "- Keep generated zip files intact; re-zipping through cloud drives or archive tools can add hidden/system files or nested folders that cause import errors.\n",
        "- Do not import `JNCA_recommended_upload_bundle.zip` directly into Overleaf; it is a handoff bundle with a nested source zip.\n",
        "- If many Overleaf errors appear immediately, confirm you uploaded `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, selected `main.tex`, and used pdfLaTeX rather than the Chinese XeLaTeX package.\n",
        "- Do not manually edit numerical table values; regenerate from scripts if result CSV files change.\n",
    ]
    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    figures = generate_result_figures()
    build_graphical_abstract(get_pyplot(), figures)
    cn = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_CN.docx"
    en = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.docx"
    highlights = OUT_DIR / "Highlights.docx"
    statements = OUT_DIR / "Author_Statements.docx"
    declaration_interest = OUT_DIR / "Declaration_of_Interest_Statement.docx"
    cover_letter = OUT_DIR / "Cover_Letter.docx"
    upload_manifest = OUT_DIR / "submission_upload_manifest.md"
    format_audit = OUT_DIR / "submission_format_audit.md"
    overleaf_import_guide = OVERLEAF_IMPORT_GUIDE
    legacy_highlights = OUT_DIR / "JNCA_Highlights.docx"
    pdf = OUT_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.pdf"
    checklist = OUT_DIR / "submission_checklist.md"
    upload_bundle = UPLOAD_BUNDLE
    build_doc("cn", cn, figures)
    build_doc("en", en, figures)
    build_highlights_doc(highlights)
    build_author_statements_doc(statements)
    build_declaration_of_interest_doc(declaration_interest)
    build_cover_letter_doc(cover_letter)
    write_figure_captions_doc(FIGURE_CAPTIONS_DOCX)
    write_figure_upload_zip(figures)
    if legacy_highlights.exists():
        legacy_highlights.unlink()
    pdf_ok, pdf_message = export_pdf(en.resolve(), pdf.resolve())
    if not ENGLISH_OVERLEAF_ZIP.exists():
        raise FileNotFoundError(f"Cannot create direct Overleaf import zip; missing {ENGLISH_OVERLEAF_ZIP.relative_to(ROOT)}")
    shutil.copy2(ENGLISH_OVERLEAF_ZIP, OVERLEAF_DIRECT_ZIP)
    write_overleaf_import_guide(overleaf_import_guide)
    write_checklist(checklist, pdf_ok, pdf_message, figures)
    write_format_audit(format_audit, pdf_ok, pdf_message, figures)
    write_upload_manifest(upload_manifest)
    write_gfa_compliance_check(GFA_COMPLIANCE_CHECK, en)
    write_placeholder_replacement_check(PLACEHOLDER_REPLACEMENT_CHECK)
    write_import_format_check(IMPORT_FORMAT_CHECK)
    write_latex_troubleshooting(LATEX_TROUBLESHOOTING)
    write_upload_bundle(upload_bundle)
    print(f"CN: {cn}")
    print(f"EN: {en}")
    print(f"Highlights: {highlights}")
    print(f"Author statements: {statements}")
    print(f"Declaration of interest: {declaration_interest}")
    print(f"Cover letter: {cover_letter}")
    print(f"PDF: {pdf} ({'ok' if pdf_ok else 'failed'})")
    print(f"Checklist: {checklist}")
    print(f"Upload manifest: {upload_manifest}")
    print(f"Format audit: {format_audit}")
    print(f"GFA compliance: {GFA_COMPLIANCE_CHECK}")
    print(f"Placeholder check: {PLACEHOLDER_REPLACEMENT_CHECK}")
    print(f"Import format check: {IMPORT_FORMAT_CHECK}")
    print(f"LaTeX troubleshooting: {LATEX_TROUBLESHOOTING}")
    print(f"Overleaf import guide: {overleaf_import_guide}")
    print(f"Direct Overleaf zip: {OVERLEAF_DIRECT_ZIP}")
    print(f"Upload bundle: {upload_bundle}")


if __name__ == "__main__":
    main()
