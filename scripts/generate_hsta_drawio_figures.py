from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


TASKS = ("QUIC-40", "QUIC-60", "TLS-40", "TLS-60")
TASK_DIRS = {
    "QUIC-40": "quic40_s",
    "QUIC-60": "quic60_s",
    "TLS-40": "tls40_s",
    "TLS-60": "tls60_s",
}
TRANSFER_TASKS = (
    "QUIC to TLS-40",
    "TLS to QUIC-40",
    "QUIC to TLS-60",
    "TLS to QUIC-60",
)
TRANSFER_IDS = {
    "QUIC to TLS-40": "quic_to_tls40_s",
    "TLS to QUIC-40": "tls_to_quic40_s",
    "QUIC to TLS-60": "quic_to_tls60_s",
    "TLS to QUIC-60": "tls_to_quic60_s",
}
PAGE_NAMES = [
    "01 Architecture",
    "02 Main Macro-F1",
    "03 Attention Ablation",
    "04 Parameter Performance",
    "05 Cross-Protocol Transfer",
    "06 Confusion Patterns",
    "07 Data Processing",
]
OUTPUT_FILENAMES = [
    "fig1_hsta_architecture.png",
    "fig2_main_macro_f1.png",
    "fig3_attention_position_ablation.png",
    "fig4_parameter_performance.png",
    "fig5_cross_protocol_transfer.png",
    "fig6_confusion_patterns.png",
    "fig7_data_processing_pipeline.png",
]
GRAPHICAL_ABSTRACT_FILENAME = "graphical_abstract_hsta.png"

CHARCOAL = "35414A"
MID_GRAY = "AEB6BD"
LIGHT_GRAY = "F4F6F7"
BLUE = "3F78A3"
SOFT_BLUE = "DCEBF6"
VIOLET = "7C6A96"
SOFT_VIOLET = "F2EDF7"
GREEN = "6F9477"
SOFT_GREEN = "E8F1EA"
ORANGE = "D87935"
SOFT_ORANGE = "FFF3E8"
TEAL = "4F8C86"
ERROR_GRAY = "66717A"
WHITE = "FFFFFF"


@dataclass(frozen=True)
class ConfusionData:
    class_ids: list[str]
    class_names: list[str]
    matrix: list[list[int]]


@dataclass(frozen=True)
class FigureData:
    main: dict[str, dict[str, tuple[float, float | None]]]
    ablation: dict[str, dict[str, tuple[float, float]]]
    transfer: dict[str, dict[str, float]]
    parameters: dict[str, float]
    confusion: dict[str, ConfusionData]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _percent(values: list[float]) -> tuple[float, float | None]:
    if not values:
        raise ValueError("Expected at least one metric value")
    scaled = [value * 100.0 for value in values]
    mean = round(statistics.mean(scaled), 2)
    std = round(statistics.stdev(scaled), 2) if len(scaled) > 1 else None
    return mean, std


def _metric(rows: list[dict[str, str]], predicate, column: str = "test_macro_f1") -> tuple[float, float | None]:
    values = [float(row[column]) for row in rows if predicate(row) and row.get(column, "")]
    return _percent(values)


def _service_names(project_root: Path) -> dict[str, str]:
    path = project_root / "data" / "raw" / "cesnet_quic22_datazoo" / "S" / "servicemap.csv"
    if not path.exists():
        return {}
    return {str(index): row.get("Service", str(index)) for index, row in enumerate(_read_csv(path))}


def _load_confusion(project_root: Path, task_dir: str, count: int) -> ConfusionData:
    path = (
        project_root
        / "results"
        / task_dir
        / f"hybrid_mm_mlp_a_mlp_{task_dir}_seed42"
        / "metrics.json"
    )
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    class_ids = [str(value) for value in payload["classes"]]
    matrix = [[int(value) for value in row] for row in payload["confusion_matrix"]]
    if len(class_ids) != count or len(matrix) != count or any(len(row) != count for row in matrix):
        raise ValueError(f"Unexpected confusion dimensions in {path}")
    names = _service_names(project_root)
    return ConfusionData(class_ids, [names.get(value, value) for value in class_ids], matrix)


def load_figure_data(project_root: Path) -> FigureData:
    project_root = Path(project_root).resolve()
    result_root = project_root / "results"
    main: dict[str, dict[str, tuple[float, float | None]]] = {
        name: {} for name in ("GRU", "Transformer", "30pktTCNET", "NetMamba", "HSTA")
    }
    sota_rows = _read_csv(result_root / "sota_adapted" / "all_results.csv")
    for task, task_dir in TASK_DIRS.items():
        rows = _read_csv(result_root / task_dir / "all_results.csv")
        main["GRU"][task] = _metric(rows, lambda row: row.get("exp_name") == f"gru_5layer_{task_dir}")
        main["Transformer"][task] = _metric(
            rows,
            lambda row: row.get("exp_name", "").startswith(f"transformer_5layer_{task_dir}_seed"),
        )
        main["HSTA"][task] = _metric(
            rows,
            lambda row: row.get("exp_name", "").startswith(f"hybrid_mm_mlp_a_mlp_{task_dir}_seed"),
        )
        main["30pktTCNET"][task] = _metric(
            sota_rows,
            lambda row, td=task_dir: row.get("exp_name", "").startswith(f"30pkttcnet_adapted_{td}_seed"),
        )
        main["NetMamba"][task] = _metric(
            sota_rows,
            lambda row, td=task_dir: row.get("exp_name", "").startswith(f"netmamba_adapted_{td}_seed"),
        )

    ablation_rows = _read_csv(result_root / "ablation_s" / "all_results.csv")
    ablation_prefixes = {
        "No attention": "ablation_no_attention",
        "Front attention": "ablation_attention_front",
        "Middle attention": "ablation_attention_middle",
    }
    ablation: dict[str, dict[str, tuple[float, float]]] = {name: {} for name in (*ablation_prefixes, "HSTA")}
    for label, prefix in ablation_prefixes.items():
        for task, task_dir in TASK_DIRS.items():
            value = _metric(
                ablation_rows,
                lambda row, p=prefix, td=task_dir: row.get("exp_name", "").startswith(f"{p}_{td}_seed"),
            )
            if value[1] is None:
                raise ValueError(f"Ablation series {label}/{task} requires multiple seeds")
            ablation[label][task] = (value[0], value[1])
    for task in TASKS:
        value = main["HSTA"][task]
        if value[1] is None:
            raise ValueError(f"HSTA series {task} requires multiple seeds")
        ablation["HSTA"][task] = (value[0], value[1])

    transfer_rows = _read_csv(result_root / "transfer_s" / "all_results.csv")
    transfer: dict[str, dict[str, float]] = {
        name: {} for name in ("Zero-shot", "LoRA", "Full fine-tuning", "Target scratch")
    }
    target_task = {
        "QUIC to TLS-40": "TLS-40",
        "TLS to QUIC-40": "QUIC-40",
        "QUIC to TLS-60": "TLS-60",
        "TLS to QUIC-60": "QUIC-60",
    }
    for label in TRANSFER_TASKS:
        ident = TRANSFER_IDS[label]
        row_by_name = {row["exp_name"]: row for row in transfer_rows}
        transfer["Zero-shot"][label] = round(float(row_by_name[f"zero_shot_{ident}"]["covered_macro_f1"]) * 100, 2)
        transfer["LoRA"][label] = round(float(row_by_name[f"hybrid_lora_{ident}"]["test_macro_f1"]) * 100, 2)
        transfer["Full fine-tuning"][label] = round(float(row_by_name[f"full_ft_{ident}"]["test_macro_f1"]) * 100, 2)
        transfer["Target scratch"][label] = main["HSTA"][target_task[label]][0]

    efficiency_rows = _read_csv(result_root / "efficiency_benchmark" / "summary.csv")
    parameter_match = {
        "GRU": lambda row: row.get("exp_name") == "gru_5layer_quic40_s",
        "Transformer": lambda row: row.get("exp_name") == "transformer_5layer_quic40_s_seed42",
        "30pktTCNET": lambda row: row.get("exp_name") == "30pkttcnet_adapted_quic40_s_seed42",
        "NetMamba": lambda row: row.get("exp_name") == "netmamba_adapted_quic40_s_seed42",
        "HSTA": lambda row: row.get("exp_name") == "hybrid_mm_mlp_a_mlp_quic40_s_seed42",
    }
    parameters: dict[str, float] = {}
    for label, predicate in parameter_match.items():
        matches = [row for row in efficiency_rows if predicate(row)]
        values = {round(float(row["parameters_m"]), 6) for row in matches}
        if len(values) != 1:
            raise ValueError(f"Expected one unique parameter value for {label}, found {sorted(values)}")
        parameters[label] = values.pop()

    confusion = {
        "QUIC-40": _load_confusion(project_root, "quic40_s", 40),
        "QUIC-60": _load_confusion(project_root, "quic60_s", 60),
    }
    return FigureData(main, ablation, transfer, parameters, confusion)


