"""Build an editable MVIF-Net Visio page and matching SVG preview."""

from __future__ import annotations

import html
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(r"E:\AllProject\流量分析python项目\paper\jnca_cas\figures")
STEM = "mvif_net_architecture"
VSDX = ROOT / f"{STEM}.vsdx"
SVG = ROOT / f"{STEM}.svg"
PNG = ROOT / f"{STEM}.png"
PAGE_W = 7.2
PAGE_H = 2.0
REF_W = 720.0
REF_H = 200.0
DRAW_W = 1800.0
DRAW_H = 500.0
DRAW_SCALE = 0.4
PX_PER_IN = REF_W / PAGE_W
VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", VISIO_NS)
ET.register_namespace("r", REL_NS)


C = {
    "ink": "#20262B",
    "gray": "#626C75",
    "light_gray": "#F4F6F8",
    "mid_gray": "#CDD3D8",
    "white": "#FFFFFF",
    "blue": "#3E6D8A",
    "blue_soft": "#EDF3F6",
    "green": "#5A7E68",
    "green_soft": "#EFF4F0",
    "orange": "#A66C3A",
    "orange_soft": "#F7F1EB",
    "purple": "#74658A",
    "purple_soft": "#F2EFF5",
    "teal": "#397783",
    "teal_soft": "#EDF4F5",
    "red": "#A24D4D",
    "red_soft": "#F7EEEE",
}

SHAPES: list[dict] = []


Y_SCALE = 1.0


def add_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    text: str = "",
    fill: str = "none",
    line: str = C["ink"],
    size: float = 9,
    bold: bool = False,
    line_pt: float = 0.8,
    dash: bool = False,
    round_px: float = 6,
    color: str = C["ink"],
    italic: bool = False,
) -> None:
    SHAPES.append(
        {
            "kind": "rect",
            "x": x * DRAW_SCALE,
            "y": y * Y_SCALE * DRAW_SCALE,
            "w": w * DRAW_SCALE,
            "h": h * Y_SCALE * DRAW_SCALE,
            "text": text,
            "fill": fill,
            "line": line,
            "size": size,
            "bold": bold,
            "italic": italic,
            "color": color,
            "line_pt": line_pt,
            "dash": dash,
            "round_px": round_px * DRAW_SCALE,
        }
    )


def add_text(
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: float = 9,
    color: str = C["ink"],
    bold: bool = False,
    italic: bool = False,
) -> None:
    add_rect(
        x,
        y,
        w,
        h,
        text,
        "none",
        "none",
        size,
        bold,
        0,
        False,
        0,
        color,
        italic,
    )


def add_oval(
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    line: str = C["white"],
    line_pt: float = 0.5,
) -> None:
    SHAPES.append(
        {
            "kind": "oval",
            "x": x * DRAW_SCALE,
            "y": y * Y_SCALE * DRAW_SCALE,
            "w": w * DRAW_SCALE,
            "h": h * Y_SCALE * DRAW_SCALE,
            "text": "",
            "fill": fill,
            "line": line,
            "line_pt": line_pt,
            "dash": False,
            "round_px": 0,
        }
    )


def add_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str = C["ink"],
    line_pt: float = 0.8,
    arrow: bool = False,
    dash: bool = False,
) -> None:
    SHAPES.append(
        {
            "kind": "line",
            "x1": x1 * DRAW_SCALE,
            "y1": y1 * Y_SCALE * DRAW_SCALE,
            "x2": x2 * DRAW_SCALE,
            "y2": y2 * Y_SCALE * DRAW_SCALE,
            "line": color,
            "line_pt": line_pt,
            "arrow": arrow,
            "dash": dash,
        }
    )


def arrow(x1: float, y1: float, x2: float, y2: float, color: str, line_pt: float = 1.0) -> None:
    add_line(x1, y1, x2, y2, color, line_pt, True)


def sum_node(cx: float, cy: float, color: str, diameter: float = 24) -> None:
    add_oval(cx - diameter / 2, cy - diameter / 2, diameter, diameter, C["white"], color, 0.8)
    add_text(cx - diameter / 2, cy - diameter / 2 - 1, diameter, diameter, "+", 5, color, True)


def multiply_node(cx: float, cy: float, color: str, diameter: float = 22) -> None:
    add_oval(cx - diameter / 2, cy - diameter / 2, diameter, diameter, C["white"], color, 0.8)
    add_text(cx - diameter / 2, cy - diameter / 2 - 1, diameter, diameter, "x", 4.8, color, True)


def grid(x: float, y: float, w: float, h: float, rows: int, cols: int, fill: str, line: str) -> None:
    add_rect(x, y, w, h, "", fill, line, line_pt=0.6, round_px=2)
    for i in range(1, cols):
        xx = x + w * i / cols
        add_line(xx, y, xx, y + h, line, 0.45)
    for i in range(1, rows):
        yy = y + h * i / rows
        add_line(x, yy, x + w, yy, line, 0.45)


def graph_icon(x: float, y: float, w: float, h: float, nonlocal_edges: bool, accent: str) -> None:
    add_rect(x, y, w, h, "", C["white"], accent, line_pt=0.7, round_px=3)
    points = [
        (x + 0.22 * w, y + 0.28 * h),
        (x + 0.50 * w, y + 0.18 * h),
        (x + 0.78 * w, y + 0.30 * h),
        (x + 0.32 * w, y + 0.72 * h),
        (x + 0.67 * w, y + 0.70 * h),
    ]
    edges = (
        [(0, 2), (0, 4), (1, 3), (1, 4), (2, 3), (2, 4)]
        if nonlocal_edges
        else [(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4)]
    )
    for a, b in edges:
        add_line(*points[a], *points[b], accent, 0.65, dash=nonlocal_edges)
    for cx, cy in points:
        add_oval(cx - 4, cy - 4, 8, 8, accent)


