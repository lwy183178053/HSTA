from __future__ import annotations

import importlib.util
import shutil
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "jnca_bilingual_latex"
FIG_DIR = OUT / "figures"
SUBMISSION = ROOT / "paper" / "submission_jnca"
SUBMISSION_OVERLEAF = SUBMISSION / "overleaf_jnca"
SUBMISSION_OVERLEAF_ZIP = SUBMISSION / "overleaf_jnca_package.zip"
EDITORIAL_SOURCE_DIR = SUBMISSION / "editorial_manager_latex_source"
EDITORIAL_SOURCE_ZIP = SUBMISSION / "JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip"
SUBMISSION_SCRIPT = ROOT / "scripts" / "generate_jnca_submission.py"
OVERLEAF_SCRIPT = ROOT / "scripts" / "generate_jnca_overleaf.py"
COMBINED_ZIP = ROOT / "paper" / "jnca_bilingual_latex_package.zip"
ENGLISH_ZIP = ROOT / "paper" / "jnca_english_overleaf_package.zip"
CHINESE_ZIP = ROOT / "paper" / "jnca_chinese_xelatex_package.zip"


REF_ITEMS = [
    ("iyengar2021quic", "J. Iyengar and M. Thomson, ``QUIC: A UDP-Based Multiplexed and Secure Transport,'' RFC 9000, Internet Engineering Task Force, 2021."),
    ("rescorla2018tls", "E. Rescorla, ``The Transport Layer Security (TLS) Protocol Version 1.3,'' RFC 8446, Internet Engineering Task Force, 2018."),
    ("luxemburk2023tls", "J. Luxemburk and T. Cejka, ``Fine-grained TLS services classification with reject option,'' Computer Networks, vol. 220, article 109467, 2023."),
    ("luxemburk2023datazoo", "J. Luxemburk and K. Hynek, ``DataZoo: Streamlining Traffic Classification Experiments,'' CoNEXT SAFE Workshop, 2023."),
    ("luxemburk2023quic22", "J. Luxemburk, K. Hynek, T. Cejka, A. Lukacovic, and P. Siska, ``CESNET-QUIC22: A Large One-Month QUIC Network Traffic Dataset from Backbone Lines,'' Data in Brief, vol. 46, article 108888, 2023."),
    ("azab2024traffic", "A. Azab, M. Khasawneh, S. Alrabaee, K.-K. R. Choo, and M. Sarsour, ``Network traffic classification: Techniques, datasets, and challenges,'' Digital Communications and Networks, vol. 10, no. 3, pp. 676--692, 2024."),
    ("sharma2025encrypted", "A. Sharma and A. H. Lashkari, ``A survey on encrypted network traffic: identification/classification techniques, challenges, and future directions,'' Computer Networks, vol. 257, article 110984, 2025."),
    ("papadogiannaki2022survey", "E. Papadogiannaki and S. Ioannidis, ``A Survey on Encrypted Network Traffic Analysis Applications, Techniques, and Countermeasures,'' ACM Computing Surveys, vol. 54, no. 6, article 124, 2022."),
    ("zhang2023tfegnn", "H. Zhang et al., ``TFE-GNN: A Temporal Fusion Encoder Using Graph Neural Networks for Fine-grained Encrypted Traffic Classification,'' WWW, pp. 2066--2075, 2023."),
    ("zhao2022mtflowformer", "R. Zhao et al., ``MT-FlowFormer: A Semi-Supervised Flow Transformer for Encrypted Traffic Classification,'' KDD, 2022."),
    ("lotfollahi2020deep", "M. Lotfollahi et al., ``Deep Packet: A Novel Approach for Encrypted Traffic Classification Using Deep Learning,'' Soft Computing, vol. 24, pp. 1999--2012, 2020."),
    ("zhao2023yatc", "R. Zhao et al., ``Yet Another Traffic Classifier: A Masked Autoencoder Based Traffic Transformer with Multi-Level Flow Representation,'' AAAI, vol. 37, no. 4, pp. 5420--5427, 2023."),
    ("meng2022packet", "X. Meng et al., ``Packet Representation Learning for Traffic Classification,'' KDD, 2022."),
    ("vaswani2017attention", "A. Vaswani et al., ``Attention Is All You Need,'' Advances in Neural Information Processing Systems, 2017."),
    ("hochreiter1997lstm", "S. Hochreiter and J. Schmidhuber, ``Long Short-Term Memory,'' Neural Computation, vol. 9, no. 8, pp. 1735--1780, 1997."),
    ("cho2014gru", "K. Cho et al., ``Learning Phrase Representations Using RNN Encoder-Decoder for Statistical Machine Translation,'' EMNLP, 2014."),
    ("dao2024ssm", "T. Dao and A. Gu, ``Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality,'' ICML, 2024."),
    ("gu2022s4", "A. Gu, K. Goel, and C. Re, ``Efficiently Modeling Long Sequences with Structured State Spaces,'' ICLR, 2022."),
    ("gu2023mamba", "A. Gu and T. Dao, ``Mamba: Linear-Time Sequence Modeling with Selective State Spaces,'' arXiv:2312.00752, 2023."),
    ("hu2022lora", "E. J. Hu et al., ``LoRA: Low-Rank Adaptation of Large Language Models,'' ICLR, 2022."),
    ("lin2022etbert", "X. Lin et al., ``ET-BERT: A Contextualized Datagram Representation with Pre-training Transformers for Encrypted Traffic Classification,'' WWW, pp. 633--642, 2022."),
    ("wang2024netmamba", "T. Wang et al., ``NetMamba: Efficient Network Traffic Classification via Pre-training Unidirectional Mamba,'' IEEE ICNP, 2024."),
    ("li2023minority", "X. Li et al., ``Listen to Minority: Encrypted Traffic Classification for Class Imbalance with Contrastive Pre-Training,'' IEEE SECON, 2023."),
    ("wickramasinghe2025sok", "N. Wickramasinghe, A. Shaghaghi, G. Tsudik, and S. Jha, ``SoK: Decoding the Enigma of Encrypted Network Traffic Classifiers,'' arXiv:2503.20093, 2025."),
    ("gahtan2024quic", "B. Gahtan, R. J. Shahla, A. M. Bronstein, and R. Cohen, ``Exploring QUIC Dynamics: A Large-Scale Dataset for Encrypted Traffic Analysis,'' arXiv:2410.03728, 2024."),
    ("luxemburk2025embedding", "J. Luxemburk, K. Hynek, R. Plny, and T. Cejka, ``Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining,'' arXiv:2502.12930, 2025."),
    ("zhou2025trafficformer", "G. Zhou et al., ``TrafficFormer: An Efficient Pre-trained Model for Traffic Data,'' IEEE Symposium on Security and Privacy, 2025."),
    ("hynek2024tlsyear", "K. Hynek, J. Luxemburk, et al., ``CESNET-TLS-Year22: A Year-Spanning TLS Network Traffic Dataset from Backbone Lines,'' Scientific Data, vol. 11, article 1156, 2024."),
    ("aceto2019mobile", "G. Aceto, D. Ciuonzo, A. Montieri, and A. Pescape, ``Mobile Encrypted Traffic Classification Using Deep Learning: Experimental Evaluation, Lessons Learned, and Challenges,'' IEEE Transactions on Network and Service Management, vol. 16, no. 2, pp. 445--458, 2019."),
    ("aceto2021distiller", "G. Aceto, D. Ciuonzo, A. Montieri, V. Persico, and A. Pescape, ``DISTILLER: Encrypted Traffic Classification via Multimodal Multitask Deep Learning,'' Journal of Network and Computer Applications, vol. 183, article 102985, 2021."),
    ("lin2023multimodal", "X. Lin et al., ``A Novel Multimodal Deep Learning Framework for Encrypted Traffic Classification,'' IEEE/ACM Transactions on Networking, vol. 31, no. 3, pp. 1369--1384, 2023."),
    ("malekghaini2023drift", "A. Malekghaini, K. M. Ispoglou, D. Choffnes, and A. Mahanti, ``Deep Learning for Encrypted Traffic Classification in the Face of Data Drift: An Empirical Study,'' Computer Networks, vol. 225, article 109648, 2023."),
    ("zhao2025sweet", "R. Zhao et al., ``The Sweet Danger of Sugar: Debunking Representation Learning Based Network Traffic Classification,'' ACM SIGCOMM, 2025."),
    ("shapira2021flowpic", "T. Shapira and Y. Shavitt, ``FlowPic: A Generic Representation for Encrypted Traffic Classification and Applications Identification,'' IEEE Transactions on Network and Service Management, 2021."),
    ("wang2023twophase", "Y. Wang, H. He, Y. Lai, and A. X. Liu, ``A Two-Phase Approach to Fast and Accurate Classification of Encrypted Traffic,'' IEEE/ACM Transactions on Networking, 2023."),
    ("chen2024multiflow", "Z. Chen, G. Cheng, Z. Wei, D. Niu, and N. Fu, ``Classify Traffic Rather Than Flow: Versatile Multi-Flow Encrypted Traffic Classification With Flow Clustering,'' IEEE Transactions on Network and Service Management, 2024."),
    ("kattadige2021seta", "C. Kattadige, K. N. Choi, A. Wijesinghe, A. Nama, K. Thilakarathna, S. Seneviratne, and G. Jourjon, ``SETA++: Real-Time Scalable Encrypted Traffic Analytics in Multi-Gbps Networks,'' IEEE Transactions on Network and Service Management, 2021."),
    ("xie2023rosetta", "R. Xie et al., ``Rosetta: Enabling Robust TLS Encrypted Traffic Classification in Diverse Network Environments with TCP-Aware Traffic Augmentation,'' Proceedings of the ACM Turing Award Celebration Conference - China, 2023."),
    ("li2025satnet", "Z. Li, H. Zhao, J. Zhao, Y. Jiang, and F. Bu, ``SAT-Net: A Staggered Attention Network Using Graph Neural Networks for Encrypted Traffic Classification,'' Journal of Network and Computer Applications, article 104069, 2025."),
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tex_escape(value: object) -> str:
    text = str(value)
    markers = {
        r"~\ref{tab:main40-en}": "ZZREFTABMAIN40ENZZ",
        r"~\ref{tab:main60-en}": "ZZREFTABMAIN60ENZZ",
        r"~\ref{tab:ablation-en}": "ZZREFTABABLATIONENZZ",
        r"~\ref{fig:ablation-macro-f1-en}": "ZZREFFIGABLATIONENZZ",
        r"~\ref{tab:efficiency-en}": "ZZREFTABEFFICIENCYENZZ",
        r"~\ref{tab:transfer-en}": "ZZREFTABTRANSFERENZZ",
        r"~\ref{fig:transfer-macro-f1-en}": "ZZREFFIGTRANSFERENZZ",
        r"~\ref{fig:hsta-en}": "ZZREFFIGHSTAENZZ",
        r"~\ref{tab:dataset-en}": "ZZREFTABDATASETENZZ",
        r"~\ref{tab:adapted-baselines-en}": "ZZREFTABADAPTEDENZZ",
        r"~\ref{fig:main-macro-f1-en}": "ZZREFFIGMAINENZZ",
        r"~\ref{tab:scaling-en}": "ZZREFTABSCALINGENZZ",
        r"~\ref{tab:depth-en}": "ZZREFTABDEPTHENZZ",
        r"~\ref{tab:confusion-en}": "ZZREFTABCONFUSIONENZZ",
        r"~\ref{tab:main40-cn}": "ZZREFTABMAIN40CNZZ",
        r"~\ref{tab:main60-cn}": "ZZREFTABMAIN60CNZZ",
        r"~\ref{tab:ablation-cn}": "ZZREFTABABLATIONCNZZ",
        r"~\ref{fig:ablation-macro-f1-cn}": "ZZREFFIGABLATIONCNZZ",
        r"~\ref{tab:efficiency-cn}": "ZZREFTABEFFICIENCYCNZZ",
        r"~\ref{tab:transfer-cn}": "ZZREFTABTRANSFERCNZZ",
        r"~\ref{fig:transfer-macro-f1-cn}": "ZZREFFIGTRANSFERCNZZ",
        r"~\ref{fig:hsta-cn}": "ZZREFFIGHSTACNZZ",
        r"~\ref{tab:dataset-cn}": "ZZREFTABDATASETCNZZ",
        r"~\ref{tab:adapted-baselines-cn}": "ZZREFTABADAPTEDCNZZ",
        r"~\ref{fig:main-macro-f1-cn}": "ZZREFFIGMAINCNZZ",
        r"~\ref{tab:scaling-cn}": "ZZREFTABSCALINGCNZZ",
        r"~\ref{tab:depth-cn}": "ZZREFTABDEPTHCNZZ",
        r"~\ref{tab:confusion-cn}": "ZZREFTABCONFUSIONCNZZ",
        "X=[x1,...,xT]": "@@SEQ@@",
        "T=30": "@@T30@@",
        "fθ:X→y": "@@MAP@@",
        "fθ:X": "@@FTHETA@@",
        "where each xt contains": "where each @@XT@@ contains",
        "其中 xt 包含": "其中 @@XT@@ 包含",
        "30 x 3": "@@THIRTYBYTHREE@@",
        "30×3": "@@THIRTYBYTHREE@@",
        "±": "@@PM@@",
        "→": "@@ARROW@@",
        "×": "@@TIMES@@",
    }
    for source, marker in markers.items():
        text = text.replace(source, marker)
    text = text.replace("–", "--").replace("—", "---")
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
    text = "".join(repl.get(ch, ch) for ch in text)
    return (
        text.replace("@@SEQ@@", r"$X=[x_1,\ldots,x_T]$")
        .replace("@@T30@@", r"$T=30$")
        .replace("@@MAP@@", r"$f_\theta:X\rightarrow y$")
        .replace("@@FTHETA@@", r"$f_\theta:X$")
        .replace("@@XT@@", r"$x_t$")
        .replace("@@THIRTYBYTHREE@@", r"$30\times3$")
        .replace("@@PM@@", r"$\pm$")
        .replace("@@ARROW@@", r"$\rightarrow$")
        .replace("@@TIMES@@", r"$\times$")
        .replace("ZZREFTABMAIN40ENZZ", r"~\ref{tab:main40-en}")
        .replace("ZZREFTABMAIN60ENZZ", r"~\ref{tab:main60-en}")
        .replace("ZZREFTABABLATIONENZZ", r"~\ref{tab:ablation-en}")
        .replace("ZZREFFIGABLATIONENZZ", r"~\ref{fig:ablation-macro-f1-en}")
        .replace("ZZREFTABEFFICIENCYENZZ", r"~\ref{tab:efficiency-en}")
        .replace("ZZREFTABTRANSFERENZZ", r"~\ref{tab:transfer-en}")
        .replace("ZZREFFIGTRANSFERENZZ", r"~\ref{fig:transfer-macro-f1-en}")
        .replace("ZZREFFIGHSTAENZZ", r"~\ref{fig:hsta-en}")
        .replace("ZZREFTABDATASETENZZ", r"~\ref{tab:dataset-en}")
        .replace("ZZREFTABADAPTEDENZZ", r"~\ref{tab:adapted-baselines-en}")
        .replace("ZZREFFIGMAINENZZ", r"~\ref{fig:main-macro-f1-en}")
        .replace("ZZREFTABSCALINGENZZ", r"~\ref{tab:scaling-en}")
        .replace("ZZREFTABDEPTHENZZ", r"~\ref{tab:depth-en}")
        .replace("ZZREFTABCONFUSIONENZZ", r"~\ref{tab:confusion-en}")
        .replace("ZZREFTABMAIN40CNZZ", r"~\ref{tab:main40-cn}")
        .replace("ZZREFTABMAIN60CNZZ", r"~\ref{tab:main60-cn}")
        .replace("ZZREFTABABLATIONCNZZ", r"~\ref{tab:ablation-cn}")
        .replace("ZZREFFIGABLATIONCNZZ", r"~\ref{fig:ablation-macro-f1-cn}")
        .replace("ZZREFTABEFFICIENCYCNZZ", r"~\ref{tab:efficiency-cn}")
        .replace("ZZREFTABTRANSFERCNZZ", r"~\ref{tab:transfer-cn}")
        .replace("ZZREFFIGTRANSFERCNZZ", r"~\ref{fig:transfer-macro-f1-cn}")
        .replace("ZZREFFIGHSTACNZZ", r"~\ref{fig:hsta-cn}")
        .replace("ZZREFTABDATASETCNZZ", r"~\ref{tab:dataset-cn}")
        .replace("ZZREFTABADAPTEDCNZZ", r"~\ref{tab:adapted-baselines-cn}")
        .replace("ZZREFFIGMAINCNZZ", r"~\ref{fig:main-macro-f1-cn}")
        .replace("ZZREFTABSCALINGCNZZ", r"~\ref{tab:scaling-cn}")
        .replace("ZZREFTABDEPTHCNZZ", r"~\ref{tab:depth-cn}")
        .replace("ZZREFTABCONFUSIONCNZZ", r"~\ref{tab:confusion-cn}")
    )


def table_tex(rows: list[list[str]], caption: str, label: str, note: str | None = None) -> str:
    rows = [[tex_escape(cell) for cell in row] for row in rows]
    n_cols = len(rows[0])
    body = [" & ".join(row) + r" \\" for row in rows[1:]]
    has_long_text = max(len(cell) for row in rows for cell in row) > 70
    if n_cols == 3 and has_long_text:
        align = r"p{0.21\linewidth}p{0.24\linewidth}>{\raggedright\arraybackslash}X"
        tabular = "\n".join(
            [
                rf"\begin{{tabularx}}{{\linewidth}}{{{align}}}",
                r"\toprule",
                " & ".join(rows[0]) + r" \\",
                r"\midrule",
                *body,
                r"\bottomrule",
                r"\end{tabularx}",
            ]
        )
    else:
        align = "l" + "c" * (n_cols - 1)
        tabular = "\n".join(
            [
                rf"\begin{{tabular}}{{{align}}}",
                r"\toprule",
                " & ".join(rows[0]) + r" \\",
                r"\midrule",
                *body,
                r"\bottomrule",
                r"\end{tabular}",
            ]
        )
    if n_cols >= 5:
        tabular = "\\resizebox{\\linewidth}{!}{%\n" + tabular + "\n}"
    parts = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        rf"\caption{{{tex_escape(caption)}}}",
        rf"\label{{{label}}}",
        tabular,
    ]
    if note:
        parts.append(rf"\begin{{flushleft}}\footnotesize {tex_escape(note)}\end{{flushleft}}")
    parts.append(r"\end{table}")
    return "\n".join(parts)