def _style(**parts) -> str:
    return ";".join(f"{key}={value}" for key, value in parts.items()) + ";"


def _box_style(fill: str, stroke: str = CHARCOAL, font_size: int = 16, rounded: int = 1, bold: bool = False) -> str:
    return _style(
        rounded=rounded,
        whiteSpace="wrap",
        html=1,
        fillColor=f"#{fill}",
        strokeColor=f"#{stroke}",
        strokeWidth=2,
        fontColor=f"#{CHARCOAL}",
        fontFamily="Arial",
        fontSize=font_size,
        fontStyle=1 if bold else 0,
        align="center",
        verticalAlign="middle",
        arcSize=8,
    )


def _text_style(font_size: int = 16, color: str = CHARCOAL, bold: bool = False, align: str = "center") -> str:
    return _style(
        text=1,
        strokeColor="none",
        fillColor="none",
        html=1,
        whiteSpace="wrap",
        overflow="hidden",
        fontColor=f"#{color}",
        fontFamily="Arial",
        fontSize=font_size,
        fontStyle=1 if bold else 0,
        align=align,
        verticalAlign="middle",
    )


class Page:
    def __init__(self, name: str, width: int, height: int):
        self.name = name
        self.width = width
        self.height = height
        self.counter = 2
        self.model = ET.Element(
            "mxGraphModel",
            {
                "dx": "1200",
                "dy": "800",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": str(width),
                "pageHeight": str(height),
                "math": "0",
                "shadow": "0",
            },
        )
        self.root = ET.SubElement(self.model, "root")
        ET.SubElement(self.root, "mxCell", {"id": "0"})
        ET.SubElement(self.root, "mxCell", {"id": "1", "parent": "0"})

    def _id(self, requested: str | None = None) -> str:
        if requested:
            return requested
        value = f"{self.name[:2]}-{self.counter}"
        self.counter += 1
        return value

    def vertex(self, value: str, x: float, y: float, w: float, h: float, style: str, cell_id: str | None = None) -> str:
        ident = self._id(cell_id)
        cell = ET.SubElement(
            self.root,
            "mxCell",
            {"id": ident, "value": value, "style": style, "vertex": "1", "parent": "1"},
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": f"{x:.3f}", "y": f"{y:.3f}", "width": f"{w:.3f}", "height": f"{h:.3f}", "as": "geometry"},
        )
        return ident

    def text(self, value: str, x: float, y: float, w: float, h: float, size: int = 16, color: str = CHARCOAL, bold: bool = False, align: str = "center", cell_id: str | None = None, rotation: int = 0) -> str:
        style = _text_style(size, color, bold, align)
        if rotation:
            style += f"rotation={rotation};"
        return self.vertex(value, x, y, w, h, style, cell_id)

    def rect(self, x: float, y: float, w: float, h: float, fill: str, stroke: str = "none", stroke_width: float = 1, rounded: int = 0, cell_id: str | None = None) -> str:
        style = _style(
            rounded=rounded,
            whiteSpace="wrap",
            html=1,
            fillColor=f"#{fill}" if fill != "none" else "none",
            strokeColor=f"#{stroke}" if stroke != "none" else "none",
            strokeWidth=stroke_width,
            arcSize=8,
        )
        return self.vertex("", x, y, w, h, style, cell_id)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = CHARCOAL, width: float = 2, dashed: bool = False, arrow: bool = False, cell_id: str | None = None) -> str:
        ident = self._id(cell_id)
        style = _style(
            edgeStyle="none",
            rounded=0,
            html=1,
            strokeColor=f"#{color}",
            strokeWidth=width,
            dashed=1 if dashed else 0,
            endArrow="block" if arrow else "none",
            endFill=1,
        )
        cell = ET.SubElement(self.root, "mxCell", {"id": ident, "style": style, "edge": "1", "parent": "1"})
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        ET.SubElement(geometry, "mxPoint", {"x": f"{x1:.3f}", "y": f"{y1:.3f}", "as": "sourcePoint"})
        ET.SubElement(geometry, "mxPoint", {"x": f"{x2:.3f}", "y": f"{y2:.3f}", "as": "targetPoint"})
        return ident

    def circle(self, value: str, x: float, y: float, size: float, fill: str, stroke: str = CHARCOAL, font_size: int = 16, cell_id: str | None = None) -> str:
        text_color = WHITE if value and fill == CHARCOAL else CHARCOAL
        style = _box_style(fill, stroke, font_size, rounded=0, bold=True) + f"fontColor=#{text_color};ellipse;aspect=fixed;"
        return self.vertex(value, x, y, size, size, style, cell_id)

    def zone(self, number: int, label: str, x: float, y: float, w: float, h: float, fill: str, stroke: str) -> None:
        self.rect(x, y, w, h, fill, stroke, 2, 1)
        self.circle(str(number), x + 16, y + 14, 34, CHARCOAL, CHARCOAL, 16)
        self.text(label, x + 58, y + 12, w - 72, 38, 19, stroke, True, "left")


def _arrow(page: Page, x1: float, y1: float, x2: float, y2: float, color: str = CHARCOAL, dashed: bool = False) -> None:
    page.line(x1, y1, x2, y2, color, 3, dashed, True)


def _layer_stack(page: Page, x: float, y: float, w: float, h: float, fill: str, stroke: str, label: str) -> None:
    for offset in (16, 8, 0):
        page.rect(x - offset, y + offset, w, h, fill, stroke, 1.5, 1)
    page.text(label, x, y, w, h, 15, CHARCOAL, True)


def _packet_strip(page: Page, x: float, y: float, count: int, scale: float = 1.0) -> None:
    heights = [38, 63, 46, 76, 52, 68, 42, 58]
    colors = [BLUE, ORANGE]
    width = 30 * scale
    gap = 8 * scale
    for index in range(count):
        height = heights[index % len(heights)] * scale
        px = x + index * (width + gap)
        py = y + 80 * scale - height
        page.rect(px, py, width, height, colors[index % 2], colors[index % 2], 1, 1)
        page.text("+" if index % 2 == 0 else "-", px, py + height / 2 - 10, width, 20, max(8, int(12 * scale)), WHITE, True)