def header(x: float, y: float, w: float, text: str, fill: str, line: str) -> None:
    add_rect(x, y, w, 30, text, fill, line, 11, True, 1.0, round_px=5)


def _build_drawing_previous_layout() -> None:
    """Draw the three-branch encoder, gated token fusion, and classifier."""
    add_rect(0, 0, REF_W, REF_H, "", C["white"], C["white"], line_pt=0, round_px=0)
    add_rect(790, 62, 270, 62, "", C["teal_soft"], C["teal"], line_pt=0.9, round_px=0)
    add_rect(245, 345, 220, 36, "", C["white"], C["green"], line_pt=0.7, dash=True, round_px=0)
    add_rect(1220, 220, 258, 160, "", C["white"], C["mid_gray"], line_pt=0.8, round_px=0)
    add_rect(24, 260, 112, 80, "Flow X\n[B, 30, 3]\nlen / dir / IAT", C["white"], C["gray"], 5.0, True, 0.9, round_px=0)

    add_text(24, 8, 650, 24, "MVIF-Net architecture", 8.5, C["ink"], True)
    add_text(24, 32, 820, 14, "Three packet views with gated fusion and attention-based classification", 5.0, C["gray"])
    lane_y = (155, 300, 445)

    # Packet input feeds the three encoders and a shared adjacency constructor.
    add_line(136, 300, 155, 300, C["ink"], 0.8)
    add_line(155, lane_y[0], 155, lane_y[2], C["ink"], 0.8)
    for cy in lane_y:
        arrow(155, cy, 170, cy, C["ink"], 0.75)
    add_line(136, 340, 136, 363, C["green"], 0.65, dash=True)
    add_line(136, 363, 245, 363, C["green"], 0.65, dash=True)
    arrow(245, 363, 245, 363, C["green"], 0.65)
    add_line(297, 345, 297, 325, C["green"], 0.65, arrow=True, dash=True)
    add_line(413, 345, 413, 325, C["green"], 0.65, arrow=True, dash=True)

    # Main branch flows remain separate through their own gate-weighted scales.
    branch_colors = (C["blue"], C["green"], C["orange"])
    for cy, color in zip(lane_y, branch_colors):
        arrow(735, cy, 790, cy, color, 0.75)
    for cy in lane_y:
        arrow(922, cy, 950, cy, C["teal"], 0.7)
    add_line(950, lane_y[0], 950, lane_y[2], C["teal"], 0.75)
    arrow(950, 300, 980, 300, C["teal"], 0.75)
    arrow(1090, 300, 1105, 300, C["teal"], 0.75)

    # Bounded residual shortcuts cross the graph and DFT branch blocks.
    add_line(248, 300, 248, 265, C["green"], 0.8)
    add_line(248, 265, 355, 265, C["green"], 0.8)
    arrow(355, 265, 355, 291, C["green"], 0.8)
    add_line(410, 445, 410, 481, C["orange"], 0.8)
    add_line(410, 481, 505, 481, C["orange"], 0.8)
    arrow(505, 481, 505, 454, C["orange"], 0.8)

    # Attention and FFN shortcuts rejoin after their respective sublayers.
    arrow(1105, 300, 1235, 300, C["teal"], 0.75)
    add_line(1228, 300, 1228, 255, C["teal"], 0.7)
    add_line(1228, 255, 1317, 255, C["teal"], 0.7)
    arrow(1317, 255, 1317, 291, C["teal"], 0.7)
    arrow(1307, 300, 1308, 300, C["ink"], 0.6)
    arrow(1326, 300, 1333, 300, C["ink"], 0.6)
    add_line(1326, 300, 1326, 342, C["teal"], 0.7)
    add_line(1326, 342, 1418, 342, C["teal"], 0.7)
    arrow(1418, 342, 1418, 309, C["teal"], 0.7)
    arrow(1408, 300, 1409, 300, C["ink"], 0.6)
    arrow(1427, 300, 1460, 300, C["teal"], 0.75)
    arrow(1562, 300, 1572, 300, C["teal"], 0.75)
    arrow(1654, 300, 1666, 300, C["teal"], 0.75)

    # Temporal branch: two serial Mamba mixers, without a residual shortcut.
    add_text(170, 105, 565, 16, "Temporal branch", 5.7, C["blue"], True)
    add_rect(170, 131, 78, 48, "Linear\n3 -> 256", C["blue_soft"], C["blue"], 5.2, True, 0.75, round_px=0)
    arrow(248, 155, 258, 155, C["ink"], 0.65)
    add_rect(258, 131, 96, 48, "Mamba x2", C["blue_soft"], C["blue"], 5.2, True, 0.75, round_px=0)
    arrow(354, 155, 364, 155, C["ink"], 0.65)
    add_rect(364, 131, 93, 48, "LayerNorm", C["blue_soft"], C["blue"], 5.1, True, 0.75, round_px=0)
    arrow(457, 155, 467, 155, C["ink"], 0.65)
    add_rect(467, 131, 120, 48, "Packet position\n+ branch type", C["blue_soft"], C["blue"], 4.8, True, 0.75, round_px=0)
    arrow(587, 155, 597, 155, C["ink"], 0.65)
    add_rect(597, 131, 138, 48, "BranchNorm\n30 packet tokens", C["blue_soft"], C["blue"], 4.9, True, 0.75, round_px=0)

    # Packet graph: a shared A(X) feeds both graph blocks; alpha_g scales the shortcut.
    add_text(170, 229, 565, 15, "Packet-graph branch", 5.7, C["green"], True)
    add_text(264, 246, 210, 12, "alpha_g x graph embedding", 4.3, C["green"], True)
    add_rect(170, 276, 78, 48, "Linear\n3 -> 256", C["green_soft"], C["green"], 5.2, True, 0.75, round_px=0)
    arrow(248, 300, 258, 300, C["ink"], 0.65)
    add_rect(258, 276, 78, 48, "Graph\nblock 1", C["green_soft"], C["green"], 4.9, True, 0.75, round_px=0)
    arrow(336, 300, 346, 300, C["ink"], 0.65)
    sum_node(355, 300, C["green"], 18)
    arrow(364, 300, 374, 300, C["ink"], 0.65)
    add_rect(374, 276, 78, 48, "Graph\nblock 2", C["green_soft"], C["green"], 4.9, True, 0.75, round_px=0)
    arrow(452, 300, 462, 300, C["ink"], 0.65)
    add_rect(462, 276, 112, 48, "LayerNorm\n+ position/type", C["green_soft"], C["green"], 4.7, True, 0.75, round_px=0)
    arrow(574, 300, 584, 300, C["ink"], 0.65)
    add_rect(584, 276, 151, 48, "BranchNorm\n30 packet tokens", C["green_soft"], C["green"], 4.9, True, 0.75, round_px=0)
    add_text(248, 348, 214, 30, "Shared adjacency A(X)\nlocal + feature kNN (k = 4)", 4.25, C["green"], True)

    # DFT branch: 30-point rFFT, six real/imag channels, and one bounded shortcut.
    add_text(170, 395, 565, 16, "DFT spectral branch", 5.7, C["orange"], True)
    add_rect(170, 421, 63, 48, "rFFT\n30 -> 16", C["orange_soft"], C["orange"], 4.8, True, 0.75, round_px=0)
    arrow(233, 445, 243, 445, C["ink"], 0.65)
    add_rect(243, 421, 83, 48, "Real / imag\n6 channels + LN", C["orange_soft"], C["orange"], 4.35, True, 0.75, round_px=0)
    arrow(326, 445, 336, 445, C["ink"], 0.65)
    add_rect(336, 421, 74, 48, "1 x 1\nprojection", C["orange_soft"], C["orange"], 4.6, True, 0.75, round_px=0)
    arrow(410, 445, 420, 445, C["ink"], 0.65)
    add_rect(420, 421, 69, 48, "Conv\nk = 1", C["orange_soft"], C["orange"], 4.7, True, 0.75, round_px=0)
    arrow(489, 445, 496, 445, C["ink"], 0.6)
    sum_node(505, 445, C["orange"], 18)
    arrow(514, 445, 522, 445, C["ink"], 0.65)
    add_rect(522, 421, 69, 48, "Conv\nk = 3", C["orange_soft"], C["orange"], 4.7, True, 0.75, round_px=0)
    arrow(591, 445, 601, 445, C["ink"], 0.65)
    add_rect(601, 421, 134, 48, "LayerNorm\n+ position/type\nBranchNorm / 16 tok.", C["orange_soft"], C["orange"], 4.2, True, 0.75, round_px=0)
    add_text(420, 483, 205, 12, "alpha_f x projected input", 4.5, C["orange"], True)

    # One global gate controls three separate scaling rows; only scaled tokens concatenate.
    add_rect(798, 67, 254, 54, "Branch Gate\nmasked means -> MLP -> Softmax\ng_T, g_G, g_F", C["teal_soft"], C["teal"], 4.45, True, 0.8, round_px=0)
    add_rect(790, 131, 132, 48, "3 g_T x T_T", C["blue_soft"], C["blue"], 4.9, True, 0.75, round_px=0)
    add_rect(790, 276, 132, 48, "3 g_G x T_G", C["green_soft"], C["green"], 4.9, True, 0.75, round_px=0)
    add_rect(790, 421, 132, 48, "3 g_F x T_F", C["orange_soft"], C["orange"], 4.9, True, 0.75, round_px=0)
    add_rect(980, 276, 110, 48, "Concatenate\n76 tokens", C["white"], C["teal"], 4.6, True, 0.75, round_px=0)
    add_rect(1105, 270, 110, 60, "Token fusion\nLinear + GELU\n+ Dropout", C["white"], C["teal"], 4.25, True, 0.75, round_px=0)

    # Attention, residual FFN, global masked pooling, and a variable class head.
    add_text(1225, 225, 246, 18, "Attention (4 heads) + FFN", 5.25, C["teal"], True)
    add_rect(1235, 276, 72, 48, "LayerNorm\nAttention", C["white"], C["teal"], 4.35, True, 0.7, round_px=0)
    sum_node(1317, 300, C["teal"], 18)
    add_rect(1333, 276, 75, 48, "LayerNorm\nFFN 256 -> 1024 -> 256", C["white"], C["teal"], 4.05, True, 0.7, round_px=0)
    sum_node(1418, 300, C["teal"], 18)
    add_text(1228, 348, 244, 14, "Padding positions masked in attention", 4.0, C["gray"])
    add_rect(1460, 266, 102, 68, "LayerNorm\nGlobal masked\nmean", C["white"], C["teal"], 4.4, True, 0.75, round_px=0)
    add_rect(1572, 266, 82, 68, "Linear\n256 -> C", C["white"], C["teal"], 4.7, True, 0.75, round_px=0)
    add_rect(1666, 266, 122, 68, "Traffic type\nC classes", C["teal_soft"], C["teal"], 4.7, True, 0.85, round_px=0)

    add_line(24, 610, 1788, 610, C["mid_gray"], 0.6)
    add_text(28, 620, 1070, 16, "Solid arrows = token flow  |  dashed arrows = shared adjacency  |  + = residual addition", 4.7, C["gray"])
    add_text(1150, 620, 630, 16, "C = 60 closed-set / 61 open-set classes  |  76 tokens", 4.7, C["gray"], True)
