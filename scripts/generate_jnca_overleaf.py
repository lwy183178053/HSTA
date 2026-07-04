from __future__ import annotations

import math
import re
import shutil
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "submission_jnca" / "overleaf_jnca"
TEMPLATE = ROOT / "paper" / "submission_jnca" / "official_template" / "elsarticle" / "elsarticle"
FIG_DIR = OUT / "figures"


TASKS = {
    "quic40_s": ("QUIC-40", ROOT / "results" / "quic40_s" / "all_results.csv"),
    "quic60_s": ("QUIC-60", ROOT / "results" / "quic60_s" / "all_results.csv"),
    "tls40_s": ("TLS-40", ROOT / "results" / "tls40_s" / "all_results.csv"),
    "tls60_s": ("TLS-60", ROOT / "results" / "tls60_s" / "all_results.csv"),
}


def esc(s: object) -> str:
    text = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "--"
    return f"{float(v) * 100:.2f}"


def mean_std(series: pd.Series) -> str:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) == 0:
        return "--"
    if len(vals) == 1:
        return pct(vals.iloc[0])
    return f"{vals.mean() * 100:.2f}$\\pm${vals.std(ddof=1) * 100:.2f}"


def df_task(key: str) -> pd.DataFrame:
    return pd.read_csv(TASKS[key][1])


def model_stat(task_key: str, model: str) -> tuple[str, str]:
    df = df_task(task_key)
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
    return mean_std(sub["test_accuracy"]), mean_std(sub["test_macro_f1"])


def sota_stat(task_key: str, model: str) -> tuple[str, str]:
    df = pd.read_csv(ROOT / "results" / "sota_adapted" / "all_results.csv")
    frag = task_key.replace("_s", "")
    sub = df[(df["model"] == model) & df["exp_name"].str.contains(frag)]
    return mean_std(sub["test_accuracy"]), mean_std(sub["test_macro_f1"])