def build_architecture_page() -> Page:
    page = Page(PAGE_NAMES[0], 1500, 900)
    page.zone(1, "Packet-level input", 45, 70, 330, 750, SOFT_BLUE, BLUE)
    _packet_strip(page, 85, 150, 6, 0.75)
    page.text("Encrypted packet sequence", 70, 220, 280, 35, 17, BLUE, True)
    page.vertex("Input tensor<br><b>[B, 30, 3]</b>", 95, 290, 230, 80, _box_style(WHITE, BLUE, 17, 1, False))
    _arrow(page, 210, 375, 210, 425, BLUE)
    page.vertex("Linear projection<br><b>3 -&gt; 128</b>", 95, 430, 230, 80, _box_style(WHITE, BLUE, 17, 1, False))
    _arrow(page, 210, 515, 210, 565, BLUE)
    _layer_stack(page, 110, 570, 210, 78, SOFT_VIOLET, VIOLET, "Learned positional embedding")
    page.text("[B, 30, 128]", 110, 680, 210, 34, 16, VIOLET, True)

    page.zone(2, "HSTA module", 405, 70, 710, 750, SOFT_VIOLET, VIOLET)
    top_y, bottom_y = 205, 505
    xs = [455, 675, 895]
    top = [
        ("Mamba block 1", SOFT_BLUE, BLUE),
        ("Mamba block 2", SOFT_BLUE, BLUE),
        ("Transition MLP", SOFT_GREEN, GREEN),
    ]
    for index, (label, fill, stroke) in enumerate(top):
        _layer_stack(page, xs[index] + 8, top_y, 170, 95, fill, stroke, label)
        if index < 2:
            _arrow(page, xs[index] + 180, top_y + 48, xs[index + 1] - 6, top_y + 48, stroke)
    page.line(985, 305, 985, 430, VIOLET, 3)
    page.line(985, 430, 545, 430, VIOLET, 3)
    _arrow(page, 545, 430, 545, 500, VIOLET)
    bottom = [
        ("Attention", SOFT_ORANGE, ORANGE),
        ("Refinement MLP", SOFT_GREEN, GREEN),
        ("LayerNorm", SOFT_GREEN, GREEN),
    ]
    for index, (label, fill, stroke) in enumerate(bottom):
        page.vertex(label, xs[index], bottom_y, 180, 105, _box_style(fill, stroke, 18, 1, True))
    _arrow(page, 635, bottom_y + 52, 675, bottom_y + 52, ORANGE)
    _arrow(page, 855, bottom_y + 52, 895, bottom_y + 52, GREEN)
    page.text("Linear-time state modeling", 455, 350, 390, 40, 16, BLUE, True)
    page.text("Selective global interaction", 785, 350, 270, 40, 16, ORANGE, True)
    page.rect(425, 435, 235, 215, "none", ORANGE, 2, 1)
    page.text("Q", 445, 460, 42, 34, 15, VIOLET, True)
    page.text("K", 500, 460, 42, 34, 15, VIOLET, True)
    page.text("V", 555, 460, 42, 34, 15, VIOLET, True)
    page.line(465, 505, 525, 550, VIOLET, 1.5, False, True)
    page.line(520, 505, 525, 550, VIOLET, 1.5, False, True)
    page.line(575, 505, 525, 550, VIOLET, 1.5, False, True)

    page.zone(3, "Prediction head", 1145, 70, 310, 750, SOFT_ORANGE, ORANGE)
    _layer_stack(page, 1200, 180, 200, 90, WHITE, ORANGE, "Normalized token states")
    _arrow(page, 1300, 300, 1300, 355, ORANGE)
    page.vertex("Mean pooling<br><b>[B, 128]</b>", 1190, 365, 220, 90, _box_style(WHITE, ORANGE, 18, 1, False))
    _arrow(page, 1300, 460, 1300, 515, ORANGE)
    page.vertex("Linear classifier<br><b>128 -&gt; C</b>", 1190, 525, 220, 90, _box_style(WHITE, ORANGE, 18, 1, False))
    _arrow(page, 1300, 620, 1300, 675, ORANGE)
    page.vertex("Class logits<br><b>[B, C]</b>", 1190, 685, 220, 80, _box_style(ORANGE, ORANGE, 20, 1, True) + f"fontColor=#{WHITE};")
    page.line(320, 609, 390, 609, BLUE, 3)
    page.line(390, 609, 390, 253, BLUE, 3)
    _arrow(page, 390, 253, 455, 253, BLUE)
    page.line(1075, 557, 1125, 557, ORANGE, 3)
    page.line(1125, 557, 1125, 225, ORANGE, 3)
    _arrow(page, 1125, 225, 1200, 225, ORANGE)
    return page


def _chart_axes(page: Page, x: float, y: float, w: float, h: float, y_min: float, y_max: float, ticks: list[float], y_label: str) -> None:
    page.line(x, y, x, y + h, CHARCOAL, 2)
    page.line(x, y + h, x + w, y + h, CHARCOAL, 2)
    for tick in ticks:
        ty = y + h - (tick - y_min) / (y_max - y_min) * h
        page.line(x, ty, x + w, ty, "D9DEE2", 1)
        page.text(f"{tick:.0f}", x - 55, ty - 14, 45, 28, 13, CHARCOAL, False, "right")
    page.text(y_label, x - 160, y + h / 2 - 17, 160, 34, 14, CHARCOAL, True, "center", rotation=270)


def _error_bar(page: Page, center_x: float, mean_y: float, error_height: float, cell_prefix: str) -> None:
    cap_half_width = 6
    segments = {
        "stem": (center_x, mean_y - error_height, center_x, mean_y + error_height),
        "upper-cap": (center_x - cap_half_width, mean_y - error_height, center_x + cap_half_width, mean_y - error_height),
        "lower-cap": (center_x - cap_half_width, mean_y + error_height, center_x + cap_half_width, mean_y + error_height),
    }
    for name, (x1, y1, x2, y2) in segments.items():
        page.line(x1, y1, x2, y2, WHITE, 3.2, cell_id=f"{cell_prefix}-{name}-halo")
    for name, (x1, y1, x2, y2) in segments.items():
        page.line(x1, y1, x2, y2, ERROR_GRAY, 1.2, cell_id=f"{cell_prefix}-{name}-foreground")


def build_main_page(data: FigureData) -> Page:
    page = Page(PAGE_NAMES[1], 1600, 940)
    page.rect(45, 55, 1510, 820, LIGHT_GRAY, CHARCOAL, 2, 1)
    x, y, w, h = 160, 150, 1320, 570
    _chart_axes(page, x, y, w, h, 80, 100, [80, 85, 90, 95, 100], "Macro-F1 (%)")
    methods = ["GRU", "Transformer", "30pktTCNET", "NetMamba", "HSTA"]
    colors = [MID_GRAY, VIOLET, TEAL, BLUE, ORANGE]
    group_width = w / len(TASKS)
    bar_w, gap = 38, 10
    for task_index, task in enumerate(TASKS):
        group_x = x + task_index * group_width + 42
        for method_index, method in enumerate(methods):
            mean, std = data.main[method][task]
            bx = group_x + method_index * (bar_w + gap)
            bh = max(0, (mean - 80) / 20 * h)
            by = y + h - bh
            page.rect(bx, by, bar_w, bh, colors[method_index], colors[method_index], 1, 1)
            page.text(f"{mean:.2f}", bx - 13, by - 31, bar_w + 26, 25, 11, colors[method_index], method == "HSTA")
            if std is not None:
                err = std / 20 * h
                _error_bar(page, bx + bar_w / 2, by, err, f"p2-error-{task_index}-{method_index}")
        page.text(task, group_x - 10, y + h + 16, 260, 34, 16, CHARCOAL, True)
        if task_index < len(TASKS) - 1:
            sep = x + (task_index + 1) * group_width
            page.line(sep, y + 15, sep, y + h - 10, "C9CFD4", 1, True)
    legend_x = 230
    for index, method in enumerate(methods):
        lx = legend_x + index * 245
        page.rect(lx, 790, 28, 18, colors[index], colors[index], 1, 1)
        page.text(method, lx + 38, 779, 180, 40, 15, colors[index], method == "HSTA", "left")
    page.text("Bars show mean; whiskers show standard deviation across three seeds where available.", 300, 835, 1000, 30, 13, CHARCOAL)
    return page


def _attention_schematic(page: Page, x: float, y: float, label: str, sequence: list[str], color: str) -> None:
    page.text(label, x, y, 210, 28, 13, color, True)
    for index, stage in enumerate(sequence):
        fill = color if stage == "A" else WHITE
        text_color = WHITE if fill != WHITE else CHARCOAL
        page.vertex(stage, x + index * 38 + 12, y + 36, 28, 28, _box_style(fill, color, 11, 1, True) + f"fontColor=#{text_color};")
        if index < 4:
            page.line(x + index * 38 + 40, y + 50, x + index * 38 + 49, y + 50, color, 1, False, True)