def build_drawing() -> None:
    """Draw a compact, paper-style three-branch MVIF-Net architecture."""
    add_rect(0, 0, REF_W, REF_H, "", C["white"], C["white"], line_pt=0, round_px=0)
    add_rect(740, 28, 220, 58, "Branch gate\nmasked means -> MLP\nSoftmax: g_T, g_G, g_F", C["teal_soft"], C["teal"], 3.9, True, 0.8, round_px=0)
    add_rect(20, 233, 96, 74, "Flow X\n[B, 30, 3]\nlength / dir / IAT", C["white"], C["gray"], 4.9, True, 0.9, round_px=0)
    add_rect(1220, 205, 230, 126, "", C["white"], C["mid_gray"], line_pt=0.75, round_px=0)
    add_rect(241, 307, 245, 38, "Shared A(X): local + feature kNN (k = 4)", C["white"], C["green"], 4.15, True, 0.7, round_px=0)

    add_text(20, 8, 560, 20, "MVIF-Net", 8.0, C["ink"], True)
    add_text(20, 29, 560, 14, "Three parallel views -> gated token fusion -> traffic type", 4.8, C["gray"])
    lane_y = (142, 270, 398)
    scale_x = 850
    collect_x = 970

    # One input fans out into three compact encoder lanes.
    add_line(116, 270, 134, 270, C["ink"], 0.75)
    add_line(134, lane_y[0], 134, lane_y[2], C["ink"], 0.75)
    for cy in lane_y:
        arrow(134, cy, 150, cy, C["ink"], 0.7)

    # Dashed gate signals feed the three multiply nodes; token paths stay separate.
    add_line(scale_x, 86, scale_x, 130, C["teal"], 0.7, arrow=True, dash=True)
    add_line(scale_x, 154, scale_x, 258, C["teal"], 0.7, arrow=True, dash=True)
    add_line(scale_x, 282, scale_x, 386, C["teal"], 0.7, arrow=True, dash=True)
    for cy in lane_y:
        add_line(scale_x + 12, cy, collect_x, cy, C["teal"], 0.7, arrow=True)
    add_line(collect_x, lane_y[0], collect_x, lane_y[2], C["teal"], 0.7)
    arrow(collect_x, lane_y[1], 990, lane_y[1], C["teal"], 0.7)
    arrow(1085, lane_y[1], 1103, lane_y[1], C["teal"], 0.7)
    arrow(1198, lane_y[1], 1220, lane_y[1], C["teal"], 0.7)

    # Bounded graph and spectral residuals bypass one block and meet at additions.
    add_line(220, 270, 220, 239, C["green"], 0.75)
    add_line(220, 239, 316, 239, C["green"], 0.75)
    arrow(316, 239, 316, 260, C["green"], 0.75)
    add_text(280, 230, 38, 8, "alpha_g", 3.3, C["green"], True)
    add_line(400, 398, 400, 432, C["orange"], 0.75)
    add_line(400, 432, 490, 432, C["orange"], 0.75)
    arrow(490, 432, 490, 409, C["orange"], 0.75)
    add_text(409, 434, 96, 10, "alpha_f * F_in", 4.0, C["orange"], True)

    # Attention and FFN each have a cross-layer residual that rejoins after the sublayer.
    add_line(1211, lane_y[1], 1211, 234, C["teal"], 0.65)
    add_line(1211, 234, 1304, 234, C["teal"], 0.65)
    arrow(1304, 234, 1304, 255, C["teal"], 0.65)
    arrow(1292, lane_y[1], 1295, lane_y[1], C["ink"], 0.55)
    arrow(1313, lane_y[1], 1320, lane_y[1], C["ink"], 0.55)
    add_line(1314, lane_y[1], 1314, 314, C["teal"], 0.65)
    add_line(1314, 314, 1404, 314, C["teal"], 0.65)
    arrow(1404, 314, 1404, 284, C["teal"], 0.65)
    arrow(1413, lane_y[1], 1432, lane_y[1], C["teal"], 0.7)
    arrow(1450, lane_y[1], 1465, lane_y[1], C["teal"], 0.7)
    arrow(1558, lane_y[1], 1572, lane_y[1], C["teal"], 0.7)
    arrow(1644, lane_y[1], 1657, lane_y[1], C["teal"], 0.7)

    # Temporal view.
    add_text(150, 99, 500, 14, "Temporal branch", 5.35, C["blue"], True)
    add_rect(150, 120, 70, 44, "Linear\n3 -> 256", C["blue_soft"], C["blue"], 4.6, True, 0.7, round_px=0)
    arrow(220, lane_y[0], 235, lane_y[0], C["ink"], 0.6)
    add_rect(235, 120, 90, 44, "Mamba x 2", C["blue_soft"], C["blue"], 4.8, True, 0.7, round_px=0)
    arrow(325, lane_y[0], 340, lane_y[0], C["ink"], 0.6)
    add_rect(340, 120, 120, 44, "LayerNorm\n+ position/type", C["blue_soft"], C["blue"], 4.3, True, 0.7, round_px=0)
    arrow(460, lane_y[0], 475, lane_y[0], C["ink"], 0.6)
    add_rect(475, 120, 125, 44, "BranchNorm\n30 packet tokens", C["blue_soft"], C["blue"], 4.55, True, 0.7, round_px=0)
    arrow(600, lane_y[0], 838, lane_y[0], C["blue"], 0.7)

    # Packet graph view with shared raw-input adjacency and a bypass around graph block 1.
    add_text(150, 216, 500, 14, "Packet-graph branch", 5.35, C["green"], True)
    add_rect(150, 248, 70, 44, "Linear\n3 -> 256", C["green_soft"], C["green"], 4.6, True, 0.7, round_px=0)
    arrow(220, lane_y[1], 235, lane_y[1], C["ink"], 0.6)
    add_rect(235, 248, 68, 44, "Graph\nblock 1", C["green_soft"], C["green"], 4.3, True, 0.7, round_px=0)
    arrow(303, lane_y[1], 307, lane_y[1], C["ink"], 0.55)
    sum_node(316, lane_y[1], C["green"], 18)
    arrow(325, lane_y[1], 330, lane_y[1], C["ink"], 0.55)
    add_rect(330, 248, 68, 44, "Graph\nblock 2", C["green_soft"], C["green"], 4.3, True, 0.7, round_px=0)
    arrow(398, lane_y[1], 410, lane_y[1], C["ink"], 0.6)
    add_rect(410, 248, 110, 44, "LayerNorm\n+ position/type", C["green_soft"], C["green"], 4.1, True, 0.7, round_px=0)
    arrow(520, lane_y[1], 535, lane_y[1], C["ink"], 0.6)
    add_rect(535, 248, 125, 44, "BranchNorm\n30 packet tokens", C["green_soft"], C["green"], 4.5, True, 0.7, round_px=0)
    arrow(660, lane_y[1], 838, lane_y[1], C["green"], 0.7)
    add_line(283, 307, 283, 292, C["green"], 0.6, arrow=True, dash=True)
    add_line(364, 307, 364, 292, C["green"], 0.6, arrow=True, dash=True)

    # DFT view uses a 30-point spectrum and a residual around the first convolution.
    add_text(150, 344, 500, 14, "DFT spectral branch", 5.35, C["orange"], True)
    add_rect(150, 376, 65, 44, "rFFT\n30 -> 16", C["orange_soft"], C["orange"], 4.4, True, 0.7, round_px=0)
    arrow(215, lane_y[2], 230, lane_y[2], C["ink"], 0.6)
    add_rect(230, 376, 85, 44, "Real / imag\n6 ch + LN", C["orange_soft"], C["orange"], 4.0, True, 0.7, round_px=0)
    arrow(315, lane_y[2], 330, lane_y[2], C["ink"], 0.6)
    add_rect(330, 376, 70, 44, "1 x 1\nprojection", C["orange_soft"], C["orange"], 4.2, True, 0.7, round_px=0)
    arrow(400, lane_y[2], 415, lane_y[2], C["ink"], 0.6)
    add_rect(415, 376, 64, 44, "Conv\nk = 1", C["orange_soft"], C["orange"], 4.3, True, 0.7, round_px=0)
    arrow(479, lane_y[2], 481, lane_y[2], C["ink"], 0.55)
    sum_node(490, lane_y[2], C["orange"], 18)
    arrow(499, lane_y[2], 505, lane_y[2], C["ink"], 0.55)
    add_rect(505, 376, 65, 44, "Conv\nk = 3", C["orange_soft"], C["orange"], 4.3, True, 0.7, round_px=0)
    arrow(570, lane_y[2], 585, lane_y[2], C["ink"], 0.6)
    add_rect(585, 376, 132, 44, "LayerNorm\n+ position/type\nBranchNorm | 16 tok.", C["orange_soft"], C["orange"], 3.4, True, 0.7, round_px=0)
    arrow(717, lane_y[2], 838, lane_y[2], C["orange"], 0.7)

    # Gate-weighted views concatenate only after per-view scaling.
    for cy, color, name in zip(lane_y, (C["blue"], C["green"], C["orange"]), ("T", "G", "F")):
        multiply_node(scale_x, cy, color, 22)
        add_text(scale_x + 14, cy - 26, 52, 14, f"3 g_{name}", 4.0, color, True)
    add_rect(990, 240, 95, 60, "Concatenate\n30 + 30 + 16\n= 76 tokens", C["white"], C["teal"], 4.0, True, 0.7, round_px=0)
    add_rect(1103, 240, 95, 60, "Token fusion\nLinear + GELU\n+ Dropout", C["white"], C["teal"], 3.95, True, 0.7, round_px=0)

    # Attention block with two visible residual bypasses.
    add_text(1220, 210, 230, 18, "Attention (4 heads) + FFN", 4.9, C["teal"], True)
    add_rect(1222, 244, 70, 42, "LayerNorm\nAttention", C["white"], C["teal"], 3.9, True, 0.65, round_px=0)
    sum_node(1304, lane_y[1], C["teal"], 18)
    add_rect(1320, 244, 74, 42, "LayerNorm\nFFN", C["white"], C["teal"], 3.8, True, 0.65, round_px=0)
    add_text(1319, 290, 76, 12, "256 -> 1024 -> 256", 3.0, C["gray"])
    sum_node(1404, lane_y[1], C["teal"], 18)
    add_rect(1465, 239, 93, 62, "LayerNorm\nGlobal masked\nmean", C["white"], C["teal"], 4.15, True, 0.7, round_px=0)
    add_rect(1572, 239, 72, 62, "Linear\n256 -> C", C["white"], C["teal"], 4.35, True, 0.7, round_px=0)
    add_rect(1657, 239, 118, 62, "Traffic type\nC classes", C["teal_soft"], C["teal"], 4.35, True, 0.8, round_px=0)

    add_line(20, 458, 1778, 458, C["mid_gray"], 0.55)
    add_text(24, 467, 1030, 14, "Solid = token flow  |  dashed teal = gate weights  |  dashed green = graph adjacency  |  + = residual addition", 4.05, C["gray"])
    add_text(1190, 467, 585, 14, "C = 60 closed-set / 61 open-set classes", 4.35, C["gray"], True)