def long_table_tex(rows: list[list[str]], caption: str, label: str) -> str:
    rows = [[tex_escape(cell) for cell in row] for row in rows]
    if len(rows[0]) == 4:
        align = r"@{}p{0.11\linewidth}p{0.34\linewidth}p{0.11\linewidth}p{0.34\linewidth}@{}"
    else:
        align = "l" * len(rows[0])
    body = [" & ".join(row) + r" \\" for row in rows[1:]]
    return "\n".join(
        [
            r"{\scriptsize",
            rf"\begin{{longtable}}{{{align}}}",
            rf"\caption{{{tex_escape(caption)}}}\label{{{label}}}\\",
            r"\toprule",
            " & ".join(rows[0]) + r" \\",
            r"\midrule",
            r"\endfirsthead",
            r"\toprule",
            " & ".join(rows[0]) + r" \\",
            r"\midrule",
            r"\endhead",
            *body,
            r"\bottomrule",
            r"\end{longtable}",
            r"}",
        ]
    )


def cn_main_rows(src) -> tuple[list[list[str]], list[list[str]]]:
    rows40, rows60 = src.build_main_result_tables()
    rows40 = [row.copy() for row in rows40]
    rows60 = [row.copy() for row in rows60]
    rows40[0] = ["模型", "QUIC-40 Acc", "QUIC-40 Macro-F1", "TLS-40 Acc", "TLS-40 Macro-F1"]
    rows60[0] = ["模型", "QUIC-60 Acc", "QUIC-60 Macro-F1", "TLS-60 Acc", "TLS-60 Macro-F1"]
    rows40[-1][0] = "HSTA-Hybrid（本文）"
    rows60[-1][0] = "HSTA-Hybrid（本文）"
    return rows40, rows60