def build_ablation_page(data: FigureData) -> Page:
    page = Page(PAGE_NAMES[2], 1600, 1000)
    page.rect(45, 45, 1510, 900, SOFT_VIOLET, VIOLET, 2, 1)
    variants = ["No attention", "Front attention", "Middle attention", "HSTA"]
    colors = [MID_GRAY, VIOLET, BLUE, ORANGE]
    sequences = [
        ["M", "M", "T", "R", "R"],
        ["A", "M", "M", "T", "R"],
        ["M", "A", "M", "T", "R"],
        ["M", "M", "T", "A", "R"],
    ]
    for index, variant in enumerate(variants):
        _attention_schematic(page, 150 + index * 355, 120, variant, sequences[index], colors[index])
    x, y, w, h = 160, 300, 1320, 500
    _chart_axes(page, x, y, w, h, 84, 100, [84, 88, 92, 96, 100], "Macro-F1 (%)")
    group_width = w / len(TASKS)
    bar_w, gap = 44, 13
    for task_index, task in enumerate(TASKS):
        group_x = x + task_index * group_width + 58
        for variant_index, variant in enumerate(variants):
            mean, std = data.ablation[variant][task]
            bx = group_x + variant_index * (bar_w + gap)
            bh = (mean - 84) / 16 * h
            by = y + h - bh
            page.rect(bx, by, bar_w, bh, colors[variant_index], colors[variant_index], 1, 1)
            page.text(f"{mean:.2f}", bx - 13, by - 30, bar_w + 26, 24, 11, colors[variant_index], variant == "HSTA")
            err = std / 16 * h
            _error_bar(page, bx + bar_w / 2, by, err, f"p3-error-{task_index}-{variant_index}")
        page.text(task, group_x - 35, y + h + 14, 260, 32, 16, CHARCOAL, True)
    page.text("M: Mamba    T: Transition MLP    A: Attention    R: Refinement MLP", 350, 885, 900, 30, 13, CHARCOAL)
    return page


def build_parameter_page(data: FigureData) -> Page:
    page = Page(PAGE_NAMES[3], 1500, 900)
    page.rect(45, 55, 1410, 790, SOFT_GREEN, GREEN, 2, 1)
    x, y, w, h = 180, 150, 1190, 570
    x_min, x_max = 0.15, 1.10
    y_min, y_max = 90.5, 97.0
    page.line(x, y, x, y + h, CHARCOAL, 2)
    page.line(x, y + h, x + w, y + h, CHARCOAL, 2)
    for tick in (0.2, 0.4, 0.6, 0.8, 1.0):
        tx = x + (tick - x_min) / (x_max - x_min) * w
        page.line(tx, y, tx, y + h, "D9DEE2", 1)
        page.text(f"{tick:.1f}", tx - 25, y + h + 8, 50, 28, 13)
    for tick in (91, 92, 93, 94, 95, 96, 97):
        ty = y + h - (tick - y_min) / (y_max - y_min) * h
        page.line(x, ty, x + w, ty, "D9DEE2", 1)
        page.text(f"{tick}", x - 55, ty - 14, 45, 28, 13, CHARCOAL, False, "right")
    page.text("Parameters (M)", 600, 770, 350, 35, 17, CHARCOAL, True)
    page.text("Average 40-class Macro-F1 (%)", 5, 415, 190, 40, 13, CHARCOAL, True, "center", rotation=270)
    colors = {"GRU": MID_GRAY, "Transformer": VIOLET, "30pktTCNET": TEAL, "NetMamba": BLUE, "HSTA": ORANGE}
    offsets = {"GRU": (-65, 12), "Transformer": (18, -45), "30pktTCNET": (-140, -55), "NetMamba": (18, 12), "HSTA": (18, -48)}
    for model, color in colors.items():
        param = data.parameters[model]
        perf = statistics.mean([data.main[model]["QUIC-40"][0], data.main[model]["TLS-40"][0]])
        px = x + (param - x_min) / (x_max - x_min) * w
        py = y + h - (perf - y_min) / (y_max - y_min) * h
        size = 34 if model == "HSTA" else 25
        page.circle("", px - size / 2, py - size / 2, size, color, WHITE, 1)
        ox, oy = offsets[model]
        page.text(f"<b>{model}</b><br>{param:.3f} M | {perf:.2f}%", px + ox, py + oy, 165, 45, 13, color, model == "HSTA", "left")
    page.rect(1040, 165, 270, 95, SOFT_ORANGE, ORANGE, 2, 1)
    page.text("Upper-left is preferred:<br>higher Macro-F1 with fewer parameters", 1060, 180, 230, 60, 14, ORANGE, True)
    return page


def build_transfer_page(data: FigureData) -> Page:
    page = Page(PAGE_NAMES[4], 1600, 920)
    page.rect(45, 55, 1510, 810, SOFT_BLUE, BLUE, 2, 1)
    x, y, w = 430, 200, 1020
    for tick in (0, 20, 40, 60, 80, 100):
        tx = x + tick / 100 * w
        page.line(tx, y - 30, tx, y + 500, "D9DEE2", 1)
        page.text(str(tick), tx - 25, y + 515, 50, 30, 13)
    page.text("Macro-F1 (%)", 760, 770, 350, 35, 17, CHARCOAL, True)
    methods = ["Zero-shot", "LoRA", "Full fine-tuning", "Target scratch"]
    colors = [MID_GRAY, VIOLET, BLUE, ORANGE]
    y_positions = [230, 355, 480, 605]
    for row_index, task in enumerate(TRANSFER_TASKS):
        ry = y_positions[row_index]
        source, target = task.split(" to ")
        page.vertex(source, 95, ry - 27, 120, 54, _box_style(SOFT_BLUE, BLUE, 14, 1, True))
        _arrow(page, 220, ry, 270, ry, BLUE)
        page.vertex(target, 275, ry - 27, 125, 54, _box_style(SOFT_ORANGE, ORANGE, 14, 1, True))
        page.line(x, ry, x + w, ry, "B7C0C7", 2)
        for method_index, method in enumerate(methods):
            value = data.transfer[method][task]
            px = x + value / 100 * w
            size = 28 if method == "Target scratch" else 22
            page.circle("", px - size / 2, ry - size / 2, size, colors[method_index], WHITE, 1)
            label_y = ry - 44 if method_index % 2 == 0 else ry + 18
            page.text(f"{value:.2f}", px - 30, label_y, 60, 24, 11, colors[method_index], method == "Target scratch")
    for index, method in enumerate(methods):
        lx = 440 + index * 255
        page.circle("", lx, 125, 18, colors[index], WHITE, 1)
        page.text(method, lx + 28, 115, 205, 38, 14, colors[index], method == "Target scratch", "left")
    page.text("* Zero-shot values use covered-class Macro-F1.", 470, 825, 620, 28, 13, CHARCOAL, False, "left")
    return page


HEAT_COLORS = ["F4F7F9", "E0EAF1", "C8DCEA", "A9CADF", "82B2D0", "5D98BD", "3F78A3", "285A7D"]


def _heat_color(value: float) -> str:
    index = min(len(HEAT_COLORS) - 1, int(math.sqrt(max(0.0, min(1.0, value))) * len(HEAT_COLORS)))
    return HEAT_COLORS[index]


def _draw_matrix(page: Page, data: ConfusionData, prefix: str, x: float, y: float, size: float, label: str) -> None:
    n = len(data.matrix)
    cell = size / n
    page.text(label, x, y - 55, size, 36, 20, BLUE, True)
    for row_index, row in enumerate(data.matrix):
        total = max(1, sum(row))
        for col_index, count in enumerate(row):
            ratio = count / total
            page.rect(
                x + col_index * cell,
                y + row_index * cell,
                cell + 0.05,
                cell + 0.05,
                _heat_color(ratio),
                "none",
                0,
                0,
                f"p6-{prefix}-cell-{row_index}-{col_index}",
            )
    page.rect(x, y, size, size, "none", CHARCOAL, 2, 0)
    step = 5 if n == 40 else 10
    for index in range(0, n, step):
        pos = index + 1
        page.text(str(pos), x + index * cell - 12, y + size + 5, 30, 24, 10, CHARCOAL)
        page.text(str(pos), x - 34, y + index * cell - 5, 28, 20, 10, CHARCOAL, False, "right")
    page.text("Predicted class index", x + size / 2 - 130, y + size + 36, 260, 30, 14, CHARCOAL, True)
    page.text("True class index", x - 78, y + size / 2 - 18, 70, 36, 13, CHARCOAL, True)