def qname(name: str) -> str:
    return f"{{{VISIO_NS}}}{name}"


def add_cell(parent: ET.Element, name: str, value: str, unit: str | None = None, formula: str | None = None) -> None:
    attrs = {"N": name, "V": value}
    if unit:
        attrs["U"] = unit
    if formula:
        attrs["F"] = formula
    ET.SubElement(parent, qname("Cell"), attrs)


def visio_shape(index: int, item: dict) -> ET.Element:
    name = f"MVIF-{item['kind']}-{index}"
    shape = ET.Element(qname("Shape"), {"ID": str(index), "Type": "Shape", "NameU": name, "Name": name})

    if item["kind"] == "line":
        x1, y1, x2, y2 = (item[key] for key in ("x1", "y1", "x2", "y2"))
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        w_px, h_px = max(right - left, 1.0), max(bottom - top, 1.0)
        cx = (left + right) / 2 / PX_PER_IN
        cy = PAGE_H - ((top + bottom) / 2 / PX_PER_IN)
        w, h = w_px / PX_PER_IN, h_px / PX_PER_IN
        add_cell(shape, "PinX", f"{cx:.6f}")
        add_cell(shape, "PinY", f"{cy:.6f}")
        add_cell(shape, "Width", f"{w:.6f}")
        add_cell(shape, "Height", f"{h:.6f}")
        add_cell(shape, "LocPinX", f"{w / 2:.6f}", formula="Width*0.5")
        add_cell(shape, "LocPinY", f"{h / 2:.6f}", formula="Height*0.5")
        add_cell(shape, "FillPattern", "0")
        line_color = item["line"] if item["line"] != "none" else C["white"]
        add_cell(
            shape,
            "LineColor",
            line_color,
            formula=f"RGB{tuple(bytes.fromhex(line_color[1:]))}",
        )
        add_cell(shape, "LineWeight", f"{item['line_pt']:.3f}", "PT")
        add_cell(shape, "LinePattern", "2" if item["dash"] else "1")
        add_cell(shape, "BeginArrow", "0")
        add_cell(shape, "EndArrow", "4" if item["arrow"] else "0")
        section = ET.SubElement(shape, qname("Section"), {"N": "Geometry", "IX": "0"})
        add_cell(section, "NoFill", "1")
        lx1 = 0.5 if right == left else (x1 - left) / (right - left)
        lx2 = 0.5 if right == left else (x2 - left) / (right - left)
        ly1 = 0.5 if bottom == top else (bottom - y1) / (bottom - top)
        ly2 = 0.5 if bottom == top else (bottom - y2) / (bottom - top)
        for row_ix, (row_type, px, py) in enumerate((("RelMoveTo", lx1, ly1), ("RelLineTo", lx2, ly2)), 1):
            row = ET.SubElement(section, qname("Row"), {"T": row_type, "IX": str(row_ix)})
            add_cell(row, "X", f"{px:.6f}")
            add_cell(row, "Y", f"{py:.6f}")
        return shape

    x, y, w, h = item["x"], item["y"], item["w"], item["h"]
    pin_x = (x + w / 2) / PX_PER_IN
    pin_y = PAGE_H - (y + h / 2) / PX_PER_IN
    visio_w, visio_h = w / PX_PER_IN, h / PX_PER_IN
    add_cell(shape, "PinX", f"{pin_x:.6f}")
    add_cell(shape, "PinY", f"{pin_y:.6f}")
    add_cell(shape, "Width", f"{visio_w:.6f}")
    add_cell(shape, "Height", f"{visio_h:.6f}")
    add_cell(shape, "LocPinX", f"{visio_w / 2:.6f}", formula="Width*0.5")
    add_cell(shape, "LocPinY", f"{visio_h / 2:.6f}", formula="Height*0.5")
    line_color = item["line"] if item["line"] != "none" else C["white"]
    add_cell(shape, "LineColor", line_color, formula=f"RGB{tuple(bytes.fromhex(line_color[1:]))}")
    add_cell(shape, "LineWeight", f"{item['line_pt']:.3f}", "PT")
    add_cell(shape, "LinePattern", "2" if item["dash"] else ("0" if item["line"] == "none" else "1"))
    fill_color = item["fill"] if item["fill"] != "none" else C["white"]
    add_cell(shape, "FillForegnd", fill_color, formula=f"RGB{tuple(bytes.fromhex(fill_color[1:]))}")
    add_cell(shape, "FillPattern", "0" if item["fill"] == "none" else "1")
    if item["round_px"]:
        add_cell(shape, "Rounding", f"{item['round_px'] / PX_PER_IN:.6f}")

    section = ET.SubElement(shape, qname("Section"), {"N": "Geometry", "IX": "0"})
    add_cell(section, "NoFill", "1" if item["fill"] == "none" else "0")
    add_cell(section, "NoLine", "1" if item["line"] == "none" else "0")
    if item["kind"] == "oval":
        row = ET.SubElement(section, qname("Row"), {"T": "Ellipse", "IX": "1"})
        add_cell(row, "X", "0.5")
        add_cell(row, "Y", "0.5")
        add_cell(row, "A", "0.5")
        add_cell(row, "B", "0")
        add_cell(row, "C", "0")
        add_cell(row, "D", "0.5")
    else:
        points = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        for row_ix, (row_type, (px, py)) in enumerate(
            zip(("RelMoveTo", "RelLineTo", "RelLineTo", "RelLineTo", "RelLineTo"), points), 1
        ):
            row = ET.SubElement(section, qname("Row"), {"T": row_type, "IX": str(row_ix)})
            add_cell(row, "X", str(px))
            add_cell(row, "Y", str(py))

    if item.get("text"):
        char = ET.SubElement(shape, qname("Section"), {"N": "Character", "IX": "0"})
        row = ET.SubElement(char, qname("Row"), {"IX": "0"})
        add_cell(row, "Font", "0")
        add_cell(row, "Size", f"{item['size']:.3f}", "PT")
        add_cell(row, "Color", item["color"], formula=f"RGB{tuple(bytes.fromhex(item['color'][1:]))}")
        add_cell(row, "Style", str((1 if item["bold"] else 0) + (2 if item["italic"] else 0)))
        para = ET.SubElement(shape, qname("Section"), {"N": "Paragraph", "IX": "0"})
        prow = ET.SubElement(para, qname("Row"), {"IX": "0"})
        add_cell(prow, "HorzAlign", "1")
        add_cell(shape, "VerticalAlign", "1")
        for margin in ("LeftMargin", "RightMargin", "TopMargin", "BottomMargin"):
            add_cell(shape, margin, "0.010000")
        text = ET.SubElement(shape, qname("Text"))
        text.text = item["text"]
    return shape