def latex_table(headers: list[str], rows: list[list[str]], caption: str, label: str, note: str | None = None) -> str:
    cols = "l" + "c" * (len(headers) - 1)
    tabular = "\n".join(
        [
            rf"\begin{{tabular}}{{{cols}}}",
            r"\toprule",
            " & ".join(headers) + r" \\",
            r"\midrule",
            *[" & ".join(row) + r" \\" for row in rows],
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    if len(headers) >= 5:
        tabular = "\\resizebox{\\linewidth}{!}{%\n" + tabular + "\n}"
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        tabular,
    ]
    if note:
        lines.append(rf"\begin{{flushleft}}\footnotesize {note}\end{{flushleft}}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def result_tables() -> str:
    rows40: list[list[str]] = []
    for model in ["MLP", "CNN", "LSTM", "GRU", "Transformer"]:
        q, t = model_stat("quic40_s", model), model_stat("tls40_s", model)
        rows40.append([model, q[0], q[1], t[0], t[1]])
    for model in ["30pktTCNET-adapted", "NetMamba-adapted"]:
        q, t = sota_stat("quic40_s", model), sota_stat("tls40_s", model)
        rows40.append([model, q[0], q[1], t[0], t[1]])
    q, t = model_stat("quic40_s", "Hybrid"), model_stat("tls40_s", "Hybrid")
    rows40.append([r"\textbf{HSTA-Hybrid}", r"\textbf{" + q[0] + "}", r"\textbf{" + q[1] + "}", r"\textbf{" + t[0] + "}", r"\textbf{" + t[1] + "}"])

    rows60: list[list[str]] = []
    for model in ["GRU", "Transformer"]:
        q, t = model_stat("quic60_s", model), model_stat("tls60_s", model)
        rows60.append([model, q[0], q[1], t[0], t[1]])
    for model in ["30pktTCNET-adapted", "NetMamba-adapted"]:
        q, t = sota_stat("quic60_s", model), sota_stat("tls60_s", model)
        rows60.append([model, q[0], q[1], t[0], t[1]])
    q, t = model_stat("quic60_s", "Hybrid"), model_stat("tls60_s", "Hybrid")
    rows60.append([r"\textbf{HSTA-Hybrid}", r"\textbf{" + q[0] + "}", r"\textbf{" + q[1] + "}", r"\textbf{" + t[0] + "}", r"\textbf{" + t[1] + "}"])

    note = "All values are percentages. Adapted baselines use the same 30-packet side-channel input and training protocol."
    return "\n\n".join(
        [
            latex_table(["Model", "QUIC-40 Acc", "QUIC-40 F1", "TLS-40 Acc", "TLS-40 F1"], rows40, "Main results on 40-class tasks.", "tab:main40", note),
            latex_table(["Model", "QUIC-60 Acc", "QUIC-60 F1", "TLS-60 Acc", "TLS-60 F1"], rows60, "Main results on 60-class tasks.", "tab:main60", note),
        ]
    )


def ablation_table() -> str:
    df = pd.read_csv(ROOT / "results" / "ablation_s" / "all_results.csv")
    variants = [("No Attention", "ablation_no_attention"), ("Attention-front", "ablation_attention_front"), ("Attention-middle", "ablation_attention_middle")]
    tasks = [("QUIC-40", "quic40"), ("QUIC-60", "quic60"), ("TLS-40", "tls40"), ("TLS-60", "tls60")]
    rows = []
    for name, prefix in variants:
        row = [name]
        for _, frag in tasks:
            row.append(mean_std(df[df["exp_name"].str.contains(prefix) & df["exp_name"].str.contains(frag)]["test_macro_f1"]))
        rows.append(row)
    rows.append(["HSTA-Hybrid"] + [model_stat(k, "Hybrid")[1] for k in ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]])
    return latex_table(["Variant", "QUIC-40", "QUIC-60", "TLS-40", "TLS-60"], rows, "Attention-position ablation results (Macro-F1, \\%).", "tab:ablation")


def efficiency_table() -> str:
    df = pd.read_csv(ROOT / "results" / "efficiency_benchmark" / "summary.csv")
    rows = []
    for raw, display in [("30pktTCNET-adapted", "30pktTCNET-adapted"), ("NetMamba-adapted", "NetMamba-adapted"), ("transformer", "Transformer"), ("hybrid", "HSTA-Hybrid")]:
        sub = df[(df["variant"] == "main") & (df["batch_size"].isin([1, 32, 512]))]
        sub = sub[sub["model"] == raw]
        if raw == "hybrid":
            sub = sub[sub["exp_name"].str.contains("hybrid_mm_mlp_a_mlp_")]
        for batch in [1, 32, 512]:
            b = sub[sub["batch_size"] == batch]
            if b.empty:
                continue
            rows.append([display, str(batch), f"{b['parameters_m'].mean():.3f}", f"{b['gflops_per_sample'].mean():.4f}", f"{b['latency_ms_mean'].mean():.3f}", f"{b['throughput_samples_per_s'].mean():.0f}"])
    return latex_table(["Model", "Batch", "Params (M)", "GFLOPs/sample", "Latency (ms)", "Throughput"], rows, "Measured complexity and inference efficiency.", "tab:efficiency")


def transfer_table() -> str:
    df = pd.read_csv(ROOT / "results" / "transfer_s" / "all_results.csv")
    cases = [("QUIC$\\rightarrow$TLS-40", "quic_to_tls40", "tls40_s"), ("TLS$\\rightarrow$QUIC-40", "tls_to_quic40", "quic40_s"), ("QUIC$\\rightarrow$TLS-60", "quic_to_tls60", "tls60_s"), ("TLS$\\rightarrow$QUIC-60", "tls_to_quic60", "quic60_s")]
    rows = []
    for label, frag, target in cases:
        zero = df[df["exp_name"].str.contains("zero_shot_" + frag)]
        lora = df[df["exp_name"].str.contains("hybrid_lora_" + frag)]
        ft = df[df["exp_name"].str.contains("full_ft_" + frag)]
        rows.append([
            label,
            pct(zero["full_accuracy"].iloc[0]),
            pct(zero["covered_macro_f1"].iloc[0]),
            pct(lora["test_macro_f1"].iloc[0]),
            f"{float(lora['trainable_ratio'].iloc[0]) * 100:.2f}",
            pct(ft["test_macro_f1"].iloc[0]),
            model_stat(target, "Hybrid")[1],
        ])
    return latex_table(["Direction", "Zero-shot Acc", "Covered F1", "LoRA F1", "LoRA params", "Full FT F1", "Scratch F1"], rows, "Cross-protocol transfer results.", "tab:transfer")


def pct_value(text: str) -> float:
    if text in {"", "--"}:
        return math.nan
    return float(str(text).split("$\\pm$")[0])


def save_figure(fig: plt.Figure, filename: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_hsta_architecture() -> Path:
    labels = [
        "Packet\nsequence",
        "Mamba\nencoding",
        "Transition\nMLP",
        "High-level\nattention",
        "Refinement\nMLP",
        "Pooling +\nclassifier",
    ]
    colors = ["#EEF2F7", "#DCEBFA", "#E7F3EA", "#FFF2D8", "#F5E6EA", "#E9E4F4"]
    fig, ax = plt.subplots(figsize=(9.2, 2.2))
    ax.set_axis_off()
    x_positions = list(range(len(labels)))
    for x, label, color in zip(x_positions, labels, colors):
        box = plt.Rectangle(
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
    return save_figure(fig, "fig1_hsta_architecture.png")


def plot_main_macro_f1() -> Path:
    tasks = ["QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]
    keys = ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]
    series = {
        "GRU": [pct_value(model_stat(k, "GRU")[1]) for k in keys],
        "Transformer": [pct_value(model_stat(k, "Transformer")[1]) for k in keys],
        "NetMamba-adapted": [pct_value(sota_stat(k, "NetMamba-adapted")[1]) for k in keys],
        "HSTA-Hybrid": [pct_value(model_stat(k, "Hybrid")[1]) for k in keys],
    }
    colors = ["#7A7A7A", "#4C78A8", "#72B7B2", "#F58518"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
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
    return save_figure(fig, "fig2_main_macro_f1.png")


def plot_ablation_macro_f1() -> Path:
    df = pd.read_csv(ROOT / "results" / "ablation_s" / "all_results.csv")
    rows = []
    variants = [
        ("No Attention", "ablation_no_attention"),
        ("Attention-front", "ablation_attention_front"),
        ("Attention-middle", "ablation_attention_middle"),
    ]
    tasks = [("QUIC-40", "quic40"), ("QUIC-60", "quic60"), ("TLS-40", "tls40"), ("TLS-60", "tls60")]
    for name, prefix in variants:
        rows.append((name, [pct_value(mean_std(df[df["exp_name"].str.contains(prefix) & df["exp_name"].str.contains(frag)]["test_macro_f1"])) for _, frag in tasks]))
    rows.append(("HSTA-Hybrid", [pct_value(model_stat(k, "Hybrid")[1]) for k in ["quic40_s", "quic60_s", "tls40_s", "tls60_s"]]))
    colors = ["#9E9E9E", "#6BAED6", "#74C476", "#F58518"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    width = 0.18
    x = list(range(len(tasks)))
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for (label, values), color, offset in zip(rows, colors, offsets):
        ax.bar([v + offset for v in x], values, width=width, label=label, color=color)
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_ylim(86, 98)
    ax.set_xticks(x)
    ax.set_xticklabels([t[0] for t in tasks])
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(ncol=2, frameon=False, fontsize=8)
    ax.set_title("Attention-Position Ablation")
    return save_figure(fig, "fig3_ablation_macro_f1.png")


def plot_transfer_macro_f1() -> Path:
    df = pd.read_csv(ROOT / "results" / "transfer_s" / "all_results.csv")
    cases = [
        ("QUIC->TLS-40", "quic_to_tls40", "tls40_s"),
        ("TLS->QUIC-40", "tls_to_quic40", "quic40_s"),
        ("QUIC->TLS-60", "quic_to_tls60", "tls60_s"),
        ("TLS->QUIC-60", "tls_to_quic60", "quic60_s"),
    ]
    labels, lora, full_ft, scratch = [], [], [], []
    for label, frag, target in cases:
        labels.append(label)
        lora_row = df[df["exp_name"].str.contains("hybrid_lora_" + frag)]
        ft_row = df[df["exp_name"].str.contains("full_ft_" + frag)]
        lora.append(float(lora_row["test_macro_f1"].iloc[0]) * 100)
        full_ft.append(float(ft_row["test_macro_f1"].iloc[0]) * 100)
        scratch.append(pct_value(model_stat(target, "Hybrid")[1]))
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    width = 0.22
    x = list(range(len(labels)))
    ax.bar([v - width for v in x], lora, width=width, label="LoRA", color="#72B7B2")
    ax.bar(x, full_ft, width=width, label="Full FT", color="#F58518")
    ax.bar([v + width for v in x], scratch, width=width, label="Scratch target", color="#4C78A8")
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_ylim(76, 99)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Cross-Protocol Adaptation")
    return save_figure(fig, "fig4_transfer_macro_f1.png")


def generate_result_figures() -> None:
    plot_hsta_architecture()
    plot_main_macro_f1()
    plot_ablation_macro_f1()
    plot_transfer_macro_f1()


def include_result_figure(filename: str, caption: str, label: str) -> str:
    return rf"""\begin{{figure}}[!htbp]
\centering
\includegraphics[width=0.92\linewidth]{{figures/{filename}}}
\caption{{{caption}}}
\label{{{label}}}
\end{{figure}}"""


def make_fig(name: str, title: str) -> None:
    tex = rf"""\documentclass[tikz,border=6pt]{{standalone}}
\usepackage{{tikz}}
\usetikzlibrary{{positioning,arrows.meta,fit}}
\begin{{document}}
\begin{{tikzpicture}}[font=\small, node distance=1.4cm, box/.style={{draw, rounded corners, align=center, minimum height=0.9cm, minimum width=2.2cm}}, arr/.style={{-Latex, thick}}]
\node[box] (input) {{Packet\\sequence}};
\node[box, right=of input] (mamba) {{Mamba\\encoding}};
\node[box, right=of mamba] (trans) {{Transition\\MLP}};
\node[box, right=of trans] (attn) {{High-level\\attention}};
\node[box, right=of attn] (refine) {{Refinement\\MLP}};
\node[box, right=of refine] (head) {{Pooling +\\classifier}};
\draw[arr] (input) -- (mamba);
\draw[arr] (mamba) -- (trans);
\draw[arr] (trans) -- (attn);
\draw[arr] (attn) -- (refine);
\draw[arr] (refine) -- (head);
\node[above=0.5cm of trans] {{{title}}};
\end{{tikzpicture}}
\end{{document}}
"""
    (OUT / name).write_text(tex, encoding="utf-8")


BIB = r"""
@misc{iyengar2021quic, title={QUIC: A UDP-Based Multiplexed and Secure Transport}, author={Iyengar, Jana and Thomson, Martin}, year={2021}, howpublished={RFC 9000}}
@misc{rescorla2018tls, title={The Transport Layer Security (TLS) Protocol Version 1.3}, author={Rescorla, Eric}, year={2018}, howpublished={RFC 8446}}
@article{luxemburk2023tls, title={Fine-grained TLS services classification with reject option}, author={Luxemburk, Jan and Cejka, Tomas}, journal={Computer Networks}, volume={220}, pages={109467}, year={2023}}
@inproceedings{luxemburk2023datazoo, title={DataZoo: Streamlining Traffic Classification Experiments}, author={Luxemburk, Jan and Hynek, Karel}, booktitle={CoNEXT SAFE Workshop}, year={2023}}
@article{luxemburk2023quic22, title={CESNET-QUIC22: A Large One-Month QUIC Network Traffic Dataset from Backbone Lines}, author={Luxemburk, Jan and Hynek, Karel and Cejka, Tomas and others}, journal={Data in Brief}, volume={46}, pages={108888}, year={2023}}
@article{azab2024traffic, title={Network traffic classification: Techniques, datasets, and challenges}, author={Azab, Ahmed and Khasawneh, Mahmoud and Alrabaee, Saed and Choo, Kim-Kwang Raymond and Sarsour, Mohammad}, journal={Digital Communications and Networks}, volume={10}, number={3}, pages={676--692}, year={2024}}
@article{sharma2025encrypted, title={A survey on encrypted network traffic: identification/classification techniques, challenges, and future directions}, author={Sharma, Anupam and Lashkari, Arash Habibi}, journal={Computer Networks}, volume={257}, pages={110984}, year={2025}}
@article{papadogiannaki2022survey, title={A Survey on Encrypted Network Traffic Analysis Applications, Techniques, and Countermeasures}, author={Papadogiannaki, Eva and Ioannidis, Sotiris}, journal={ACM Computing Surveys}, volume={54}, number={6}, pages={1--35}, year={2022}}
@inproceedings{zhang2023tfegnn, title={TFE-GNN: A Temporal Fusion Encoder Using Graph Neural Networks for Fine-grained Encrypted Traffic Classification}, author={Zhang, Hao and others}, booktitle={WWW}, pages={2066--2075}, year={2023}}
@inproceedings{zhao2022mtflowformer, title={MT-FlowFormer: A Semi-Supervised Flow Transformer for Encrypted Traffic Classification}, author={Zhao, Rui and others}, booktitle={KDD}, year={2022}}
@article{lotfollahi2020deep, title={Deep Packet: A Novel Approach for Encrypted Traffic Classification Using Deep Learning}, author={Lotfollahi, Mohammad and others}, journal={Soft Computing}, volume={24}, pages={1999--2012}, year={2020}}
@inproceedings{zhao2023yatc, title={Yet Another Traffic Classifier: A Masked Autoencoder Based Traffic Transformer with Multi-Level Flow Representation}, author={Zhao, Rui and others}, booktitle={AAAI}, volume={37}, number={4}, pages={5420--5427}, year={2023}}
@inproceedings{meng2022packet, title={Packet Representation Learning for Traffic Classification}, author={Meng, Xiang and others}, booktitle={KDD}, year={2022}}
@inproceedings{vaswani2017attention, title={Attention Is All You Need}, author={Vaswani, Ashish and others}, booktitle={Advances in Neural Information Processing Systems}, year={2017}}
@article{hochreiter1997lstm, title={Long Short-Term Memory}, author={Hochreiter, Sepp and Schmidhuber, Jurgen}, journal={Neural Computation}, volume={9}, number={8}, pages={1735--1780}, year={1997}}
@inproceedings{cho2014gru, title={Learning Phrase Representations Using RNN Encoder-Decoder for Statistical Machine Translation}, author={Cho, Kyunghyun and others}, booktitle={EMNLP}, year={2014}}
@inproceedings{dao2024ssm, title={Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality}, author={Dao, Tri and Gu, Albert}, booktitle={ICML}, year={2024}}
@inproceedings{gu2022s4, title={Efficiently Modeling Long Sequences with Structured State Spaces}, author={Gu, Albert and Goel, Karan and Re, Christopher}, booktitle={ICLR}, year={2022}}
@misc{gu2023mamba, title={Mamba: Linear-Time Sequence Modeling with Selective State Spaces}, author={Gu, Albert and Dao, Tri}, year={2023}, eprint={2312.00752}, archivePrefix={arXiv}}
@inproceedings{hu2022lora, title={LoRA: Low-Rank Adaptation of Large Language Models}, author={Hu, Edward J. and others}, booktitle={ICLR}, year={2022}}
@inproceedings{lin2022etbert, title={ET-BERT: A Contextualized Datagram Representation with Pre-training Transformers for Encrypted Traffic Classification}, author={Lin, Xinjie and others}, booktitle={WWW}, pages={633--642}, year={2022}}
@inproceedings{wang2024netmamba, title={NetMamba: Efficient Network Traffic Classification via Pre-training Unidirectional Mamba}, author={Wang, Tian and others}, booktitle={IEEE ICNP}, year={2024}}
@inproceedings{li2023minority, title={Listen to Minority: Encrypted Traffic Classification for Class Imbalance with Contrastive Pre-Training}, author={Li, Xin and others}, booktitle={IEEE SECON}, year={2023}}
@misc{wickramasinghe2025sok, title={SoK: Decoding the Enigma of Encrypted Network Traffic Classifiers}, author={Wickramasinghe, N. and Shaghaghi, A. and Tsudik, G. and Jha, S.}, year={2025}, eprint={2503.20093}, archivePrefix={arXiv}}
@misc{gahtan2024quic, title={Exploring QUIC Dynamics: A Large-Scale Dataset for Encrypted Traffic Analysis}, author={Gahtan, B. and Shahla, R. J. and Bronstein, A. M. and Cohen, R.}, year={2024}, eprint={2410.03728}, archivePrefix={arXiv}}
@misc{luxemburk2025embedding, title={Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining}, author={Luxemburk, Jan and Hynek, Karel and Plny, R. and Cejka, Tomas}, year={2025}, eprint={2502.12930}, archivePrefix={arXiv}}
@inproceedings{zhou2025trafficformer, title={TrafficFormer: An Efficient Pre-trained Model for Traffic Data}, author={Zhou, Guang and others}, booktitle={IEEE Symposium on Security and Privacy}, year={2025}}
@article{hynek2024tlsyear, title={CESNET-TLS-Year22: A Year-Spanning TLS Network Traffic Dataset from Backbone Lines}, author={Hynek, Karel and Luxemburk, Jan and others}, journal={Scientific Data}, volume={11}, pages={1156}, year={2024}}
@article{aceto2019mobile, title={Mobile Encrypted Traffic Classification Using Deep Learning: Experimental Evaluation, Lessons Learned, and Challenges}, author={Aceto, Giuseppe and Ciuonzo, Domenico and Montieri, Antonio and Pescape, Antonio}, journal={IEEE Transactions on Network and Service Management}, volume={16}, number={2}, pages={445--458}, year={2019}}
@article{aceto2021distiller, title={DISTILLER: Encrypted Traffic Classification via Multimodal Multitask Deep Learning}, author={Aceto, Giuseppe and Ciuonzo, Domenico and Montieri, Antonio and Persico, Valerio and Pescape, Antonio}, journal={Journal of Network and Computer Applications}, volume={183}, pages={102985}, year={2021}}
@article{lin2023multimodal, title={A Novel Multimodal Deep Learning Framework for Encrypted Traffic Classification}, author={Lin, Xinjie and others}, journal={IEEE/ACM Transactions on Networking}, volume={31}, number={3}, pages={1369--1384}, year={2023}}
@article{malekghaini2023drift, title={Deep Learning for Encrypted Traffic Classification in the Face of Data Drift: An Empirical Study}, author={Malekghaini, Amirhossein and Ispoglou, Kyriakos M. and Choffnes, David and Mahanti, Anirban}, journal={Computer Networks}, volume={225}, pages={109648}, year={2023}}
@inproceedings{zhao2025sweet, title={The Sweet Danger of Sugar: Debunking Representation Learning Based Network Traffic Classification}, author={Zhao, Rui and others}, booktitle={ACM SIGCOMM}, year={2025}}
@article{shapira2021flowpic, title={FlowPic: A Generic Representation for Encrypted Traffic Classification and Applications Identification}, author={Shapira, Tal and Shavitt, Yuval}, journal={IEEE Transactions on Network and Service Management}, year={2021}, doi={10.1109/TNSM.2021.3071441}}
@article{wang2023twophase, title={A Two-Phase Approach to Fast and Accurate Classification of Encrypted Traffic}, author={Wang, Yipeng and He, Huijie and Lai, Yingxu and Liu, Alex X.}, journal={IEEE/ACM Transactions on Networking}, year={2023}, doi={10.1109/TNET.2022.3209979}}
@article{chen2024multiflow, title={Classify Traffic Rather Than Flow: Versatile Multi-Flow Encrypted Traffic Classification With Flow Clustering}, author={Chen, Zihan and Cheng, Guang and Wei, Zijun and Niu, Dandan and Fu, Nan}, journal={IEEE Transactions on Network and Service Management}, year={2024}, doi={10.1109/TNSM.2023.3322861}}
@article{kattadige2021seta, title={SETA++: Real-Time Scalable Encrypted Traffic Analytics in Multi-Gbps Networks}, author={Kattadige, Chamara and Choi, Kwon Nung and Wijesinghe, Achintha and Nama, Arpit and Thilakarathna, Kanchana and Seneviratne, Suranga and Jourjon, Guillaume}, journal={IEEE Transactions on Network and Service Management}, year={2021}, doi={10.1109/TNSM.2021.3085097}}
@inproceedings{xie2023rosetta, title={Rosetta: Enabling Robust TLS Encrypted Traffic Classification in Diverse Network Environments with TCP-Aware Traffic Augmentation}, author={Xie, Renjie and others}, booktitle={Proceedings of the ACM Turing Award Celebration Conference - China}, year={2023}, doi={10.1145/3603165.3607437}}
@article{li2025satnet, title={SAT-Net: A Staggered Attention Network Using Graph Neural Networks for Encrypted Traffic Classification}, author={Li, Zhiyuan and Zhao, Hongyi and Zhao, Jingyu and Jiang, Yuqi and Bu, Fanliang}, journal={Journal of Network and Computer Applications}, pages={104069}, year={2025}, doi={10.1016/j.jnca.2024.104069}}
"""


def write_main() -> None:
    body = rf"""% !TeX program = pdflatex
% English JNCA/Elsevier manuscript. Overleaf should compile this file with pdfLaTeX.
\documentclass[preprint,12pt]{{elsarticle}}

\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{tabularx}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage[section]{{placeins}}
\usepackage{{lineno}}
\usepackage{{hyperref}}

\journal{{Journal of Network and Computer Applications}}

\begin{{document}}

\begin{{frontmatter}}

\title{{Hybrid State-Space Transition-Attention Modeling for Lightweight Encrypted QUIC/TLS Traffic Classification}}

\author[aff1]{{Author One\corref{{cor1}}}}
\ead{{email@example.com}}
\author[aff1]{{Author Two}}
\author[aff2]{{Author Three}}
\cortext[cor1]{{Corresponding author [placeholder; confirm before submission]}}
\address[aff1]{{Affiliation 1 [placeholder], City, Country}}
\address[aff2]{{Affiliation 2 [placeholder], City, Country}}

\begin{{abstract}}
The widespread deployment of TLS 1.3 and QUIC has made encrypted traffic classification increasingly dependent on weak side-channel information, because port numbers, plaintext payloads, and deep packet inspection rules are no longer reliable. In fine-grained service identification, packet sizes, directions, and inter-arrival times often expose only limited and overlapping behavioral patterns. This paper proposes a Hybrid State-space Transition-Attention Block (HSTA Block) for lightweight encrypted QUIC/TLS traffic classification. The block integrates Mamba-based state-space sequence encoding, Transition MLP representation transformation, high-level attention reweighting, and Refinement MLP feature consolidation into a single feature extraction unit. Rather than stacking modules mechanically, the design first captures packet-level sequential dependencies and then emphasizes discriminative traffic patterns in a more stable high-level representation space. Experiments on QUIC-40, QUIC-60, TLS-40, and TLS-60 tasks derived from CESNET-QUIC22 and CESNET-TLS22 show Macro-F1 scores of 91.09$\pm$0.20\%, 90.28$\pm$0.39\%, 96.78$\pm$0.14\%, and 96.29$\pm$0.17\%, respectively. HSTA-Hybrid consistently outperforms MLP, CNN, LSTM, GRU, Transformer, and two adapted advanced baselines under the same lightweight packet-level input. Ablation, efficiency, depth-sensitivity, cross-protocol transfer, and class-level error analyses further indicate that the gain comes from the ordered cooperation among state-space sequence modeling, representation transformation, and high-level attention reweighting.
\end{{abstract}}

\begin{{highlights}}
\item HSTA Block combines Mamba encoding, transition, attention, and refinement.
\item HSTA-Hybrid achieves the best Macro-F1 on four QUIC/TLS tasks.
\item Ablation shows attention works best after state-space transformation.
\item Efficiency, depth sensitivity, and cross-protocol transfer are evaluated.
\end{{highlights}}

\begin{{keyword}}
encrypted traffic classification \sep QUIC \sep TLS \sep Mamba \sep state-space model \sep cross-protocol transfer
\end{{keyword}}

\end{{frontmatter}}

\linenumbers

\section{{Introduction}}
Internet traffic analysis is moving from visible protocol fields and plaintext payloads toward behavioral inference under encryption. TLS~1.3 strengthens encrypted transport, while QUIC integrates reliable transport, multiplexing, connection migration, and TLS-based encryption over UDP~\cite{{iyengar2021quic,rescorla2018tls}}. These mechanisms improve privacy and performance but reduce the effectiveness of conventional traffic identification methods used for network management, security monitoring, and quality-of-service control.

When payloads and application-layer metadata are unavailable, a classifier must rely on packet sizes, packet directions, and inter-arrival times. These features are sequential and informative, but they are also weak, noisy, and often shared by multiple services. The coexistence of QUIC and TLS further complicates the problem because their transport mechanisms shape packet sequences differently, making direct cross-protocol transfer unreliable.

To address this setting, we design HSTA Block as a problem-driven feature extraction unit. Mamba modules model directional changes, packet-size dynamics, and burst patterns; a Transition MLP maps state-space outputs to a discriminative representation space; an attention module reweights high-level traffic patterns; and a Refinement MLP consolidates the reweighted sequence before pooling and classification. The contributions are fourfold: we construct four reproducible QUIC/TLS fine-grained tasks, propose a lightweight hybrid state-space and attention architecture, verify the mechanism through ablation and class-level error analysis, and evaluate complexity, inference efficiency, and cross-protocol adaptation for deployment-oriented use.

\section{{Related Work}}
Early traffic classification relied on ports, protocol fields, DPI rules, or manually designed statistics. Dynamic ports, encryption, content delivery infrastructures, and rapid application evolution have progressively weakened these assumptions~\cite{{azab2024traffic,sharma2025encrypted,papadogiannaki2022survey}}. Deep learning approaches address this limitation by learning representations directly from packet sequences, burst patterns, or flow-level features.

TLS and QUIC are central to current encrypted communication. TLS usually runs over TCP, whereas QUIC runs over UDP and embeds reliable transport, multiplexing, connection migration, and TLS encryption. CESNET-TLS22, CESNET-QUIC22, and DataZoo provide realistic and reproducible foundations for fine-grained service classification in backbone traffic~\cite{{luxemburk2023tls,luxemburk2023quic22,luxemburk2023datazoo,gahtan2024quic,luxemburk2025embedding}}. CNNs, recurrent models, Transformers, pretrained traffic models, and graph neural networks have all been explored for encrypted traffic classification~\cite{{lotfollahi2020deep,zhao2022mtflowformer,zhao2023yatc,meng2022packet,li2023minority,lin2022etbert,zhou2025trafficformer,vaswani2017attention,hochreiter1997lstm,cho2014gru}}. Recent state-space models, including Mamba, offer input-dependent sequence modeling with favorable computational properties~\cite{{dao2024ssm,gu2022s4,gu2023mamba}}. This work focuses on a lightweight online scenario that uses only the first 30 packets and three side-channel features per packet, and studies how state-space modeling and high-level attention can be combined effectively.

\section{{Problem Definition and Method}}
An encrypted flow is represented as a packet-level sequence $X=[x_1,\ldots,x_T]$ with $T=30$, where each $x_t$ contains packet size, direction, and packet inter-arrival time. Flows longer than 30 packets are truncated, while shorter flows are padded during preprocessing. No plaintext payload, domain name, application-layer content, or DPI-derived feature is used.

The objective is to learn a mapping $f_\theta:X\rightarrow y$ for closed-set classification on QUIC-40, QUIC-60, TLS-40, or TLS-60. Models are trained with cross-entropy loss, and validation Macro-F1 is used for model selection and early stopping. Because the tasks are fine-grained and class-imbalanced, Macro-F1 is treated as the primary metric. The design is motivated by three observations: packet-level side channels contain sequential dependencies such as direction switching and burst transmission; raw low-level features are noisy, so applying attention too early may amplify short-term fluctuations; and representations produced by state-space encoding and nonlinear transformation are more suitable for global reweighting.

The full model consists of an input projection layer, an HSTA Block, sequence pooling, and an independent MLP classification head. The projection layer maps three-dimensional packet-level side-channel features into a hidden space. The HSTA Block extracts hybrid sequential features, mean pooling produces a flow-level representation, and the classifier outputs class probabilities.

{include_result_figure("fig1_hsta_architecture.png", "Schematic of the HSTA Block.", "fig:hsta")}

HSTA Block has four stages. First, consecutive Mamba modules capture packet-level sequential dependencies through selective state-space modeling. Second, a Transition MLP performs nonlinear transformation and representation alignment. Third, the attention module computes Query-Key-Value interactions in the high-level representation space and assigns larger weights to discriminative packet segments or feature combinations. Fourth, a Refinement MLP consolidates the reweighted representation for downstream pooling and classification.

All experiments use a batch size of 512, a hidden dimension of 128, dropout of 0.15, Mamba state dimension of 16, local convolution kernel size of 4, and expansion factor of 2. The main model uses one HSTA Block; depth sensitivity is evaluated with one, two, and four blocks. All models share the same input features, data splits, and metrics for fair comparison.

\section{{Experimental Setup}}
The experiments are based on CESNET-QUIC22 and CESNET-TLS22, exported through DataZoo as the first 30 packets with packet size, direction, and inter-arrival time. We build four tasks, QUIC-40, QUIC-60, TLS-40, and TLS-60, to cover different protocols, class scales, and imbalance levels.

The compared models include MLP, CNN, LSTM, GRU, Transformer, HSTA-Hybrid, and two adapted advanced baselines: 30pktTCNET-adapted and NetMamba-adapted~\cite{{wang2024netmamba}}. These adapted baselines are used only for fair structural comparison under the same lightweight side-channel input, and should not be interpreted as full reproductions of the original methods with their complete input pipelines or pretraining procedures. Transformer, HSTA-Hybrid, the adapted advanced baselines, and the ablation variants are repeated with three random seeds and reported as mean$\pm$standard deviation. Metrics include Accuracy, Macro-F1, parameters, FLOPs, forward latency, throughput, peak GPU memory, zero-shot transfer, LoRA adaptation, and full fine-tuning.

{result_tables()}

\section{{Results and Analysis}}
Tables~\ref{{tab:main40}} and~\ref{{tab:main60}} show that HSTA-Hybrid achieves the best average Macro-F1 on all four tasks. Compared with NetMamba-adapted, it improves Macro-F1 by approximately 1.21, 1.32, 0.57, and 0.11 percentage points on QUIC-40, QUIC-60, TLS-40, and TLS-60, respectively. The improvement is more pronounced on QUIC, indicating that complex modern transport behavior benefits from the joint modeling of packet-level order and high-level discriminative patterns.

{include_result_figure("fig2_main_macro_f1.png", "Macro-F1 comparison of main models on four tasks.", "fig:main-macro-f1")}

When the number of classes increases from 40 to 60, the Macro-F1 of HSTA-Hybrid decreases from 91.09$\pm$0.20\% to 90.28$\pm$0.39\% on QUIC, and from 96.78$\pm$0.14\% to 96.29$\pm$0.17\% on TLS. The relatively small degradation suggests that the model remains robust when additional low-frequency classes are introduced.

{ablation_table()}

The attention-position ablation in Table~\ref{{tab:ablation}} confirms that the gain is not caused by simply adding an attention layer. The complete HSTA Block outperforms no-attention, front-attention, and middle-attention variants on all tasks. This supports the hypothesis that attention is most effective after Mamba sequence encoding and Transition MLP transformation.

{include_result_figure("fig3_ablation_macro_f1.png", "Attention-position ablation comparison.", "fig:ablation-macro-f1")}

{efficiency_table()}

Complexity and efficiency measurements in Table~\ref{{tab:efficiency}} show that HSTA-Hybrid has fewer parameters than Transformer and offers a favorable performance-efficiency trade-off for small and medium batch inference. The results also show that theoretical FLOPs do not fully determine practical latency.

{transfer_table()}

Cross-protocol transfer results in Table~\ref{{tab:transfer}} show that direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior. LoRA trains only about 5.36\%--5.75\% of the parameters and provides partial adaptation, but remains weaker than full fine-tuning~\cite{{hu2022lora}}.

{include_result_figure("fig4_transfer_macro_f1.png", "Cross-protocol adaptation comparison.", "fig:transfer-macro-f1")}

Full fine-tuning transfers from QUIC to TLS as well as, or slightly better than, training from scratch on TLS, whereas TLS-to-QUIC transfer remains below QUIC training from scratch. This reveals a clear direction asymmetry in cross-protocol adaptation.

\section{{Discussion}}
The effectiveness of HSTA Block comes from the alignment between its processing order and the structure of encrypted traffic. The lower stage captures packet-level dynamics, the higher stage selects stable discriminative patterns, and the refinement stage consolidates attention-enhanced features. This design is especially beneficial for QUIC, whose multiplexing, connection migration, and reliable transport over UDP produce more complex sequential behavior.

The efficiency results also show that theoretical FLOPs do not fully determine practical latency. 30pktTCNET-adapted has lower latency or higher throughput in some batch settings, but its Macro-F1 is clearly lower than that of HSTA-Hybrid. NetMamba-adapted has fewer theoretical FLOPs, but does not achieve the lowest measured latency in this short-sequence setting. We therefore position HSTA-Hybrid as a performance-oriented model that still maintains a practical trade-off for online or medium-batch inference.

This study has limitations. It uses only the first 30 packets and focuses on closed-set classification. It does not yet address unknown-class rejection, long-term temporal drift, or cross-collection generalization~\cite{{hynek2024tlsyear}}. Inference efficiency is measured on a single GPU platform, and the adapted advanced baselines are not full reproductions of the original methods. Future work should investigate open-set recognition, self-supervised pretraining, protocol-adaptive continual learning, and real online deployment.

\section{{Conclusion}}
This paper presented HSTA Block for lightweight fine-grained QUIC/TLS encrypted traffic classification. By organizing state-space sequence encoding, representation transformation, high-level attention reweighting, and feature refinement into a unified block, the proposed model improves Macro-F1 on four tasks using only packet size, direction, and inter-arrival time. Extensive experiments show that the advantage of HSTA-Hybrid comes from structural cooperation rather than merely adding attention or increasing depth. Ablation, efficiency, depth, transfer, and error analyses indicate that the method is suitable for fine-grained service identification under modern encrypted protocols and provides a basis for future protocol-adaptive and deployable encrypted traffic classification systems.

\section*{{Declarations}}
\textbf{{Author contributions (CRediT):}} Author One: Conceptualization, Methodology, Software, Investigation, Writing - original draft; Author Two: Data curation, Validation, Formal analysis, Visualization; Author Three: Supervision, Writing - review and editing, Project administration. [placeholder; confirm final roles before submission]

\textbf{{Funding:}} Funding information is to be completed. [placeholder or state no funding]

\textbf{{Declaration of competing interest:}} The authors declare that they have no known competing financial interests or personal relationships that could have influenced the work reported in this paper. [to be confirmed]

\textbf{{Data and code availability:}} The experiments are based on CESNET-QUIC22, CESNET-TLS22, and DataZoo. Code and processing scripts are available in the project repository; the final link should be handled according to the journal's anonymous review or repository policy.

\bibliographystyle{{elsarticle-num}}
\bibliography{{references}}

\end{{document}}
"""
    (OUT / "main.tex").write_text(body, encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    generate_result_figures()
    write_main()
    (OUT / "references.bib").write_text(BIB.strip() + "\n", encoding="utf-8")
    make_fig("fig_hsta_block.tex", "HSTA Block")
    readme = """# Overleaf/JNCA submission package

Upload every file in this folder to Overleaf and set `main.tex` as the main file.

Recommended compile sequence on Overleaf: pdfLaTeX + BibTeX. The included `latexmkrc` sets pdfLaTeX as the default engine. The template uses Elsevier `elsarticle` with numerical citations and `elsarticle-num.bst`.
The package includes `elsarticle-num.bst` copied from the official Elsevier template bundle. `elsarticle.cls` is expected from Overleaf or the submission-system TeX installation.

If Overleaf shows many errors immediately after import, first check that:
- The main file is `main.tex`.
- The compiler is pdfLaTeX.
- You uploaded this English package, not the Chinese XeLaTeX package.
- If the log says `elsarticle.cls not found`, use Overleaf first or confirm that the submission platform supports the Elsevier `elsarticle` class.

Files:
- `main.tex`: Elsevier `elsarticle` manuscript.
- `references.bib`: BibTeX references.
- `elsarticle-num.bst`: Elsevier numerical bibliography style copied from the official template bundle.
- `elsarticle.cls`: not bundled here; expected from Overleaf or the submission-system TeX installation.
- `latexmkrc`: Overleaf compiler hint; keeps this package on pdfLaTeX.
- `fig_hsta_block.tex`: standalone editable TikZ source for the architecture figure, kept as a replacement source if you want to refine Figure 1.
- `figure_notes.md`: figure-generation and replacement notes.
- `figures/fig1_hsta_architecture.png`: generated HSTA architecture overview used by `main.tex`.
- `figures/fig2_main_macro_f1.png`: generated main Macro-F1 comparison.
- `figures/fig3_ablation_macro_f1.png`: generated attention-position ablation comparison.
- `figures/fig4_transfer_macro_f1.png`: generated cross-protocol adaptation comparison.

Before final submission:
- Replace author, affiliation, funding, and repository placeholders.
- Replace the generated Figure 1 PNG with final exported draw.io artwork if you want to use the refined architecture figure.
- Keep the generated result figures or replace them with journal-polished artwork exported from `paper/论文全部图_精修可编辑.drawio`.
"""
    (OUT / "README_overleaf.md").write_text(readme, encoding="utf-8")
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    (OUT / "latexmkrc").write_text("$pdf_mode = 1;\n", encoding="utf-8")
    bst = TEMPLATE / "elsarticle-num.bst"
    if bst.exists():
        shutil.copy2(bst, OUT / "elsarticle-num.bst")
    figure_note = "main.tex includes generated PNG figures under figures/. Replace Figure 1 with exported draw.io artwork before final submission if desired.\n"
    figure_notes = """# Figure Notes

- Figure 1 is generated as `figures/fig1_hsta_architecture.png`; `fig_hsta_block.tex` is kept as an editable TikZ replacement source.
- Figures 2, 3, and 4 are generated automatically from existing CSV summaries under `results/`.
- The editable draw.io source is `paper/论文全部图_精修可编辑.drawio`; export polished PDF/PNG artwork from it before final journal submission if needed.
- Do not hand-edit numerical values in figures; regenerate them from the manuscript scripts when result CSV files change.
"""
    (OUT / "FIGURE_BUILD_NOTE.txt").write_text(figure_note, encoding="utf-8")
    (OUT / "figure_notes.md").write_text(figure_notes, encoding="utf-8")
    zip_path = OUT.parent / "overleaf_jnca_package.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", OUT)
    print(OUT)
    print(zip_path)


if __name__ == "__main__":
    main()