def _callout_pair(page: Page, data: ConfusionData, prefix: str, x: float, y: float, size: float, source_id: str, target_id: str, box_x: float, box_y: float) -> None:
    if source_id not in data.class_ids or target_id not in data.class_ids:
        return
    row = data.class_ids.index(source_id)
    col = data.class_ids.index(target_id)
    cell = size / len(data.matrix)
    count = data.matrix[row][col]
    total = max(1, sum(data.matrix[row]))
    percent = count / total * 100
    page.rect(x + col * cell, y + row * cell, cell, cell, "none", ORANGE, 3, 0, f"p6-{prefix}-highlight-{row}-{col}")
    label = f"<b>{data.class_names[row]} -&gt; {data.class_names[col]}</b><br>{count} flows | {percent:.2f}%"
    page.vertex(label, box_x, box_y, 290, 62, _box_style(SOFT_ORANGE, ORANGE, 13, 1, False))
    page.line(x + (col + 0.5) * cell, y + (row + 0.5) * cell, box_x, box_y + 31, ORANGE, 1.5, True, False)


def build_confusion_page(data: FigureData) -> Page:
    page = Page(PAGE_NAMES[5], 1900, 980)
    page.rect(35, 35, 1830, 890, LIGHT_GRAY, CHARCOAL, 2, 1)
    q40, q60 = data.confusion["QUIC-40"], data.confusion["QUIC-60"]
    x1, x2, y, size = 125, 980, 160, 570
    _draw_matrix(page, q40, "q40", x1, y, size, "QUIC-40")
    _draw_matrix(page, q60, "q60", x2, y, size, "QUIC-60")
    _callout_pair(page, q40, "q40", x1, y, size, "68", "13", 80, 790)
    _callout_pair(page, q40, "q40", x1, y, size, "52", "41", 385, 790)
    _callout_pair(page, q60, "q60", x2, y, size, "68", "13", 955, 790)
    _callout_pair(page, q60, "q60", x2, y, size, "52", "41", 1260, 790)
    bar_x = 1670
    for index, color in enumerate(HEAT_COLORS):
        page.rect(bar_x, 250 + (len(HEAT_COLORS) - 1 - index) * 48, 34, 48, color, "none")
    page.rect(bar_x, 250, 34, len(HEAT_COLORS) * 48, "none", CHARCOAL, 1)
    page.text("100%", bar_x + 44, 240, 70, 28, 12, CHARCOAL, False, "left")
    page.text("0%", bar_x + 44, 625, 70, 28, 12, CHARCOAL, False, "left")
    page.text("Row-normalized", 1630, 675, 150, 30, 12, CHARCOAL, True)
    return page


def build_data_page() -> Page:
    page = Page(PAGE_NAMES[6], 1800, 1100)
    page.zone(1, "Encrypted traffic acquisition", 45, 55, 395, 430, SOFT_BLUE, BLUE)
    page.vertex("CESNET-TLS22", 95, 135, 290, 68, _box_style(WHITE, BLUE, 19, 1, True))
    page.vertex("CESNET-QUIC22", 95, 225, 290, 68, _box_style(WHITE, BLUE, 19, 1, True))
    _packet_strip(page, 95, 335, 6, 0.75)
    page.text("Application labels + packet-level PPI records", 70, 415, 345, 42, 14, BLUE, True)

    page.zone(2, "Flow reconstruction", 470, 55, 390, 430, SOFT_VIOLET, VIOLET)
    page.text("Group packet rows by flow_id", 520, 130, 290, 42, 17, VIOLET, True)
    _packet_strip(page, 520, 195, 7, 0.72)
    page.line(530, 310, 800, 310, VIOLET, 2, True)
    page.text("Ordered packet sequence", 540, 325, 250, 35, 15, VIOLET, True)
    page.text("Malformed rows removed before flow assembly", 510, 395, 310, 45, 13, CHARCOAL)

    page.zone(3, "Payload-free feature encoding", 890, 55, 480, 430, SOFT_GREEN, GREEN)
    features = [("|s|", "Packet size"), ("d", "Direction"), ("dt", "Inter-arrival time")]
    for index, (symbol, label) in enumerate(features):
        fx = 930 + index * 145
        page.circle(symbol, fx + 30, 145, 70, WHITE, GREEN, 20)
        page.text(label, fx, 225, 130, 46, 14, GREEN, True)
    page.text("No payload", 930, 320, 120, 40, 14, CHARCOAL, True)
    page.text("No DPI", 1050, 320, 120, 40, 14, CHARCOAL, True)
    page.text("No domains", 1170, 320, 130, 40, 14, CHARCOAL, True)
    page.rect(920, 305, 410, 75, "none", GREEN, 2, 1)
    page.text("No application-layer metadata", 960, 390, 330, 40, 13, GREEN, True)

    page.zone(4, "Fixed-length sequence", 1400, 55, 355, 430, SOFT_ORANGE, ORANGE)
    columns = ["Packet", "Size", "Dir.", "Delta t"]
    table_x, table_y, col_w, row_h = 1435, 140, 70, 40
    for col, label in enumerate(columns):
        page.vertex(label, table_x + col * col_w, table_y, col_w, row_h, _box_style(SOFT_ORANGE, ORANGE, 11, 0, True))
    rows = [("1", "...", "+1", "..."), ("2", "...", "-1", "..."), ("...", "...", "...", "..."), ("30", "...", "+1", "..."), ("pad", "0", "0", "0")]
    for row_index, values in enumerate(rows):
        for col, value in enumerate(values):
            fill = LIGHT_GRAY if row_index == len(rows) - 1 else WHITE
            page.vertex(value, table_x + col * col_w, table_y + (row_index + 1) * row_h, col_w, row_h, _box_style(fill, "C18A64", 11, 0, False))
    page.text("Truncate or zero-pad to 30 packets", 1425, 395, 305, 45, 14, ORANGE, True)

    _arrow(page, 440, 270, 470, 270, BLUE)
    _arrow(page, 860, 270, 890, 270, VIOLET)
    _arrow(page, 1370, 270, 1400, 270, GREEN)

    page.zone(5, "Leakage-aware preparation", 45, 530, 1120, 500, SOFT_GREEN, GREEN)
    page.text("Protocol-specific temporal partitioning", 90, 615, 420, 42, 18, GREEN, True)
    split_y = 690
    page.vertex("Train", 95, split_y, 400, 90, _box_style(SOFT_BLUE, BLUE, 20, 1, True))
    page.vertex("Validation", 515, split_y, 250, 90, _box_style(WHITE, GREEN, 18, 1, True))
    page.vertex("Test", 785, split_y, 250, 90, _box_style(WHITE, GREEN, 18, 1, True))
    page.text("Official DataZoo split retained when available", 150, 800, 820, 40, 14, CHARCOAL, True)
    page.rect(90, 875, 980, 105, WHITE, GREEN, 2, 1)
    page.text("<b>Train-only standardization</b><br>Fit mean and scale on Train -&gt; transform Train / Validation / Test", 125, 892, 910, 70, 17, GREEN, False)

    page.zone(6, "Model-ready representation", 1200, 530, 555, 500, SOFT_ORANGE, ORANGE)
    for offset in (32, 16, 0):
        page.rect(1345 - offset, 665 + offset, 270, 170, WHITE, ORANGE, 2, 1)
        for row in range(3):
            for col in range(6):
                page.rect(1370 - offset + col * 35, 690 + offset + row * 35, 25, 25, SOFT_ORANGE if (row + col) % 2 else SOFT_BLUE, "D6B18F", 0.7, 0)
    page.text("Input tensor", 1360, 610, 240, 40, 18, ORANGE, True)
    page.text("<b>X in R^(B x 30 x 3)</b><br>y in {1, ..., C}", 1300, 865, 355, 75, 21, ORANGE, True)
    page.text("Compact packet-side representation for HSTA", 1280, 960, 395, 35, 14, CHARCOAL, True)
    _arrow(page, 1165, 780, 1200, 780, GREEN)
    return page