def en_main_rows(src) -> tuple[list[list[str]], list[list[str]]]:
    rows40, rows60 = src.build_main_result_tables()
    rows40 = [row.copy() for row in rows40]
    rows60 = [row.copy() for row in rows60]
    rows40[-1][0] = "HSTA-Hybrid (Proposed)"
    rows60[-1][0] = "HSTA-Hybrid (Proposed)"
    return rows40, rows60


def cn_scaling_rows(src) -> list[list[str]]:
    rows = src.build_scaling_table()
    rows[0] = ["协议", "40 类", "60 类", "变化（百分点）"]
    return rows


def cn_ablation_rows(src) -> list[list[str]]:
    rows = src.build_ablation_table()
    rows[0] = ["结构变体", "QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]
    mapping = {
        "No Attention": "无注意力",
        "Attention-front": "前置注意力",
        "Attention-middle": "中间注意力",
        "HSTA-Hybrid (Proposed)": "HSTA-Hybrid（本文）",
    }
    for row in rows[1:]:
        row[0] = mapping.get(row[0], row[0])
    return rows


def cn_efficiency_rows(src) -> list[list[str]]:
    rows = src.build_efficiency_table()
    rows[0] = ["模型", "Batch", "参数量(M)", "GFLOPs/样本", "延迟(ms)", "吞吐(samples/s)", "峰值显存(MB)"]
    return rows


def cn_depth_rows(src) -> list[list[str]]:
    rows = src.build_depth_table()
    rows[0] = ["堆叠深度 N", "结构说明", "QUIC-40", "QUIC-60", "TLS-40", "TLS-60"]
    mapping = {
        "Main model (1×HSTA)": "主模型（1×HSTA）",
        "2×HSTA Blocks": "2×HSTA Block",
        "4×HSTA Blocks": "4×HSTA Block",
    }
    for row in rows[1:]:
        row[1] = mapping.get(row[1], row[1])
    return rows


def cn_transfer_rows(src) -> list[list[str]]:
    rows = src.build_transfer_table()
    rows[0] = ["迁移方向", "Zero-shot Acc", "重叠类 F1", "LoRA F1", "LoRA 参数(%)", "Full FT F1", "从头训练 F1", "FT-从头训练"]
    return rows


def en_dataset_rows(src) -> list[list[str]]:
    return src.translate_header_rows(src.source_tables()[1])


def en_adapted_rows(src) -> list[list[str]]:
    return src.translate_header_rows(src.source_tables()[2])


def en_confusion_rows(src) -> list[list[str]]:
    return src.translate_header_rows(src.extract_confusion_table())


def en_appendix_rows(src, index: int) -> list[list[str]]:
    return src.translate_header_rows(src.source_tables()[index])


def en_scaling_rows(src) -> list[list[str]]:
    return src.build_scaling_table()


def en_ablation_rows(src) -> list[list[str]]:
    return src.build_ablation_table()


def en_efficiency_rows(src) -> list[list[str]]:
    return src.build_efficiency_table()


def en_depth_rows(src) -> list[list[str]]:
    return src.build_depth_table()


def en_transfer_rows(src) -> list[list[str]]:
    return src.build_transfer_table()


def hsta_tikz_cn() -> str:
    return r"""\begin{figure}[!htbp]
\centering
\includegraphics[width=0.92\linewidth]{figures/fig1_hsta_architecture.png}
\caption{HSTA Block 的五阶段混合特征提取流程。}
\label{fig:hsta-cn}
\end{figure}"""


def figure_tex(filename: str, caption: str, label: str) -> str:
    return "\n".join(
        [
            r"\begin{figure}[!htbp]",
            r"\centering",
            rf"\includegraphics[width=0.92\linewidth]{{figures/{filename}}}",
            rf"\caption{{{tex_escape(caption)}}}",
            rf"\label{{{label}}}",
            r"\end{figure}",
        ]
    )


def references_tex() -> str:
    lines = [r"\begin{thebibliography}{99}"]
    for key, ref in REF_ITEMS:
        lines.append(rf"\bibitem{{{key}}} {tex_escape(ref)}")
    lines.append(r"\end{thebibliography}")
    return "\n".join(lines)


def add_refs_to_english_results(text: str) -> str:
    text = text.replace(
        "The main results show that HSTA-Hybrid achieves the best average Macro-F1 on all four tasks.",
        r"As shown in Tables~\ref{tab:main40-en} and~\ref{tab:main60-en}, HSTA-Hybrid achieves the best average Macro-F1 on all four tasks.",
    )
    text = text.replace(
        "The attention-position ablation confirms that the gain is not caused by simply adding an attention layer.",
        r"The attention-position ablation in Table~\ref{tab:ablation-en} and Figure~\ref{fig:ablation-macro-f1-en} confirms that the gain is not caused by simply adding an attention layer.",
    )
    text = text.replace(
        "The attention-position ablation is the main mechanism test.",
        r"The attention-position ablation in Table~\ref{tab:ablation-en} and Figure~\ref{fig:ablation-macro-f1-en} is the main mechanism test.",
    )
    text = text.replace(
        "The attention-position ablation is the main mechanism test and acts as a negative control for a simple ``attention always helps'' explanation.",
        r"The attention-position ablation in Table~\ref{tab:ablation-en} and Figure~\ref{fig:ablation-macro-f1-en} is the main mechanism test and acts as a negative control for a simple ``attention always helps'' explanation.",
    )
    text = text.replace(
        "Complexity and efficiency measurements further show that HSTA-Hybrid has fewer parameters than Transformer and offers a favorable performance-efficiency trade-off for small and medium batch inference.",
        r"Complexity and efficiency measurements in Table~\ref{tab:efficiency-en} further show that HSTA-Hybrid has fewer parameters than Transformer and offers a favorable performance-efficiency trade-off for small and medium batch inference.",
    )
    text = text.replace(
        "Cross-protocol transfer results show that direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior.",
        r"Cross-protocol transfer results in Table~\ref{tab:transfer-en} and Figure~\ref{fig:transfer-macro-f1-en} show that direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior.",
    )
    text = text.replace(
        "Cross-protocol transfer is evaluated as a stress test of representation reuse rather than as a claim of protocol-invariant classification. Direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior.",
        r"Cross-protocol transfer in Table~\ref{tab:transfer-en} and Figure~\ref{fig:transfer-macro-f1-en} is evaluated as a stress test of representation reuse rather than as a claim of protocol-invariant classification. Direct zero-shot transfer is ineffective, indicating substantial differences between QUIC and TLS in both class overlap and protocol behavior.",
    )
    return text


def add_refs_to_english_paragraph(title: str, index: int, text: str) -> str:
    if title == "4 Proposed Method" and index == 0:
        return text + r" Figure~\ref{fig:hsta-en} summarizes the resulting HSTA feature extraction pipeline."
    if title == "5 Experimental Setup" and index == 0:
        return text + r" Table~\ref{tab:dataset-en} summarizes the four datasets and task settings."
    if title == "5 Experimental Setup" and index == 1:
        return text + r" Table~\ref{tab:adapted-baselines-en} states how the adapted advanced baselines are constrained under the unified input setting."
    if title == "6 Results and Analysis":
        text = add_refs_to_english_results(text)
        if index == 0:
            text += r" Figure~\ref{fig:main-macro-f1-en} visualizes the Macro-F1 comparison across the four tasks."
        elif index == 1:
            text += r" Table~\ref{tab:scaling-en} reports the corresponding 40-to-60-class performance changes."
        elif index == 2:
            text += r" Table~\ref{tab:depth-en} reports the depth-sensitivity comparison."
    if title == "7 Discussion" and index == 0:
        return text + r" The class-level confusion cases in Table~\ref{tab:confusion-en} further illustrate where the remaining errors concentrate."
    return text


def add_refs_to_chinese_results(text: str) -> str:
    text = text.replace(
        "主实验结果表明，HSTA-Hybrid 在四个任务上均取得最高平均 Macro-F1。",
        r"如表~\ref{tab:main40-cn} 和表~\ref{tab:main60-cn} 所示，HSTA-Hybrid 在四个任务上均取得最高平均 Macro-F1。",
    )
    text = text.replace(
        "注意力位置消融实验表明，性能增益并不是简单增加注意力层所带来的。",
        r"表~\ref{tab:ablation-cn} 和图~\ref{fig:ablation-macro-f1-cn} 的注意力位置消融实验表明，性能增益并不是简单增加注意力层所带来的。",
    )
    text = text.replace(
        "复杂度和效率结果进一步表明，HSTA-Hybrid 的参数量低于 Transformer，并在小批量和中等批量推理中保持较好的性能效率折中。",
        r"表~\ref{tab:efficiency-cn} 的复杂度和效率结果进一步表明，HSTA-Hybrid 的参数量低于 Transformer，并在小批量和中等批量推理中保持较好的性能效率折中。",
    )
    text = text.replace(
        "跨协议迁移结果表明，直接 zero-shot 迁移效果很弱，说明 QUIC 与 TLS 在类别重叠和协议行为上存在显著差异。",
        r"表~\ref{tab:transfer-cn} 和图~\ref{fig:transfer-macro-f1-cn} 的跨协议迁移结果表明，直接 zero-shot 迁移效果很弱，说明 QUIC 与 TLS 在类别重叠和协议行为上存在显著差异。",
    )
    return text


def add_refs_to_chinese_paragraph(title: str, index: int, text: str) -> str:
    if title == "4 所提方法" and index == 0:
        return text + r" 图~\ref{fig:hsta-cn} 概括了 HSTA 的特征提取流程。"
    if title == "5 实验设置" and index == 0:
        return text + r" 表~\ref{tab:dataset-cn} 汇总了四个数据集与任务设置。"
    if title == "5 实验设置" and index == 1:
        return text + r" 表~\ref{tab:adapted-baselines-cn} 说明了统一输入设置下适配先进基线的约束。"
    if title == "6 结果与分析":
        text = add_refs_to_chinese_results(text)
        if index == 0:
            text += r" 图~\ref{fig:main-macro-f1-cn} 展示了四个任务上的 Macro-F1 对比。"
        elif index == 1:
            text += r" 表~\ref{tab:scaling-cn} 给出了从 40 类扩展到 60 类时的性能变化。"
        elif index == 2:
            text += r" 表~\ref{tab:depth-cn} 给出了 HSTA Block 深度敏感性比较。"
    if title == "7 讨论" and index == 0:
        return text + r" 表~\ref{tab:confusion-cn} 的类别混淆案例进一步展示了剩余错误的集中位置。"
    return text


def write_english_tex(src) -> None:
    sections = {title: paras for title, paras in src.EN_SECTIONS}
    rows40, rows60 = en_main_rows(src)
    abstract = "\n\n".join(tex_escape(p) for p in sections["Abstract"])
    keywords = tex_escape(sections["Keywords"][0])
    highlights = "\n".join(rf"\item {tex_escape(item)}" for item in sections["Highlights"])

    def paragraphs(title: str, cites: dict[int, str] | None = None) -> str:
        cites = cites or {}
        lines: list[str] = []
        for index, para in enumerate(sections[title]):
            para = add_refs_to_english_paragraph(title, index, para)
            lines.append(tex_escape(para) + cites.get(index, ""))
            lines.append("")
        return "\n".join(lines).strip()

    body = rf"""% !TeX program = pdflatex
% Default English JNCA/Elsevier manuscript. Overleaf can compile this with pdfLaTeX.
\documentclass[preprint,12pt]{{elsarticle}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{tabularx}}
\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb}}
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
{abstract}
\end{{abstract}}

\begin{{highlights}}
{highlights}
\end{{highlights}}

\begin{{keyword}}
{keywords.replace('; ', r' \sep ')}
\end{{keyword}}
\end{{frontmatter}}

\linenumbers

\section{{Introduction}}
{paragraphs("1 Introduction", {0: r"~\cite{rescorla2018tls,iyengar2021quic,wang2023twophase,kattadige2021seta}", 1: r"~\cite{azab2024traffic,sharma2025encrypted,wickramasinghe2025sok,zhou2025trafficformer,aceto2019mobile,aceto2021distiller,malekghaini2023drift,zhao2025sweet,shapira2021flowpic,wang2023twophase,chen2024multiflow,kattadige2021seta,li2025satnet}"})}

\section{{Background and Related Work}}
{paragraphs("2 Background and Related Work", {0: r"~\cite{azab2024traffic,sharma2025encrypted,papadogiannaki2022survey,aceto2019mobile,aceto2021distiller,lin2023multimodal,shapira2021flowpic,chen2024multiflow,li2025satnet}", 1: r"~\cite{luxemburk2023tls,luxemburk2023quic22,luxemburk2023datazoo,gahtan2024quic,luxemburk2025embedding}", 2: r"~\cite{lotfollahi2020deep,zhao2022mtflowformer,zhao2023yatc,meng2022packet,li2023minority,lin2022etbert,zhou2025trafficformer,vaswani2017attention,dao2024ssm,gu2022s4,gu2023mamba,zhao2025sweet,shapira2021flowpic,wang2023twophase,li2025satnet}"})}

\section{{Problem Definition and Motivation}}
{paragraphs("3 Problem Definition and Motivation")}

\section{{Proposed Method}}
{paragraphs("4 Proposed Method")}

{figure_tex("fig1_hsta_architecture.png", "Five-stage hybrid feature extraction process of HSTA Block.", "fig:hsta-en")}

\section{{Experimental Setup}}
{paragraphs("5 Experimental Setup", {1: r"~\cite{wang2024netmamba}"})}

{table_tex(en_dataset_rows(src), "Dataset and task statistics.", "tab:dataset-en")}

{table_tex(en_adapted_rows(src), "Adapted advanced baselines under the unified input setting.", "tab:adapted-baselines-en")}

\section{{Results and Analysis}}
{paragraphs("6 Results and Analysis", {3: r"~\cite{hu2022lora}"})}

{table_tex(rows40, "Main results on 40-class tasks and adapted advanced baselines (%).", "tab:main40-en", "30pktTCNET-adapted and NetMamba-adapted are adapted to the same lightweight packet-level side-channel input.")}

{figure_tex("fig2_main_macro_f1.png", "Macro-F1 comparison of main models on four tasks.", "fig:main-macro-f1-en")}

{table_tex(rows60, "Main results on 60-class tasks and adapted advanced baselines (%).", "tab:main60-en", "30pktTCNET-adapted and NetMamba-adapted are adapted to the same lightweight packet-level side-channel input.")}

{table_tex(en_scaling_rows(src), "Performance change from 40 to 60 classes (Macro-F1, %).", "tab:scaling-en")}

{table_tex(en_ablation_rows(src), "Attention-position ablation results (Macro-F1, %).", "tab:ablation-en")}

{figure_tex("fig3_ablation_macro_f1.png", "Attention-position ablation comparison.", "fig:ablation-macro-f1-en")}

{table_tex(en_efficiency_rows(src), "Complexity and measured inference efficiency.", "tab:efficiency-en")}

{table_tex(en_depth_rows(src), "Depth sensitivity of HSTA Block (Macro-F1, %).", "tab:depth-en")}

{table_tex(en_transfer_rows(src), "Cross-protocol transfer results (%).", "tab:transfer-en")}

{figure_tex("fig4_transfer_macro_f1.png", "Cross-protocol adaptation comparison.", "fig:transfer-macro-f1-en")}

{table_tex(en_confusion_rows(src), "Major confused class pairs of HSTA-Hybrid.", "tab:confusion-en")}

\section{{Discussion}}
{paragraphs("7 Discussion", {2: r"~\cite{wickramasinghe2025sok,malekghaini2023drift,zhao2025sweet,chen2024multiflow,kattadige2021seta,xie2023rosetta}"})}

\section{{Threats to Validity}}
{paragraphs("8 Threats to Validity", {1: r"~\cite{hynek2024tlsyear,malekghaini2023drift,zhao2025sweet,xie2023rosetta}"})}

\section{{Conclusion}}
{paragraphs("9 Conclusion")}

\section*{{Declarations}}
\textbf{{Author contributions (CRediT):}} Author One: Conceptualization, Methodology, Software, Investigation, Writing - original draft; Author Two: Data curation, Validation, Formal analysis, Visualization; Author Three: Supervision, Writing - review and editing, Project administration. [placeholder; confirm final roles before submission]

\textbf{{Funding:}} Funding information is to be completed. [placeholder or state no funding]

\textbf{{Declaration of competing interest:}} The authors declare that they have no known competing financial interests or personal relationships that could have influenced the work reported in this paper. [to be confirmed by all authors]

\textbf{{Data and code availability:}} The experiments are based on CESNET-QUIC22, CESNET-TLS22, and DataZoo. Code and processing scripts are available in the project repository; the final link should be handled according to the journal's anonymous review or repository policy.

\textbf{{Acknowledgements:}} To be completed. [placeholder]

\bibliographystyle{{elsarticle-num}}
\bibliography{{references}}

\appendix
\section{{QUIC label-to-service mapping}}
{long_table_tex(en_appendix_rows(src, 11), "QUIC label-to-service mapping.", "tab:quic-map-en")}

\section{{TLS label-to-service mapping}}
{long_table_tex(en_appendix_rows(src, 12), "TLS label-to-service mapping.", "tab:tls-map-en")}

\end{{document}}
"""
    (OUT / "JNCA_HSTA_Encrypted_Traffic_EN.tex").write_text(body, encoding="utf-8")
    (OUT / "main.tex").write_text(body, encoding="utf-8")


def copy_support_files(overleaf_module) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    overleaf_module.main()
    overleaf_out = overleaf_module.OUT
    for name in ["references.bib", "elsarticle-num.bst"]:
        source = overleaf_out / name
        if source.exists():
            shutil.copy2(source, OUT / name)
    source_fig_dir = overleaf_out / "figures"
    for fig in source_fig_dir.glob("*.png"):
        shutil.copy2(fig, FIG_DIR / fig.name)


def write_chinese_tex(src) -> None:
    tables = src.source_tables()
    rows40, rows60 = cn_main_rows(src)
    sections = {title: paras for title, paras in src.CN_SECTIONS}
    abstract = "\n\n".join(tex_escape(p) for p in sections["摘要"])
    keywords = tex_escape(sections["关键词"][0])
    highlights = "\n".join(rf"\item {tex_escape(item)}" for item in sections["Highlights"])

    def paragraphs(title: str, cites: dict[int, str] | None = None) -> str:
        cites = cites or {}
        lines: list[str] = []
        for index, para in enumerate(sections[title]):
            para = add_refs_to_chinese_paragraph(title, index, para)
            lines.append(tex_escape(para) + cites.get(index, ""))
            lines.append("")
        return "\n".join(lines).strip()

    body = rf"""% !TeX program = xelatex
% Chinese companion manuscript. In Overleaf, switch compiler to XeLaTeX before compiling this file.
\documentclass[UTF8,a4paper,12pt]{{ctexart}}
\usepackage[margin=2.5cm]{{geometry}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{tabularx}}
\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb}}
\usepackage[section]{{placeins}}
\usepackage{{hyperref}}
\hypersetup{{colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue}}
\title{{面向轻量级加密 QUIC/TLS 流量分类的混合状态空间转换与注意力建模方法\\\large Hybrid State-Space Transition-Attention Modeling for Lightweight Encrypted QUIC/TLS Traffic Classification}}
\author{{Author One；Author Two；Author Three [占位，请替换]}}
\date{{}}

\begin{{document}}
\maketitle

\begin{{abstract}}
{abstract}
\end{{abstract}}

\noindent\textbf{{关键词：}}{keywords}

\section*{{Highlights}}
\begin{{itemize}}
{highlights}
\end{{itemize}}

\section{{引言}}
{paragraphs("1 引言", {0: r"~\cite{rescorla2018tls,iyengar2021quic}"})}

\section{{背景与相关工作}}
{paragraphs("2 背景与相关工作", {0: r"~\cite{azab2024traffic,sharma2025encrypted,papadogiannaki2022survey}", 1: r"~\cite{luxemburk2023tls,luxemburk2023quic22,luxemburk2023datazoo,gahtan2024quic,luxemburk2025embedding}", 2: r"~\cite{lotfollahi2020deep,zhao2022mtflowformer,zhao2023yatc,meng2022packet,li2023minority,lin2022etbert,zhou2025trafficformer,vaswani2017attention,dao2024ssm,gu2022s4,gu2023mamba}"})}

\section{{问题定义与方法动机}}
{paragraphs("3 问题定义与方法动机")}

\section{{所提方法}}
{paragraphs("4 所提方法")}

{hsta_tikz_cn()}

\section{{实验设置}}
{paragraphs("5 实验设置", {1: r"~\cite{wang2024netmamba}"})}

{table_tex(tables[1], "数据集和任务统计。", "tab:dataset-cn")}

{table_tex(tables[2], "统一输入设置下的适配先进结构基线。", "tab:adapted-baselines-cn")}

\section{{结果与分析}}
{paragraphs("6 结果与分析", {3: r"~\cite{hu2022lora}"})}

{table_tex(rows40, "40 类任务主实验与适配先进结构基线结果（单位：%）。", "tab:main40-cn", "30pktTCNET-adapted 和 NetMamba-adapted 均为统一轻量包级侧信道输入下的适配版本。")}

{figure_tex("fig2_main_macro_f1.png", "主要模型在四个任务上的 Macro-F1 对比。", "fig:main-macro-f1-cn")}

{table_tex(rows60, "60 类任务主实验与适配先进结构基线结果（单位：%）。", "tab:main60-cn", "30pktTCNET-adapted 和 NetMamba-adapted 均为统一轻量包级侧信道输入下的适配版本。")}

{table_tex(cn_scaling_rows(src), "HSTA-Hybrid 从 40 类到 60 类的性能变化（Macro-F1，单位：%）。", "tab:scaling-cn")}

{table_tex(cn_ablation_rows(src), "注意力位置消融实验结果（Macro-F1，单位：%）。", "tab:ablation-cn")}

{figure_tex("fig3_ablation_macro_f1.png", "注意力位置消融实验对比。", "fig:ablation-macro-f1-cn")}

{table_tex(cn_efficiency_rows(src), "核心模型与适配先进结构基线复杂度及推理效率。", "tab:efficiency-cn")}

{table_tex(cn_depth_rows(src), "HSTA Block 堆叠深度敏感性实验（Macro-F1，单位：%）。", "tab:depth-cn")}

{table_tex(cn_transfer_rows(src), "跨协议迁移结果总览（单位：%）。", "tab:transfer-cn")}

{figure_tex("fig4_transfer_macro_f1.png", "跨协议迁移结果对比。", "fig:transfer-macro-f1-cn")}

{table_tex(src.extract_confusion_table(), "HSTA-Hybrid 主要混淆类别对。", "tab:confusion-cn")}

\section{{讨论}}
{paragraphs("7 讨论", {2: r"~\cite{hynek2024tlsyear}"})}

\section{{结论}}
{paragraphs("8 结论")}

\section*{{声明}}
\textbf{{作者贡献（CRediT）：}}Author One：Conceptualization、Methodology、Software、Investigation、Writing - original draft；Author Two：Data curation、Validation、Formal analysis、Visualization；Author Three：Supervision、Writing - review and editing、Project administration。[占位，请投稿前确认最终角色]

\textbf{{资金支持：}}本研究资金支持信息待补充。[占位，请替换或写明无资金支持]

\textbf{{利益冲突：}}作者声明不存在已知竞争性经济利益或个人关系会影响本文工作。[占位，请作者确认]

\textbf{{数据和代码可用性：}}实验基于公开 CESNET-QUIC22、CESNET-TLS22 和 DataZoo；代码与处理脚本位于本项目仓库，提交前请按匿名审稿或公开仓库要求处理链接。

\textbf{{致谢：}}待补充。[占位]

\section*{{参考文献}}
{references_tex()}

\appendix
\section{{QUIC 标签编号与流量名称映射}}
{long_table_tex(tables[11], "QUIC 标签编号与流量名称映射。", "tab:quic-map-cn")}

\section{{TLS 标签编号与流量名称映射}}
{long_table_tex(tables[12], "TLS 标签编号与流量名称映射。", "tab:tls-map-cn")}

\end{{document}}
"""
    (OUT / "JNCA_HSTA_Encrypted_Traffic_CN.tex").write_text(body, encoding="utf-8")
    (OUT / "main_cn.tex").write_text(body, encoding="utf-8")


def write_readme() -> None:
    readme = """# JNCA Bilingual LaTeX Package

This folder contains the final bilingual LaTeX manuscript files requested for the JNCA-oriented SCI submission workflow.

Overleaf default:
- Compile `main.tex` first. It is the English JNCA/Elsevier manuscript and is intended to compile with pdfLaTeX.
- To compile the Chinese companion version, set `main_cn.tex` as the main file and switch the compiler to XeLaTeX.

Recommended upload packages:
- `paper/jnca_english_overleaf_package.zip`: upload this for the English JNCA submission draft. It contains only the English main file and support assets.
- `paper/jnca_chinese_xelatex_package.zip`: upload this only when checking the Chinese companion version, and use XeLaTeX.
- `paper/jnca_bilingual_latex_package.zip`: archival bilingual package; if Overleaf auto-selects the wrong main file, manually set `main.tex`.
Each specialized zip includes its own README and `latexmkrc` so Overleaf is less likely to choose the wrong compiler.

Files:
- `main.tex`: default English Overleaf entry file.
- `main_cn.tex`: Chinese Overleaf entry file; use XeLaTeX.
- `JNCA_HSTA_Encrypted_Traffic_EN.tex`: English JNCA/Elsevier LaTeX manuscript.
- `JNCA_HSTA_Encrypted_Traffic_CN.tex`: corresponding Chinese LaTeX manuscript.
- `figures/`: generated architecture and result figures shared by both versions.
- `references.bib` and `elsarticle-num.bst`: bibliography support for the English Elsevier manuscript.
- `elsarticle.cls`: not bundled here; expected from Overleaf or the submission-system TeX installation.

Recommended compilation:
- English: `pdflatex -> bibtex -> pdflatex -> pdflatex`, or upload the folder to Overleaf and set `main.tex` as the main file.
- Chinese: set `main_cn.tex` as the main file and use XeLaTeX because it uses `ctexart`.

Formatting notes:
- Result tables are generated from repository CSV summaries; do not hand-edit numerical values in the `.tex` files.
- Long explanation tables use fixed-width or `tabularx` columns to reduce overflow risk in Overleaf.
- Appendix label maps use compact long tables; move them to supplementary material if the target submission system prefers a shorter main manuscript.

Before submission:
- Replace author, affiliation, funding, acknowledgement, repository, and corresponding-author placeholders in both language versions.
- Replace the generated HSTA architecture PNG with the refined draw.io export if a polished journal figure is required.
- Compile both language versions and check table wrapping, figure placement, and references after metadata replacement.
- Run a final human proofread after author metadata and figure exports are finalized.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    (OUT / "latexmkrc").write_text("$pdf_mode = 1;\n", encoding="utf-8")


def write_zip(zip_path: Path, entries: list[tuple[Path, str]], text_entries: list[tuple[str, str]] | None = None) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for source, arcname in entries:
            if source.is_dir():
                for item in source.rglob("*"):
                    if item.is_file():
                        zf.write(item, str(Path(arcname) / item.relative_to(source)).replace("\\", "/"))
            else:
                zf.write(source, arcname.replace("\\", "/"))
        for arcname, content in text_entries or []:
            zf.writestr(arcname.replace("\\", "/"), content)


def flat_tex_for_editorial_manager(text: str) -> str:
    return text.replace("figures/", "")


def sync_submission_overleaf_folder() -> None:
    if SUBMISSION_OVERLEAF.exists():
        shutil.rmtree(SUBMISSION_OVERLEAF)
    SUBMISSION_OVERLEAF.mkdir(parents=True, exist_ok=True)
    for name in ["main.tex", "JNCA_HSTA_Encrypted_Traffic_EN.tex", "references.bib", "elsarticle-num.bst"]:
        shutil.copy2(OUT / name, SUBMISSION_OVERLEAF / name)
    shutil.copytree(OUT / "figures", SUBMISSION_OVERLEAF / "figures")
    readme = """# JNCA English Overleaf Package

Upload this folder or `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` to Overleaf for the English SCI/JNCA draft.

Overleaf settings:
- Main file: `main.tex`
- Compiler: pdfLaTeX
- Bibliography: BibTeX with `elsarticle-num.bst`

Package layout:
- Root files: `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, and `latexmkrc`.
- Figures are kept under `figures/`, and `main.tex` references the same `figures/...` paths.

Template dependency:
- `elsarticle-num.bst` is packaged from the official Elsevier template bundle.
- `elsarticle.cls` is expected from Overleaf or the submission-system TeX installation.
- Author affiliations use the legacy-compatible `\address[...]` form instead of newer structured `\affiliation[...]` fields.

Do not upload `JNCA_recommended_upload_bundle.zip` as an Overleaf project; it is a mixed handoff bundle. Do not upload `FIGURES_FOR_UPLOAD.zip` to compile the manuscript; it is only for separate artwork upload.
If `elsarticle.cls not found` appears, the platform TeX environment is missing the Elsevier class rather than the manuscript body being corrupted.
This package intentionally excludes the Chinese manuscript.
"""
    (SUBMISSION_OVERLEAF / "README.md").write_text(readme, encoding="utf-8")
    (SUBMISSION_OVERLEAF / "README_overleaf.md").write_text(readme, encoding="utf-8")
    (SUBMISSION_OVERLEAF / "latexmkrc").write_text("$pdf_mode = 1;\n", encoding="utf-8")
    (SUBMISSION_OVERLEAF / "figure_notes.md").write_text(
        "# Figure Notes\n\n"
        "- `main.tex` references generated PNG figures under `figures/` for Overleaf preview.\n"
        "- Replace Figure 1 with final draw.io artwork before formal submission if needed.\n"
        "- Figures 2, 3, and 4 are generated automatically from existing CSV summaries under `results/`.\n",
        encoding="utf-8",
    )
    (SUBMISSION_OVERLEAF / "FIGURE_BUILD_NOTE.txt").write_text(
        "Overleaf preview package. Use the flat Editorial Manager source zip for systems that reject subfolders.\n",
        encoding="utf-8",
    )
    write_zip(
        SUBMISSION_OVERLEAF_ZIP,
        [
            (SUBMISSION_OVERLEAF / "main.tex", "main.tex"),
            (SUBMISSION_OVERLEAF / "JNCA_HSTA_Encrypted_Traffic_EN.tex", "JNCA_HSTA_Encrypted_Traffic_EN.tex"),
            (SUBMISSION_OVERLEAF / "references.bib", "references.bib"),
            (SUBMISSION_OVERLEAF / "elsarticle-num.bst", "elsarticle-num.bst"),
            (SUBMISSION_OVERLEAF / "figures", "figures"),
            (SUBMISSION_OVERLEAF / "README.md", "README.md"),
            (SUBMISSION_OVERLEAF / "README_overleaf.md", "README_overleaf.md"),
            (SUBMISSION_OVERLEAF / "latexmkrc", "latexmkrc"),
            (SUBMISSION_OVERLEAF / "figure_notes.md", "figure_notes.md"),
            (SUBMISSION_OVERLEAF / "FIGURE_BUILD_NOTE.txt", "FIGURE_BUILD_NOTE.txt"),
        ],
    )


def write_editorial_manager_source_package() -> None:
    if EDITORIAL_SOURCE_DIR.exists():
        shutil.rmtree(EDITORIAL_SOURCE_DIR)
    EDITORIAL_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    main_text = flat_tex_for_editorial_manager((OUT / "main.tex").read_text(encoding="utf-8"))
    source_text = flat_tex_for_editorial_manager((OUT / "JNCA_HSTA_Encrypted_Traffic_EN.tex").read_text(encoding="utf-8"))
    (EDITORIAL_SOURCE_DIR / "main.tex").write_text(main_text, encoding="utf-8")
    (EDITORIAL_SOURCE_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.tex").write_text(source_text, encoding="utf-8")
    for name in ["references.bib", "elsarticle-num.bst"]:
        shutil.copy2(OUT / name, EDITORIAL_SOURCE_DIR / name)
    for fig in (OUT / "figures").glob("*.png"):
        shutil.copy2(fig, EDITORIAL_SOURCE_DIR / fig.name)
    readme = """# JNCA Editorial Manager LaTeX Source

This zip is the flat LaTeX source package for Elsevier/Editorial Manager-style upload systems that may reject subfolders.

Compile settings:
- Main file: `main.tex`
- Compiler: pdfLaTeX
- Bibliography: BibTeX with `elsarticle-num.bst`

Package layout:
- Root files: `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, and `latexmkrc`.
- Root figure files: `fig1_hsta_architecture.png`, `fig2_main_macro_f1.png`, `fig3_ablation_macro_f1.png`, and `fig4_transfer_macro_f1.png`.
- `main.tex` references the PNG figures directly from the zip root.

Template dependency:
- `elsarticle-num.bst` is packaged from the official Elsevier template bundle.
- `elsarticle.cls` is expected from the submission-system TeX installation.
- Author affiliations use the legacy-compatible `\address[...]` form instead of newer structured `\affiliation[...]` fields.

Use `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` for Overleaf preview/editing; use this flat source zip when the submission system asks for LaTeX source files. Do not upload `FIGURES_FOR_UPLOAD.zip` to compile the manuscript; it is only for separate artwork upload.
If `elsarticle.cls not found` appears, the platform TeX environment is missing the Elsevier class rather than the manuscript body being corrupted.
"""
    (EDITORIAL_SOURCE_DIR / "README.md").write_text(readme, encoding="utf-8")
    (EDITORIAL_SOURCE_DIR / "latexmkrc").write_text("$pdf_mode = 1;\n", encoding="utf-8")
    write_zip(
        EDITORIAL_SOURCE_ZIP,
        [
            (EDITORIAL_SOURCE_DIR / "main.tex", "main.tex"),
            (EDITORIAL_SOURCE_DIR / "JNCA_HSTA_Encrypted_Traffic_EN.tex", "JNCA_HSTA_Encrypted_Traffic_EN.tex"),
            (EDITORIAL_SOURCE_DIR / "references.bib", "references.bib"),
            (EDITORIAL_SOURCE_DIR / "elsarticle-num.bst", "elsarticle-num.bst"),
            (EDITORIAL_SOURCE_DIR / "fig1_hsta_architecture.png", "fig1_hsta_architecture.png"),
            (EDITORIAL_SOURCE_DIR / "fig2_main_macro_f1.png", "fig2_main_macro_f1.png"),
            (EDITORIAL_SOURCE_DIR / "fig3_ablation_macro_f1.png", "fig3_ablation_macro_f1.png"),
            (EDITORIAL_SOURCE_DIR / "fig4_transfer_macro_f1.png", "fig4_transfer_macro_f1.png"),
            (EDITORIAL_SOURCE_DIR / "README.md", "README.md"),
            (EDITORIAL_SOURCE_DIR / "latexmkrc", "latexmkrc"),
        ],
    )


def write_specialized_packages() -> None:
    figures = OUT / "figures"
    english_readme = """# JNCA English Overleaf Package

Upload this zip when preparing the English JNCA submission draft.

The same direct-import package is also copied to `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` when the submission package is regenerated. Use that clearly named copy if you are working from the submission folder.

Overleaf settings:
- Main file: `main.tex`
- Compiler: pdfLaTeX
- Bibliography: BibTeX with `elsarticle-num.bst`

Package layout:
- Root files: `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, and `latexmkrc`.
- Figures are kept under `figures/`, and `main.tex` references the same `figures/...` paths.

Template dependency:
- `elsarticle-num.bst` is packaged from the official Elsevier template bundle.
- `elsarticle.cls` is expected from Overleaf or the submission-system TeX installation.
- Author affiliations use the legacy-compatible `\address[...]` form instead of newer structured `\affiliation[...]` fields.

Do not upload `JNCA_recommended_upload_bundle.zip` as an Overleaf project; it is a mixed handoff bundle. Do not upload `FIGURES_FOR_UPLOAD.zip` to compile the manuscript; it is only for separate artwork upload.
If `elsarticle.cls not found` appears, the platform TeX environment is missing the Elsevier class rather than the manuscript body being corrupted.
This package intentionally excludes the Chinese manuscript so that Overleaf will not auto-select a `ctexart` file and compile it with pdfLaTeX.

Included figures:
- `figures/fig1_hsta_architecture.png`: generated HSTA architecture overview.
- `figures/fig2_main_macro_f1.png`, `figures/fig3_ablation_macro_f1.png`, and `figures/fig4_transfer_macro_f1.png`: generated result figures from repository CSV summaries.

Before submission:
- Replace author, affiliation, email, funding, acknowledgement, repository, and contribution placeholders.
- Replace Figure 1 with the polished draw.io export if final journal artwork is required.
- Compile at least twice after BibTeX and check figure placement, table wrapping, and references.
"""
    chinese_readme = """# JNCA Chinese XeLaTeX Package

Upload this zip only when checking the Chinese companion manuscript.

Overleaf settings:
- Main file: `main.tex`
- Compiler: XeLaTeX
- Bibliography: embedded `thebibliography`; BibTeX is not required.

If Overleaf reports many Chinese-character or `ctexart` errors, the compiler is almost certainly still set to pdfLaTeX. Switch it to XeLaTeX and recompile.

Figure 1 is included as a generated PNG for stable preview; replace it with polished draw.io artwork before final submission if needed.
"""
    write_zip(
        ENGLISH_ZIP,
        [
            (OUT / "main.tex", "main.tex"),
            (OUT / "JNCA_HSTA_Encrypted_Traffic_EN.tex", "JNCA_HSTA_Encrypted_Traffic_EN.tex"),
            (OUT / "references.bib", "references.bib"),
            (OUT / "elsarticle-num.bst", "elsarticle-num.bst"),
            (figures, "figures"),
        ],
        text_entries=[
            ("README.md", english_readme),
            ("latexmkrc", "$pdf_mode = 1;\n"),
        ],
    )
    write_zip(
        CHINESE_ZIP,
        [
            (OUT / "main_cn.tex", "main.tex"),
            (OUT / "JNCA_HSTA_Encrypted_Traffic_CN.tex", "JNCA_HSTA_Encrypted_Traffic_CN.tex"),
            (figures, "figures"),
        ],
        text_entries=[
            ("README.md", chinese_readme),
            ("latexmkrc", "$pdf_mode = 5;\n"),
        ],
    )
    sync_submission_overleaf_folder()
    write_editorial_manager_source_package()


def main() -> None:
    src = load_module(SUBMISSION_SCRIPT, "generate_jnca_submission")
    overleaf = load_module(OVERLEAF_SCRIPT, "generate_jnca_overleaf")
    if OUT.exists():
        shutil.rmtree(OUT)
    copy_support_files(overleaf)
    write_english_tex(src)
    write_chinese_tex(src)
    write_readme()
    if COMBINED_ZIP.exists():
        COMBINED_ZIP.unlink()
    shutil.make_archive(str(COMBINED_ZIP.with_suffix("")), "zip", OUT)
    write_specialized_packages()
    print(OUT)
    print(OUT / "JNCA_HSTA_Encrypted_Traffic_EN.tex")
    print(OUT / "JNCA_HSTA_Encrypted_Traffic_CN.tex")
    print(COMBINED_ZIP)
    print(ENGLISH_ZIP)
    print(CHINESE_ZIP)


if __name__ == "__main__":
    main()