def build_vsdx() -> None:
    if not VSDX.exists():
        raise FileNotFoundError(f"Blank Visio template not found: {VSDX}")
    backup = VSDX.with_name(f"{VSDX.stem}.backup{VSDX.suffix}")
    if not backup.exists():
        shutil.copy2(VSDX, backup)
        print(f"Backup: {backup}")
    else:
        print(f"Keeping existing backup: {backup}")

    root = ET.Element(qname("PageContents"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
    shapes = ET.SubElement(root, qname("Shapes"))
    for index, item in enumerate(SHAPES, 1):
        shapes.append(visio_shape(index, item))
    page_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    temp_path = VSDX.with_suffix(".tmp.vsdx")
    with zipfile.ZipFile(VSDX, "r") as source, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "visio/pages/page1.xml":
                data = page_xml
            elif info.filename == "visio/pages/pages.xml":
                data = resize_pages_xml(data)
            elif info.filename == "visio/document.xml":
                data = set_document_font(data)
            target.writestr(info, data)
    os.replace(temp_path, VSDX)
    print(f"VSDX: {VSDX} ({VSDX.stat().st_size} bytes; {len(SHAPES)} editable shapes)")


def resize_pages_xml(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for cell in root.findall(f".//{qname('Cell')}"):
        if cell.attrib.get("N") == "PageWidth":
            cell.set("V", str(PAGE_W))
        elif cell.attrib.get("N") == "PageHeight":
            cell.set("V", str(PAGE_H))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def set_document_font(data: bytes) -> bytes:
    root = ET.fromstring(data)
    face_names = root.find(qname("FaceNames"))
    if face_names is not None:
        faces = face_names.findall(qname("FaceName"))
        if faces:
            faces[0].set("NameU", "Times New Roman")
            faces[0].set("UnicodeRanges", "-1 -1 -1 0")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def svg_text(item: dict) -> str:
    value = item["text"]
    lines = value.splitlines() or [value]
    font_size = item["size"] * PX_PER_IN / 72
    line_height = font_size * 1.15
    first_y = item["y"] + item["h"] / 2 - (len(lines) - 1) * line_height / 2 + font_size * 0.34
    weight = "700" if item["bold"] else "400"
    style = "italic" if item["italic"] else "normal"
    tspans = "".join(
        f'<tspan x="{item["x"] + item["w"] / 2:.2f}" y="{first_y + i * line_height:.2f}">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return (
        f'<text text-anchor="middle" dominant-baseline="middle" '
        f'font-family="Times New Roman,serif" font-size="{font_size:.2f}" '
        f'font-weight="{weight}" font-style="{style}" fill="{item["color"]}">{tspans}</text>'
    )


def build_svg() -> None:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}in" height="{PAGE_H}in" viewBox="0 0 {REF_W:.0f} {REF_H:.0f}">',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 z" fill="context-stroke"/></marker></defs>',
        f'<rect width="{REF_W:.0f}" height="{REF_H:.0f}" fill="#FFFFFF"/>',
    ]
    for item in SHAPES:
        if item["kind"] == "line":
            dash = ' stroke-dasharray="5 4"' if item["dash"] else ""
            marker = ' marker-end="url(#arrow)"' if item["arrow"] else ""
            parts.append(
                f'<line x1="{item["x1"]:.2f}" y1="{item["y1"]:.2f}" x2="{item["x2"]:.2f}" y2="{item["y2"]:.2f}" '
                f'stroke="{item["line"]}" stroke-width="{item["line_pt"] * PX_PER_IN / 72:.2f}"{dash}{marker}/>'
            )
            continue
        if item["kind"] == "oval":
            parts.append(
                f'<ellipse cx="{item["x"] + item["w"] / 2:.2f}" cy="{item["y"] + item["h"] / 2:.2f}" '
                f'rx="{item["w"] / 2:.2f}" ry="{item["h"] / 2:.2f}" fill="{item["fill"]}" '
                f'stroke="{item["line"]}" stroke-width="{item["line_pt"] * PX_PER_IN / 72:.2f}"/>'
            )
            continue
        fill = "none" if item["fill"] == "none" else item["fill"]
        stroke = "none" if item["line"] == "none" else item["line"]
        dash = ' stroke-dasharray="6 5"' if item["dash"] else ""
        parts.append(
            f'<rect x="{item["x"]:.2f}" y="{item["y"]:.2f}" width="{item["w"]:.2f}" height="{item["h"]:.2f}" '
            f'rx="{item["round_px"]:.2f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{item["line_pt"] * PX_PER_IN / 72:.2f}"{dash}/>'
        )
        if item["text"]:
            parts.append(svg_text(item))
    parts.append("</svg>")
    SVG.write_text("\n".join(parts), encoding="utf-8")
    print(f"SVG: {SVG} ({SVG.stat().st_size} bytes)")


def render_png() -> None:
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.exists():
        print("PNG preview skipped: Microsoft Edge not found; SVG remains available.")
        return
    svg_source = SVG.read_text(encoding="utf-8")
    physical_size = f'width="{PAGE_W}in" height="{PAGE_H}in"'
    preview_size = f'width="{DRAW_W:.0f}px" height="{DRAW_H:.0f}px"'
    preview_source = svg_source.replace(physical_size, preview_size, 1)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            preview_svg = Path(temp_dir) / SVG.name
            preview_svg.write_text(preview_source, encoding="utf-8")
            command = [
                str(edge),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--disable-extensions",
                "--hide-scrollbars",
                "--window-size=1800,500",
                f"--screenshot={PNG}",
                preview_svg.resolve().as_uri(),
            ]
            subprocess.run(command, check=True, timeout=45, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if PNG.exists():
            print(f"PNG preview: {PNG} ({PNG.stat().st_size} bytes)")
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"PNG preview skipped: {exc}")


def validate_package() -> None:
    with zipfile.ZipFile(VSDX) as package:
        for name in package.namelist():
            if name.endswith((".xml", ".rels")):
                ET.fromstring(package.read(name))
        page = ET.fromstring(package.read("visio/pages/page1.xml"))
        shapes = page.findall(f".//{qname('Shape')}")
        shape_count = len(shapes)
        ids = [shape.attrib["ID"] for shape in shapes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate Visio shape IDs")
        if any(shape.find(f"{qname('Section')}[@N='Geometry']") is None for shape in shapes):
            raise ValueError("A Visio shape is missing editable geometry")
        media = [name for name in package.namelist() if name.startswith("visio/media/")]
        text = " ".join(" ".join((node.text or "").split()) for node in page.findall(f".//{qname('Text')}"))
        pages = ET.fromstring(package.read("visio/pages/pages.xml"))
        page_cells = {cell.attrib.get("N"): float(cell.attrib["V"]) for cell in pages.findall(f".//{qname('Cell')}")}
    if page_cells.get("PageWidth") != PAGE_W or page_cells.get("PageHeight") != PAGE_H:
        raise ValueError(f"Unexpected Visio page size: {page_cells.get('PageWidth')} x {page_cells.get('PageHeight')}")
    labels = [
        "Temporal branch",
        "Packet-graph branch",
        "DFT spectral branch",
        "Branch gate",
        "Concatenate",
        "Attention (4 heads) + FFN",
        "Global masked mean",
        "Traffic type",
        "76 tokens",
    ]
    missing = [label for label in labels if label not in text]
    if missing:
        raise ValueError(f"Required labels missing from editable page: {missing}")
    if "SDPA" in text:
        raise ValueError("The architecture figure should use the label Attention, not SDPA")
    if media:
        raise ValueError(f"Unexpected embedded media: {media}")
    if not SVG.exists() or SVG.stat().st_size == 0:
        raise ValueError("SVG preview is missing or empty")
    png_data = PNG.read_bytes()
    if png_data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Preview is not a PNG")
    png_w, png_h = struct.unpack(">II", png_data[16:24])
    if (png_w, png_h) != (1800, 500):
        raise ValueError(f"Unexpected PNG dimensions: {png_w} x {png_h}")
    print(
        f"Package check: {shape_count} native shapes; XML parts parse; unique IDs; "
        f"page={PAGE_W}x{PAGE_H} in; media=0; required labels={len(labels)}/{len(labels)}; PNG={png_w}x{png_h}"
    )


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    build_drawing()
    build_vsdx()
    build_svg()
    render_png()
    validate_package()