def _ga_panel(page: Page, letter: str, title: str, x: float, y: float, w: float, h: float, color: str, fill: str) -> None:
    page.rect(x, y, w, h, WHITE, color, 2, 1)
    page.rect(x + 12, y + 10, w - 24, 50, fill, "none", 0, 1)
    page.circle(letter, x + 24, y + 18, 34, color, color, 16)
    page.text(title, x + 70, y + 16, w - 94, 36, 18, color, True, "left")


def _ga_stage_box(
    page: Page,
    number: int,
    label: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    stroke: str,
    cell_id: str | None = None,
) -> None:
    page.rect(x, y, w, h, fill, stroke, 2, 1, cell_id)
    page.circle(str(number), x + 14, y + 14, 32, stroke, stroke, 14)
    page.text(label, x + 56, y + 10, w - 68, 48, 18, stroke, True, "left")


def _ga_sequence_glyph(page: Page, x: float, y: float, color: str) -> None:
    values = [22, 52, 34, 68, 43]
    for index, value in enumerate(values):
        px = x + index * 28
        page.rect(px, y + 55 - value / 2, 16, value / 2, color if index % 2 == 0 else WHITE, color, 1, 1)
    page.line(x + 8, y + 56, x + 120, y + 56, color, 1.5)


def _ga_network(page: Page, x: float, y: float, color: str) -> None:
    left = [(x, y + offset) for offset in (0, 28, 56, 84)]
    right = [(x + 90, y + offset) for offset in (14, 42, 70)]
    for lx, ly in left:
        for rx, ry in right:
            page.line(lx + 10, ly + 10, rx + 10, ry + 10, color, 0.7)
    for px, py in (*left, *right):
        page.circle("", px, py, 20, WHITE, color, 8)


def _ga_heatmap(page: Page, x: float, y: float, color: str, fill: str) -> None:
    intensities = [0, 2, 5, 1, 3, 7, 4, 2, 1, 4, 6, 3, 0, 2, 3, 7]
    palette = [WHITE, "F7F2FA", "E9DFF0", "D6C3E1", "B99FCC", "9D79B5", VIOLET, "5F4675"]
    for row in range(4):
        for col in range(4):
            page.rect(x + col * 27, y + row * 27, 24, 24, palette[intensities[row * 4 + col]], "D8CCE0", 0.6, 0)
    page.text("Q / K / V", x, y + 114, 105, 22, 11, color, True)


def _ga_mini_matrix(page: Page, data: ConfusionData, prefix: str, x: float, y: float, size: float, label: str) -> None:
    n = len(data.matrix)
    cell = size / n
    page.text(label, x, y - 28, size, 24, 13, BLUE, True)
    for row_index, row in enumerate(data.matrix):
        total = max(1, sum(row))
        for col_index, count in enumerate(row):
            page.rect(
                x + col_index * cell,
                y + row_index * cell,
                cell + 0.03,
                cell + 0.03,
                _heat_color(count / total),
                "none",
                0,
                0,
                f"ga-{prefix}-cell-{row_index}-{col_index}",
            )
    page.rect(x, y, size, size, "none", CHARCOAL, 1.5, 0)


def build_graphical_abstract_page(data: FigureData) -> Page:
    page = Page("Graphical Abstract", 2600, 1700)
    page.rect(30, 25, 2540, 110, CHARCOAL, CHARCOAL, 0, 1)
    page.text("HSTA", 66, 43, 175, 62, 38, WHITE, True, "left")
    page.text(
        "Hybrid state-space transition-attention modeling for encrypted QUIC/TLS traffic classification",
        240,
        43,
        1470,
        62,
        22,
        WHITE,
        True,
        "left",
    )
    badges = [
        ("30 packets", BLUE, SOFT_BLUE),
        ("3 side-channel features", GREEN, SOFT_GREEN),
        ("No payload / DPI", ORANGE, SOFT_ORANGE),
    ]
    for index, (label, stroke, fill) in enumerate(badges):
        page.vertex(label, 1765 + index * 260, 54, 230, 46, _box_style(fill, stroke, 14, 1, True))

    # Band 1: a full-width, leakage-aware data preparation narrative.
    page.rect(40, 155, 2520, 520, WHITE, BLUE, 2, 1, "ga-data-band")
    page.rect(52, 167, 2496, 60, SOFT_BLUE, "none", 0, 1)
    page.circle("1", 68, 180, 36, BLUE, BLUE, 16)
    page.text("DATA PREPARATION", 118, 173, 270, 44, 20, BLUE, True, "left")
    page.text("Privacy-preserving input and leakage-aware packet-side preprocessing", 390, 173, 1160, 44, 21, CHARCOAL, True, "left")
    page.vertex("NO PAYLOAD", 2050, 180, 150, 36, _box_style(WHITE, ORANGE, 12, 1, True))
    page.vertex("NO DPI", 2215, 180, 125, 36, _box_style(WHITE, ORANGE, 12, 1, True))
    page.vertex("NO DOMAINS", 2355, 180, 165, 36, _box_style(WHITE, ORANGE, 12, 1, True))

    data_steps = [
        ("01", "ENCRYPTED DATA", 70, 245, 330, SOFT_BLUE, BLUE),
        ("02", "FLOW RECONSTRUCTION", 430, 245, 340, SOFT_VIOLET, VIOLET),
        ("03", "FIXED-LENGTH ENCODING", 800, 245, 610, SOFT_ORANGE, ORANGE),
        ("04", "LEAKAGE-AWARE SPLIT", 1440, 245, 530, SOFT_GREEN, GREEN),
        ("05", "MODEL-READY TENSOR", 2000, 245, 520, LIGHT_GRAY, CHARCOAL),
    ]
    for number, title, x, y, width, fill, stroke in data_steps:
        page.rect(x, y, width, 390, fill, stroke, 1.5, 1)
        page.circle(number, x + 14, y + 14, 32, stroke, stroke, 12)
        page.text(title, x + 58, y + 10, width - 72, 40, 16, stroke, True, "left")

    page.vertex("CESNET-TLS22", 90, 315, 138, 44, _box_style(WHITE, BLUE, 13, 1, True))
    page.vertex("CESNET-QUIC22", 240, 315, 140, 44, _box_style(WHITE, BLUE, 13, 1, True))
    _packet_strip(page, 105, 385, 7, 0.70)
    page.text("Encrypted bidirectional packet stream", 84, 458, 300, 34, 14, BLUE, True)
    page.text("Application labels + packet-level PPI records", 84, 508, 300, 46, 13, CHARCOAL)
    page.vertex("payload remains encrypted", 100, 575, 270, 40, _box_style(WHITE, BLUE, 12, 1, True))

    flow_steps = [
        ("flow_id", 458, 320, BLUE, SOFT_BLUE),
        ("ordered packets", 458, 405, VIOLET, WHITE),
        ("first 30", 458, 490, ORANGE, WHITE),
    ]
    for index, (label, x, y, stroke, fill) in enumerate(flow_steps):
        page.vertex(label, x, y, 280, 50, _box_style(fill, stroke, 15, 1, True))
        if index < len(flow_steps) - 1:
            _arrow(page, x + 140, y + 53, x + 140, y + 78, stroke)
    page.text("group rows", 650, 365, 88, 22, 11, BLUE, True)
    page.text("preserve order", 630, 450, 108, 22, 11, VIOLET, True)
    page.text("truncate / pad", 630, 535, 108, 22, 11, ORANGE, True)
    page.text("Malformed records are removed before flow assembly", 458, 575, 282, 42, 12, CHARCOAL)

    table_x, table_y, col_w, row_h = 842, 305, 132, 39
    columns = ["Packet", "Size", "Direction", "Delta t"]
    for col, label in enumerate(columns):
        page.vertex(label, table_x + col * col_w, table_y, col_w, row_h, _box_style(SOFT_ORANGE, ORANGE, 12, 0, True))
    rows = [
        ("1", "s1", "+1", "dt1"),
        ("2", "s2", "-1", "dt2"),
        ("...", "...", "...", "..."),
        ("29", "s29", "-1", "dt29"),
        ("30", "s30", "+1", "dt30"),
        ("pad", "0", "0", "0"),
    ]
    for row_index, values in enumerate(rows):
        for col, value in enumerate(values):
            fill = LIGHT_GRAY if row_index == len(rows) - 1 else WHITE
            page.vertex(value, table_x + col * col_w, table_y + (row_index + 1) * row_h, col_w, row_h, _box_style(fill, "C79D7C", 12, 0, False))
    page.text("Truncate or zero-pad to 30 packets", 855, 592, 500, 28, 14, ORANGE, True)

    page.text("Official protocol-specific split", 1480, 305, 450, 34, 16, GREEN, True)
    split_x, split_y = 1480, 360
    split_widths = [230, 112, 112]
    split_labels = [("TRAIN", SOFT_BLUE, BLUE), ("VAL", WHITE, GREEN), ("TEST", WHITE, GREEN)]
    cursor = split_x
    for width, (label, fill, stroke) in zip(split_widths, split_labels):
        page.vertex(label, cursor, split_y, width, 68, _box_style(fill, stroke, 15, 1, True))
        cursor += width + 10
    page.text("Preserve the official DataZoo partition", 1490, 445, 430, 32, 13, CHARCOAL, True)
    page.rect(1480, 490, 450, 110, WHITE, GREEN, 1.5, 1)
    page.text("<b>train-only standardization</b><br>fit on Train -&gt; transform Train / Val / Test", 1505, 505, 400, 78, 15, GREEN, False)

    features = [
        ("Packet size", BLUE, SOFT_BLUE),
        ("Direction", ORANGE, SOFT_ORANGE),
        ("Inter-arrival time", GREEN, SOFT_GREEN),
    ]
    for index, (label, stroke, fill) in enumerate(features):
        page.vertex(label, 2030 + index * 155, 315, 140, 48, _box_style(fill, stroke, 12, 1, True))
    _layer_stack(page, 2155, 405, 230, 100, WHITE, BLUE, "Tensor [B, 30, 3]")
    page.text("X in R^(B x 30 x 3)", 2085, 522, 365, 34, 19, ORANGE, True)
    page.text("Compact packet-side representation", 2075, 558, 385, 28, 13, CHARCOAL, True)
    page.text("No payload | No DPI | No domains", 2040, 594, 450, 20, 11, ORANGE, True)

    for x1, x2, color in ((400, 430, BLUE), (770, 800, VIOLET), (1410, 1440, ORANGE), (1970, 2000, GREEN)):
        _arrow(page, x1, 445, x2, 445, color)

    # Band 2: the complete HSTA model occupies its own uninterrupted row.
    page.rect(40, 695, 2520, 455, WHITE, VIOLET, 2, 1, "ga-model-band")
    page.rect(52, 707, 2496, 60, SOFT_VIOLET, "none", 0, 1)
    page.circle("2", 68, 720, 36, VIOLET, VIOLET, 16)
    page.text("HSTA MODEL", 118, 713, 205, 44, 20, VIOLET, True, "left")
    page.text("HSTA representation and classification pipeline", 325, 713, 820, 44, 21, CHARCOAL, True, "left")
    page.text("state-space encoding", 1715, 713, 260, 44, 15, BLUE, True)
    page.text("selective interaction", 1975, 713, 260, 44, 15, VIOLET, True)
    page.text("compact prediction", 2235, 713, 260, 44, 15, ORANGE, True)

    stages = [
        ("Projection +<br>position", SOFT_BLUE, BLUE, 300),
        ("Mamba<br>block 1", SOFT_BLUE, BLUE, 285),
        ("Mamba<br>block 2", SOFT_BLUE, BLUE, 285),
        ("Transition<br>MLP", SOFT_GREEN, GREEN, 300),
        ("Attention", SOFT_VIOLET, VIOLET, 285),
        ("Refinement<br>MLP", SOFT_ORANGE, ORANGE, 300),
        ("Pool + head", LIGHT_GRAY, CHARCOAL, 300),
    ]
    sx = 100
    stage_positions = []
    for index, (label, fill, stroke, width) in enumerate(stages):
        _ga_stage_box(page, index + 1, label, sx, 790, width, 245, fill, stroke, f"ga-model-stage-{index + 1}")
        stage_positions.append((sx, width, stroke))
        sx += width + 38
    for index, (stage_x, width, stroke) in enumerate(stage_positions[:-1]):
        _arrow(page, stage_x + width, 912, stage_positions[index + 1][0], 912, stroke)
    _ga_sequence_glyph(page, 180, 875, BLUE)
    _ga_sequence_glyph(page, 520, 875, BLUE)
    _ga_sequence_glyph(page, 845, 875, BLUE)
    _ga_network(page, 1195, 860, GREEN)
    _ga_heatmap(page, 1530, 855, VIOLET, SOFT_VIOLET)
    _ga_network(page, 1855, 860, ORANGE)
    pool_stage_x = stage_positions[-1][0]
    for row in range(4):
        page.rect(pool_stage_x + 48, 858 + row * 29, 72 - row * 8, 18, SOFT_BLUE, BLUE, 1, 1)
    page.line(pool_stage_x + 145, 845, pool_stage_x + 145, 970, CHARCOAL, 2)
    for index, height in enumerate((32, 58, 82, 48)):
        page.rect(
            pool_stage_x + 180 + index * 28,
            970 - height,
            18,
            height,
            ORANGE,
            ORANGE,
            1,
            1,
            f"ga-pool-logit-{index}",
        )
    descriptions = [
        "3 -&gt; 128 + learned position",
        "local state dynamics",
        "long-range context",
        "nonlinear transition",
        "packet reweighting",
        "feature refinement",
        "LayerNorm + mean pooling",
    ]
    for index, (stage_x, width, stroke) in enumerate(stage_positions):
        page.text(descriptions[index], stage_x + 10, 1044, width - 20, 30, 13, stroke, True)
    mechanisms = [
        ("Sequential dependency modeling", BLUE),
        ("Discriminative packet reweighting", VIOLET),
        ("Compact flow representation", ORANGE),
    ]
    for index, (label, color) in enumerate(mechanisms):
        mx = 260 + index * 785
        page.circle(str(index + 1), mx, 1092, 30, color, color, 13)
        page.text(label, mx + 44, 1084, 570, 46, 16, color, True, "left")
        if index < 2:
            _arrow(page, mx + 630, 1107, mx + 735, 1107, color)

    # Band 3: four complementary evidence panels share one aligned baseline.
    page.rect(40, 1170, 2520, 490, WHITE, CHARCOAL, 1.5, 1, "ga-evidence-band")
    panel_y, panel_h = 1190, 450
    _ga_panel(page, "A", "Four-task performance", 58, panel_y, 600, panel_h, ORANGE, SOFT_ORANGE)
    chart_x, chart_y, chart_w, chart_h = 115, 1280, 485, 210
    page.line(chart_x, chart_y, chart_x, chart_y + chart_h, CHARCOAL, 1.5)
    page.line(chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h, CHARCOAL, 1.5)
    group_w = chart_w / 4
    methods = [("GRU", MID_GRAY), ("NetMamba", BLUE), ("HSTA", ORANGE)]
    for task_index, task in enumerate(TASKS):
        gx = chart_x + task_index * group_w + 18
        for method_index, (method, color) in enumerate(methods):
            value = data.main[method][task][0]
            bar_h = (value - 84) / 14 * chart_h
            bx = gx + method_index * 27
            page.rect(bx, chart_y + chart_h - bar_h, 20, bar_h, color, color, 0.5, 1)
        page.text(task, gx - 14, chart_y + chart_h + 10, 112, 26, 11, CHARCOAL, True)
        hsta_value = data.main["HSTA"][task][0]
        page.text(f"{hsta_value:.2f}", gx + 46, chart_y + chart_h - (hsta_value - 84) / 14 * chart_h - 25, 62, 22, 10, ORANGE, True)
    page.text("Best Macro-F1 on all four tasks", 120, 1535, 475, 28, 15, ORANGE, True)
    page.text("91.09 / 90.28 QUIC | 96.78 / 96.29 TLS", 105, 1570, 505, 26, 11, CHARCOAL, True)
    page.text("QUIC gains are largest over strong sequence baselines", 95, 1605, 525, 22, 10, CHARCOAL)

    _ga_panel(page, "B", "Attention placement", 678, panel_y, 600, panel_h, VIOLET, SOFT_VIOLET)
    variants = [
        ("No attention", "No attention", ["M", "M", "T", "R", "R"], MID_GRAY),
        ("Front", "Front attention", ["A", "M", "M", "T", "R"], VIOLET),
        ("Middle", "Middle attention", ["M", "A", "M", "T", "R"], BLUE),
        ("HSTA", "HSTA", ["M", "M", "T", "A", "R"], ORANGE),
    ]
    averages = {
        display_name: statistics.mean(data.ablation[data_key][task][0] for task in TASKS)
        for display_name, data_key, _, _ in variants
    }
    for index, (name, _, sequence, color) in enumerate(variants):
        vy = 1280 + index * 62
        page.text(name, 710, vy, 115, 28, 12, color, True, "left")
        for stage_index, stage in enumerate(sequence):
            fill = color if stage == "A" else WHITE
            text_color = WHITE if fill != WHITE else CHARCOAL
            page.vertex(stage, 830 + stage_index * 53, vy - 2, 38, 34, _box_style(fill, color, 11, 1, True) + f"fontColor=#{text_color};")
            if stage_index < 4:
                page.line(868 + stage_index * 53, vy + 15, 883 + stage_index * 53, vy + 15, color, 1, False, True)
        page.text(f"{averages[name]:.2f}%", 1120, vy, 110, 28, 12, color, name == "HSTA", "right")
    page.rect(730, 1535, 495, 72, SOFT_ORANGE, ORANGE, 1.5, 1)
    page.text("Attention is most effective after state-space encoding and transition.", 755, 1545, 445, 50, 13, ORANGE, True)

    _ga_panel(page, "C", "Efficiency and transfer", 1298, panel_y, 600, panel_h, GREEN, SOFT_GREEN)
    scatter_x, scatter_y, scatter_w, scatter_h = 1360, 1280, 475, 145
    page.line(scatter_x, scatter_y, scatter_x, scatter_y + scatter_h, CHARCOAL, 1.2)
    page.line(scatter_x, scatter_y + scatter_h, scatter_x + scatter_w, scatter_y + scatter_h, CHARCOAL, 1.2)
    model_colors = {"GRU": MID_GRAY, "Transformer": VIOLET, "30pktTCNET": TEAL, "NetMamba": BLUE, "HSTA": ORANGE}
    for model, color in model_colors.items():
        param = data.parameters[model]
        perf = statistics.mean([data.main[model]["QUIC-40"][0], data.main[model]["TLS-40"][0]])
        px = scatter_x + (param - 0.15) / 0.95 * scatter_w
        py = scatter_y + scatter_h - (perf - 90.5) / 6.5 * scatter_h
        page.circle("", px - 8, py - 8, 16 if model != "HSTA" else 23, color, WHITE, 8)
        if model in {"HSTA", "NetMamba", "Transformer"}:
            page.text(model, px + 10, py - 15, 100, 24, 10, color, model == "HSTA", "left")
    page.text("Parameters (M)", 1495, 1430, 200, 22, 10, CHARCOAL, True)
    page.vertex("HSTA: 0.602 M parameters", 1385, 1460, 425, 40, _box_style(SOFT_ORANGE, ORANGE, 13, 1, True))
    transfer_values = [data.transfer["Full fine-tuning"][task] for task in TRANSFER_TASKS]
    transfer_labels = [("QUIC", "TLS-40"), ("TLS", "QUIC-40"), ("QUIC", "TLS-60"), ("TLS", "QUIC-60")]
    for index, ((source, target), value) in enumerate(zip(transfer_labels, transfer_values)):
        ty = 1520 + (index % 2) * 46
        tx = 1338 + (index // 2) * 280
        page.vertex(source, tx, ty, 66, 30, _box_style(SOFT_BLUE, BLUE, 10, 1, True))
        _arrow(page, tx + 72, ty + 15, tx + 100, ty + 15, BLUE)
        page.vertex(target, tx + 106, ty, 82, 30, _box_style(SOFT_ORANGE, ORANGE, 10, 1, True))
        page.text(f"{value:.2f}", tx + 194, ty + 1, 60, 28, 11, ORANGE, True)
    page.text("Full fine-tuning remains effective across protocols", 1350, 1610, 490, 20, 10, GREEN, True)

    _ga_panel(page, "D", "Class-level error structure", 1918, panel_y, 624, panel_h, BLUE, SOFT_BLUE)
    _ga_mini_matrix(page, data.confusion["QUIC-40"], "q40", 1985, 1280, 190, "QUIC-40")
    _ga_mini_matrix(page, data.confusion["QUIC-60"], "q60", 2260, 1280, 190, "QUIC-60")
    page.rect(1970, 1495, 500, 72, SOFT_ORANGE, ORANGE, 1.5, 1)
    page.text("AdAvoid -&gt; Gmail", 1990, 1503, 215, 24, 12, ORANGE, True, "left")
    page.text("23.01% / 24.07%", 2225, 1503, 220, 24, 12, ORANGE, True, "right")
    page.text("Play.cz Radio -&gt; Overleaf Compile", 1990, 1535, 315, 23, 10, ORANGE, True, "left")
    page.text("21.33% / 17.96%", 2280, 1535, 165, 23, 10, ORANGE, True, "right")
    page.text("Errors are concentrated in a small number of service pairs.", 1995, 1575, 455, 32, 13, BLUE, True)
    page.text("Row-normalized matrices | highlighted pairs dominate residual confusion", 1975, 1608, 490, 22, 9, CHARCOAL)
    return page


def build_graphical_abstract_document(data: FigureData) -> str:
    page = build_graphical_abstract_page(data)
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Electron",
            "agent": "Codex HSTA graphical abstract generator",
            "version": "30.0.4",
            "type": "device",
            "compressed": "false",
        },
    )
    diagram = ET.SubElement(mxfile, "diagram", {"id": "hsta-graphical-abstract", "name": page.name})
    diagram.append(page.model)
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", xml_declaration=True)


def write_graphical_abstract(data: FigureData, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_graphical_abstract_document(data), encoding="utf-8")


def build_drawio_document(data: FigureData) -> str:
    pages = [
        build_architecture_page(),
        build_main_page(data),
        build_ablation_page(data),
        build_parameter_page(data),
        build_transfer_page(data),
        build_confusion_page(data),
        build_data_page(),
    ]
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Electron",
            "agent": "Codex HSTA figure generator",
            "version": "30.0.4",
            "type": "device",
            "compressed": "false",
        },
    )
    for page in pages:
        diagram = ET.SubElement(mxfile, "diagram", {"id": re.sub(r"[^a-z0-9]", "-", page.name.lower()), "name": page.name})
        diagram.append(page.model)
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", xml_declaration=True)


def write_drawio(data: FigureData, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_drawio_document(data), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate seven editable HSTA paper figures in draw.io format.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--graphical-abstract-output", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output = args.output or project_root / "paper" / "figures_drawio" / "JNCA_HSTA_Figures.drawio"
    graphical_output = (
        args.graphical_abstract_output
        or project_root / "paper" / "figures_drawio" / "JNCA_HSTA_Graphical_Abstract.drawio"
    )
    data = load_figure_data(project_root)
    write_drawio(data, output)
    write_graphical_abstract(data, graphical_output)
    print(f"Wrote {output}")
    print(f"Pages: {len(PAGE_NAMES)}")
    print(f"Wrote {graphical_output}")
    print("Graphical abstract pages: 1")


if __name__ == "__main__":
    main()
