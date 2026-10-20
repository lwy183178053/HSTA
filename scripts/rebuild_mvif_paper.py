"""Rebuild the MVIF-Net manuscript from the formal result snapshots.

The template is never edited in place. Paragraph and table positions are kept
from the supplied manuscript, while result values are read from the final
run-level CSV/JSON snapshots.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
import os
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph


MODEL_ORDER = ["30pktTCNET", "NetMamba", "SRViT", "TrafficAudio", "BPF-GNN", "MVIF-Net"]
MODEL_MAP = {
    "mvif-net": "MVIF-Net",
    "30pkttcnet-adapted": "30pktTCNET",
    "netmamba-adapted": "NetMamba",
    "srvit-adapted": "SRViT",
    "srvit": "SRViT",
    "trafficaudio-adapted": "TrafficAudio",
    "trafficaudio": "TrafficAudio",
    "bpf-gnn": "BPF-GNN",
    "bpfgnn": "BPF-GNN",
}
DATASET_MAP = {"tls60": "CESNET-TLS22", "quic60": "CESNET-QUIC22"}
DATASET_SHORT = {value: key[:3].upper() for key, value in DATASET_MAP.items()}
CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*[,，–-]\s*\d+)*)\]")


def _set_paragraph_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run._element.getparent().remove(run._element)
    else:
        paragraph.add_run(text)


def _set_cell_text(cell, text: str) -> None:
    paragraph = cell.paragraphs[0]
    _set_paragraph_text(paragraph, text)
    for paragraph in cell.paragraphs[1:]:
        paragraph._element.getparent().remove(paragraph._element)


def _format_two_decimals(value: str | Decimal | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _format_result_stat(value: str) -> str:
    match = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?)\s*±\s*([-+]?\d+(?:\.\d+)?)\s*", value)
    if match is None:
        return value
    return f"{_format_two_decimals(match.group(1))}±{_format_two_decimals(match.group(2))}"


def _get_or_add(parent, tag: str):
    element = parent.find(qn(tag))
    if element is None:
        element = OxmlElement(tag)
        parent.append(element)
    return element


def _set_border(element, edge: str, value: str, size: int = 8) -> None:
    element.set(qn("w:val"), value)
    if value == "nil":
        for attribute in ("sz", "space", "color"):
            element.attrib.pop(qn(f"w:{attribute}"), None)
        return
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:space"), "0")
    element.set(qn("w:color"), "000000")


def _apply_three_line_table(table) -> None:
    """Apply the three-line table convention used by 修改版15."""
    tbl_pr = table._tbl.tblPr

    tbl_width = _get_or_add(tbl_pr, "w:tblW")
    tbl_width.set(qn("w:w"), "0")
    tbl_width.set(qn("w:type"), "auto")
    alignment = _get_or_add(tbl_pr, "w:jc")
    alignment.set(qn("w:val"), "center")

    borders = _get_or_add(tbl_pr, "w:tblBorders")
    for edge in ("top", "bottom"):
        border = _get_or_add(borders, f"w:{edge}")
        _set_border(border, edge, "single", size=12)
    for edge in ("left", "right", "insideH", "insideV"):
        border = _get_or_add(borders, f"w:{edge}")
        _set_border(border, edge, "nil")

    tbl_look = _get_or_add(tbl_pr, "w:tblLook")
    for attribute, value in (
        ("val", "04A0"),
        ("firstRow", "1"),
        ("lastRow", "0"),
        ("firstColumn", "1"),
        ("lastColumn", "0"),
        ("noHBand", "0"),
        ("noVBand", "1"),
    ):
        tbl_look.set(qn(f"w:{attribute}"), value)

    last_row_index = len(table.rows) - 1
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            cell_borders = _get_or_add(tc_pr, "w:tcBorders")
            top_border = _get_or_add(cell_borders, "w:top")
            _set_border(top_border, "top", "single" if row_index == 0 else "nil", size=12)
            bottom_value = (
                "single"
                if row_index == 0 or row_index == last_row_index
                else "nil"
            )
            bottom_size = 8 if row_index == 0 else 12
            bottom_border = _get_or_add(cell_borders, "w:bottom")
            _set_border(bottom_border, "bottom", bottom_value, size=bottom_size)
            for edge in ("left", "right"):
                border = _get_or_add(cell_borders, f"w:{edge}")
                _set_border(border, edge, "nil")


def _normalize_colons(text: str) -> str:
    text = text.replace("关键词：", "关键词 ")
    text = text.replace("注：", "注")
    text = text.replace("doi: ", "doi ")
    text = text.replace("doi:", "doi ")
    return text.replace("：", "，").replace(":", ",")


def _normalize_document_text(doc) -> None:
    for paragraph in doc.paragraphs:
        normalized = _normalize_colons(paragraph.text)
        if normalized != paragraph.text:
            _set_paragraph_text(paragraph, normalized)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                normalized = _normalize_colons(cell.text)
                if normalized != cell.text:
                    _set_cell_text(cell, normalized)


def _remove_row(table, index: int) -> None:
    row = table.rows[index]
    table._tbl.remove(row._tr)


def _set_table(table, headers: list[str], rows: list[list[str]], bold_last: bool = False) -> None:
    expected_rows = len(rows) + 1
    while len(table.rows) > expected_rows:
        _remove_row(table, len(table.rows) - 1)
    while len(table.rows) < expected_rows:
        table.add_row()
    if len(table.columns) != len(headers):
        raise ValueError(f"模板表格列数不匹配: got={len(table.columns)}, expected={len(headers)}")
    for row, values in zip(table.rows, [headers, *rows]):
        if len(values) != len(table.columns):
            raise ValueError("表格行列数不匹配")
        for cell, value in zip(row.cells, values):
            text = _format_result_stat(str(value)).replace(" ± ", "±")
            if not text.strip() or text == "--":
                raise ValueError("表格存在空白或未填充的实验结果")
            _set_cell_text(cell, text)
    _apply_three_line_table(table)
    if bold_last:
        for cell in table.rows[-1].cells:
            _bold_table_cell(cell)


def _set_table_column_widths(table, widths: list[float]) -> None:
    """Keep dense metric tables readable after replacing the template rows."""
    if len(widths) != len(table.columns):
        raise ValueError("表格列宽数量不匹配")
    tbl_pr = table._tbl.tblPr
    layout = _get_or_add(tbl_pr, "w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    grid_columns = table._tbl.tblGrid.gridCol_lst
    for grid_column, width in zip(grid_columns, widths):
        grid_column.set(qn("w:w"), str(round(width * 1440)))
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_width = _get_or_add(tc_pr, "w:tcW")
            tc_width.set(qn("w:w"), str(round(width * 1440)))
            tc_width.set(qn("w:type"), "dxa")


def _parse_markdown_table(lines: list[str], heading_prefix: str) -> list[dict[str, str]]:
    """Read one pipe-delimited Markdown table without changing its values."""
    heading_index = next(
        (index for index, line in enumerate(lines) if line.strip().startswith(heading_prefix)),
        None,
    )
    if heading_index is None:
        raise ValueError(f"最新结果文件缺少 {heading_prefix}")

    table_lines = []
    for line in lines[heading_index + 1 :]:
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if "|" not in stripped:
            if table_lines:
                break
            continue
        table_lines.append(stripped)

    if len(table_lines) < 3:
        raise ValueError(f"最新结果文件中的 {heading_prefix} 表格不完整")

    def split_row(line: str) -> list[str]:
        content = line.strip().strip("|")
        return [re.sub(r"^\*+|\*+$", "", item.strip()) for item in content.split("|")]

    headers = split_row(table_lines[0])
    rows = []
    for line in table_lines[2:]:
        values = split_row(line)
        if len(values) != len(headers):
            raise ValueError(f"最新结果文件中的 {heading_prefix} 行列数不一致")
        rows.append(dict(zip(headers, values)))
    return rows


def _load_latest_metrics(path: Path) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    """Load the user-designated Markdown result snapshot as the result authority."""
    lines = path.read_text(encoding="utf-8").splitlines()
    known_rows = _parse_markdown_table(lines, "## Table 1.")
    open_rows = _parse_markdown_table(lines, "## Table 2.")
    unknown_rows = _parse_markdown_table(lines, "## Table 3.")

    metrics = {"known": {"tls60": {}, "quic60": {}}, "open": {"tls60": {}, "quic60": {}}, "unknown": {"tls60": {}, "quic60": {}}}
    for row in known_rows:
        model = row["Model"]
        metrics["known"]["tls60"][model] = {
            "accuracy": row["TLS Accuracy (%)"],
            "macro_f1": row["TLS Macro-F1 (%)"],
        }
        metrics["known"]["quic60"][model] = {
            "accuracy": row["QUIC Accuracy (%)"],
            "macro_f1": row["QUIC Macro-F1 (%)"],
        }

    for row in open_rows:
        model = row["Model"]
        metrics["open"]["tls60"][model] = {
            "accuracy": row["TLS Open-Set Accuracy (%)"],
            "macro_f1": row["TLS Open-Set Macro-F1 (%)"],
        }
        metrics["open"]["quic60"][model] = {
            "accuracy": row["QUIC Open-Set Accuracy (%)"],
            "macro_f1": row["QUIC Open-Set Macro-F1 (%)"],
        }

    for row in unknown_rows:
        model = row["Model"]
        dataset = "tls60" if row["Dataset"] == "TLS60" else "quic60" if row["Dataset"] == "QUIC60" else None
        if dataset is None:
            raise ValueError(f"未知结果表中出现未识别的数据集 {row['Dataset']}")
        metrics["unknown"][dataset][model] = {
            "precision": row["Unknown Precision (%)"],
            "tpr": row["TPR / Unknown Recall (%)"],
            "f1": row["Unknown F1 (%)"],
            "fpr": row["FPR (%)"],
            "auroc": row["AUROC (%)"],
            "aupr": row["AUPR (%)"],
        }

    expected_models = set(MODEL_ORDER)
    for section in ("known", "open", "unknown"):
        for dataset in ("tls60", "quic60"):
            if set(metrics[section][dataset]) != expected_models:
                raise ValueError(f"最新结果文件的 {section}/{dataset} 模型集合不完整")
    return metrics


def _latest_value(metrics: dict, section: str, dataset: str, model: str, metric: str) -> str:
    return metrics[section][dataset][model][metric]


def _latest_mean(value: str) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if match is None:
        raise ValueError(f"无法读取最新结果数值 {value}")
    return float(match.group(0))


def _latest_mean_decimal(value: str) -> Decimal:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if match is None:
        raise ValueError(f"无法读取最新结果数值 {value}")
    return Decimal(match.group(0))


def _format_point_gain(value: str, baseline: str) -> str:
    return _format_two_decimals(_latest_mean_decimal(value) - _latest_mean_decimal(baseline))


def _latest_best_baseline(metrics: dict, section: str, dataset: str, metric: str) -> tuple[str, str]:
    candidates = [
        (model, _latest_value(metrics, section, dataset, model, metric))
        for model in MODEL_ORDER[:-1]
    ]
    return max(candidates, key=lambda item: _latest_mean(item[1]))


def _insert_paragraph_after(paragraph, text: str, style=None):
    new_element = OxmlElement("w:p")
    paragraph._p.addnext(new_element)
    new_paragraph = Paragraph(new_element, paragraph._parent)
    if style is not None:
        new_paragraph.style = style
    _set_paragraph_text(new_paragraph, text)
    return new_paragraph


def _insert_table_after(paragraph, headers: list[str], rows: list[list[str]], bold_last: bool = False):
    table = paragraph._parent.add_table(rows=1, cols=len(headers), width=Inches(6.5))
    _set_table(table, headers, rows, bold_last=bold_last)
    paragraph._p.addnext(table._tbl)
    return table


def _insert_paragraph_after_table(table, text: str, style=None):
    new_element = OxmlElement("w:p")
    table._tbl.addnext(new_element)
    new_paragraph = Paragraph(new_element, table._parent)
    if style is not None:
        new_paragraph.style = style
    _set_paragraph_text(new_paragraph, text)
    return new_paragraph


def _bold_table_cell(cell) -> None:
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True


def _set_page_break_before(paragraph) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    page_break = _get_or_add(paragraph_properties, "w:pageBreakBefore")
    page_break.set(qn("w:val"), "1")


def _parse_dataset(exp_name: str) -> str:
    match = re.search(r"_(tls60|quic60)_seed\d+$", exp_name)
    if not match:
        raise ValueError(f"无法解析数据集: {exp_name}")
    return DATASET_MAP[match.group(1)]


def _load_results(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["dataset"] = frame["exp_name"].map(_parse_dataset)
    frame["model_name"] = frame["model"].astype(str).str.lower().map(MODEL_MAP)
    if frame["model_name"].isna().any():
        raise ValueError("结果中有未映射的模型")
    if len(frame) != 36 or frame["exp_name"].nunique() != 36:
        raise ValueError("论文重构要求 all_results.csv 含 36 条唯一正式运行")
    for model in MODEL_ORDER:
        for dataset in DATASET_MAP.values():
            subset = frame[(frame["model_name"] == model) & (frame["dataset"] == dataset)]
            if len(subset) != 3 or subset["seed"].nunique() != 3:
                raise ValueError(f"缺少 {model}/{dataset} 的三个正式 seed")
    return frame


def _load_source_groups(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"model", "dataset", "seed", "source_group", "view", "unknown_f1"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"来源分层快照缺少字段: {sorted(missing)}")
    frame["dataset"] = frame["dataset"].astype(str).str.replace("-S", "", regex=False)
    return frame


def _citation_numbers(group: str) -> list[int]:
    numbers = []
    for part in re.split(r"[,，]", group):
        part = part.strip()
        range_match = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if range_match:
            start, end = map(int, range_match.groups())
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(part))
    return numbers


def _renumber_references(doc) -> None:
    paragraphs = doc.paragraphs
    heading_index = next(
        (index for index, paragraph in enumerate(paragraphs) if paragraph.text.strip() == "参考文献"),
        None,
    )
    if heading_index is None:
        raise ValueError("稿件中找不到参考文献标题")

    entries = {}
    for paragraph in paragraphs[heading_index + 1 :]:
        match = re.match(r"^\[(\d+)\]\s*(.*)$", paragraph.text.strip())
        if match:
            entries[int(match.group(1))] = (paragraph, match.group(2))
    if not entries:
        raise ValueError("参考文献列表为空")

    first_appearance = []
    for paragraph in paragraphs[:heading_index]:
        for match in CITATION_PATTERN.finditer(paragraph.text):
            for number in _citation_numbers(match.group(1)):
                if number not in first_appearance:
                    first_appearance.append(number)

    missing = set(first_appearance) - set(entries)
    if missing:
        raise ValueError(f"正文引用缺少对应文献条目: {sorted(missing)}")
    renumber = {old: new for new, old in enumerate(first_appearance, start=1)}

    def replace_citation(match) -> str:
        numbers = _citation_numbers(match.group(1))
        return "[" + ",".join(str(renumber[number]) for number in numbers) + "]"

    for paragraph in paragraphs[:heading_index]:
        for run in paragraph.runs:
            updated_text = CITATION_PATTERN.sub(replace_citation, run.text)
            if updated_text != run.text:
                run.text = updated_text

    heading = paragraphs[heading_index]
    anchor = heading._p
    for old_number, (paragraph, body) in entries.items():
        if old_number not in renumber:
            paragraph._p.getparent().remove(paragraph._p)
    for old_number in first_appearance:
        paragraph, body = entries[old_number]
        if old_number == 29:
            body = (
                'J. Luxemburk, K. Hynek, T. Čejka, A. Lukačovič, and P. Šiška, '
                '"CESNET-QUIC22, A large one-month QUIC network traffic dataset from backbone lines," '
                "Data in Brief, vol. 46, Art. no. 108888, 2023, doi 10.1016/j.dib.2023.108888."
            )
        if "Fine-grained TLS services classification with reject option" in body:
            body = (
                'J. Luxemburk and T. Čejka, "Fine-grained TLS services classification with reject option," '
                "Computer Networks, vol. 220, Art. no. 109467, 2023, doi 10.1016/j.comnet.2022.109467."
            )
        if "NetMamba+" in body:
            body = (
                'T. Wang et al., "NetMamba+, A framework of pre-trained models for efficient and '
                'accurate network traffic classification," arXiv preprint, no. 2601.21792, 2026.'
            )
        _set_paragraph_text(paragraph, f"[{renumber[old_number]}] {body}")
        anchor.addnext(paragraph._p)
        anchor = paragraph._p


def _normalize_dataset_names(doc) -> None:
    replacements = {
        "CESNET-TLS22-S": "CESNET-TLS22",
        "CESNET-QUIC22-S": "CESNET-QUIC22",
    }
    for paragraph in doc.paragraphs:
        text = paragraph.text
        for old, new in replacements.items():
            text = text.replace(old, new)
        if text != paragraph.text:
            _set_paragraph_text(paragraph, text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text
                for old, new in replacements.items():
                    text = text.replace(old, new)
                if text != cell.text:
                    _set_cell_text(cell, text)


def _stats(frame: pd.DataFrame, dataset: str, model: str, column: str) -> tuple[float, float]:
    values = frame[(frame["dataset"] == dataset) & (frame["model_name"] == model)][column].astype(float)
    if len(values) != 3:
        raise ValueError(f"{dataset}/{model}/{column} 不是三个 seed")
    return float(values.mean()), float(values.std(ddof=1))


def _fmt_percent(mean: float, std: float | None = None) -> str:
    if std is None:
        return f"{mean * 100:.2f}"
    return f"{mean * 100:.2f}±{std * 100:.2f}"


def _fmt_params(frame: pd.DataFrame, model: str) -> str:
    values = frame.loc[frame["model_name"] == model, "trainable_params"].astype(float)
    unique = values.unique()
    if len(unique) != 1:
        raise ValueError(f"{model} 参数量在正式结果中不一致")
    return f"{_format_two_decimals(Decimal(str(unique[0])) / Decimal(1_000_000))} M"


def _source_stats(
    source: pd.DataFrame,
    dataset: str,
    source_group: str,
    column: str,
) -> tuple[float, float]:
    values = source[
        (source["model"] == "MVIF-Net")
        & (source["dataset"] == dataset)
        & (source["source_group"] == source_group)
        & (source["view"] == "threshold")
    ][column].astype(float)
    if len(values) != 3:
        raise ValueError(f"来源分层 {dataset}/{source_group}/{column} 不是三个 seed")
    return float(values.mean()), float(values.std(ddof=1))


def _best_baseline(frame: pd.DataFrame, dataset: str, column: str) -> tuple[str, float, float]:
    candidates = []
    for model in MODEL_ORDER[1:]:
        mean, std = _stats(frame, dataset, model, column)
        candidates.append((model, mean, std))
    return max(candidates, key=lambda item: item[1])


def _replace_media(docx_path: Path, media_name: str, replacement: Path) -> None:
    docx_path = docx_path.resolve()
    with tempfile.NamedTemporaryFile(
        prefix="mvif_docx_",
        suffix=".docx",
        dir=docx_path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
    try:
        with zipfile.ZipFile(docx_path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
            replacement_bytes = replacement.read_bytes()
            for item in source.infolist():
                payload = replacement_bytes if item.filename == media_name else source.read(item.filename)
                target.writestr(item, payload)
        os.replace(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _clean_architecture_figure(template: Path, output_dir: Path) -> Path:
    """Update the architecture figure while preserving its supplied layout."""
    with zipfile.ZipFile(template, "r") as archive:
        payload = archive.read("word/media/image1.png")

    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
    if image.size != (3942, 1848):
        raise ValueError(f"模板架构图尺寸发生变化: {image.size}")

    # The supplied template still contains the archived Closed-60 output.
    # Mask only that inactive branch and restore the pooling-box border.
    draw = ImageDraw.Draw(image)
    white = (255, 255, 255)
    green_border = (77, 126, 66)
    green_fill = (231, 240, 226)
    draw.rectangle((3545, 980, 3590, 1190), fill=white)
    draw.rectangle((3564, 1070, 3866, 1336), fill=white)
    draw.rectangle((3545, 980, 3579, 1107), fill=green_fill)
    draw.rounded_rectangle((3176, 682, 3586, 1112), radius=18, outline=green_border, width=9)

    # Replace the three long Chinese branch descriptions with concise English
    # labels that identify the evidence represented by each view.
    branch_specs = [
        ((610, 235, 1292, 607), (226, 238, 248), (52, 111, 166), "Temporal\nSequence"),
        ((610, 748, 1292, 1118), (225, 240, 222), (77, 126, 66), "Packet\nRelations"),
        ((610, 1260, 1292, 1625), (251, 225, 211), (190, 92, 44), "DFT Spectral\nConv"),
    ]
    font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
    if not font_path.exists():
        font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"缺少架构图字体: {font_path}")
    branch_font = ImageFont.truetype(str(font_path), 56)
    for box, fill, outline, label in branch_specs:
        draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=9)
        left, top, right, bottom = box
        draw.multiline_text(
            ((left + right) // 2, (top + bottom) // 2),
            label,
            fill=(30, 38, 50),
            font=branch_font,
            anchor="mm",
            align="center",
            spacing=8,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="mvif_architecture_",
        suffix=".png",
        dir=output_dir,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()
    image.save(temp_path, format="PNG")
    return temp_path


def _clean_dataset_figure(template: Path, output_dir: Path) -> Path:
    """Update dataset labels in the workflow figure without changing its layout."""
    with zipfile.ZipFile(template, "r") as archive:
        payload = archive.read("word/media/image2.png")

    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
    if image.size != (3978, 1788):
        raise ValueError(f"模板数据集流程图尺寸发生变化: {image.size}")

    font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simhei.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"缺少流程图字体: {font_path}")

    draw = ImageDraw.Draw(image)
    draw.rectangle((132, 820, 536, 985), fill=(255, 244, 214))
    draw.multiline_text(
        (334, 902),
        "CESNET-TLS22\nCESNET-QUIC22\n原始H5 + 服务映射",
        fill=(23, 32, 42),
        font=ImageFont.truetype(str(font_path), 31),
        anchor="mm",
        align="center",
        spacing=5,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="mvif_dataset_flow_",
        suffix=".png",
        dir=output_dir,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()
    image.save(temp_path, format="PNG")
    return temp_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rebuild(
    template: Path,
    output: Path,
    results_path: Path,
    source_path: Path,
    latest_metrics_path: Path,
    figure_path: Path,
) -> None:
    original_hash = _sha256(template)
    frame = _load_results(results_path)
    source = _load_source_groups(source_path)
    latest = _load_latest_metrics(latest_metrics_path)
    doc = Document(template)
    paragraphs = doc.paragraphs
    tables = doc.tables

    tls = DATASET_MAP["tls60"]
    quic = DATASET_MAP["quic60"]
    tls_known_mean, tls_known_std = _stats(frame, tls, "MVIF-Net", "test_threshold_known_macro_f1")
    quic_known_mean, quic_known_std = _stats(frame, quic, "MVIF-Net", "test_threshold_known_macro_f1")
    tls_unknown_mean, tls_unknown_std = _stats(frame, tls, "MVIF-Net", "test_threshold_unknown_f1")
    quic_unknown_mean, quic_unknown_std = _stats(frame, quic, "MVIF-Net", "test_threshold_unknown_f1")
    tls_auroc_mean, tls_auroc_std = _stats(frame, tls, "MVIF-Net", "test_threshold_unknown_auroc")
    quic_auroc_mean, quic_auroc_std = _stats(frame, quic, "MVIF-Net", "test_threshold_unknown_auroc")
    tls_aupr_mean, tls_aupr_std = _stats(frame, tls, "MVIF-Net", "test_threshold_unknown_aupr")
    quic_aupr_mean, quic_aupr_std = _stats(frame, quic, "MVIF-Net", "test_threshold_unknown_aupr")
    tls_false_unknown = _stats(frame, tls, "MVIF-Net", "test_threshold_known_false_unknown_rate")
    quic_false_unknown = _stats(frame, quic, "MVIF-Net", "test_threshold_known_false_unknown_rate")
    tls_false_known = _stats(frame, tls, "MVIF-Net", "test_threshold_unknown_false_known_rate")
    quic_false_known = _stats(frame, quic, "MVIF-Net", "test_threshold_unknown_false_known_rate")
    tls_best = _best_baseline(frame, tls, "test_threshold_known_macro_f1")
    quic_best = _best_baseline(frame, quic, "test_threshold_known_macro_f1")
    tls_best_unknown = _best_baseline(frame, tls, "test_threshold_unknown_f1")
    quic_best_unknown = _best_baseline(frame, quic, "test_threshold_unknown_f1")

    # The user-designated Markdown snapshot is authoritative for comparative metrics.
    tls_known = _latest_value(latest, "known", "tls60", "MVIF-Net", "macro_f1")
    quic_known = _latest_value(latest, "known", "quic60", "MVIF-Net", "macro_f1")
    tls_open = _latest_value(latest, "open", "tls60", "MVIF-Net", "macro_f1")
    quic_open = _latest_value(latest, "open", "quic60", "MVIF-Net", "macro_f1")
    tls_unknown = _latest_value(latest, "unknown", "tls60", "MVIF-Net", "f1")
    quic_unknown = _latest_value(latest, "unknown", "quic60", "MVIF-Net", "f1")
    tls_auroc = _latest_value(latest, "unknown", "tls60", "MVIF-Net", "auroc")
    quic_auroc = _latest_value(latest, "unknown", "quic60", "MVIF-Net", "auroc")
    tls_aupr = _latest_value(latest, "unknown", "tls60", "MVIF-Net", "aupr")
    quic_aupr = _latest_value(latest, "unknown", "quic60", "MVIF-Net", "aupr")
    tls_tpr = _latest_value(latest, "unknown", "tls60", "MVIF-Net", "tpr")
    quic_tpr = _latest_value(latest, "unknown", "quic60", "MVIF-Net", "tpr")
    tls_fpr = _latest_value(latest, "unknown", "tls60", "MVIF-Net", "fpr")
    quic_fpr = _latest_value(latest, "unknown", "quic60", "MVIF-Net", "fpr")
    tls_best = _latest_best_baseline(latest, "known", "tls60", "macro_f1")
    quic_best = _latest_best_baseline(latest, "known", "quic60", "macro_f1")
    tls_best_unknown = _latest_best_baseline(latest, "unknown", "tls60", "f1")
    quic_best_unknown = _latest_best_baseline(latest, "unknown", "quic60", "f1")

    # Abstract, introduction, and contribution list.
    _set_paragraph_text(
        paragraphs[3],
        "加密流量识别需要在不读取载荷的条件下应对应用开放和流量分布随时间变化的现实情况。本文提出 MVIF-Net，从包大小、方向和包间到达间隔构建时序、包关系与频域三视图，并借助样本级门控、有界可学习残差和分支类型标签完成跨视图交互。基于 CESNET-TLS22 与 CESNET-QUIC22 的时间前向开放集实验显示，MVIF-Net 在已知类别和整体开放集识别上均取得最佳结果。TLS 与 QUIC 的已知类别 Macro-F1 分别为 %s 和 %s，整体开放集 Macro-F1 分别为 %s 和 %s；未知流量 F1 分别达到 %s 和 %s。真实未知应用按身份隔离，测试窗口位于训练窗口之后，结果体现了模型在开放应用环境与时间分布变化下的识别优势。"
        % tuple(_format_result_stat(value) for value in (tls_known, quic_known, tls_open, quic_open, tls_unknown, quic_unknown)),
    )
    _set_paragraph_text(
        paragraphs[8],
        "本文提出 MVIF-Net，通过时序、包关系和频域视图的互补建模形成统一的加密流量表示，并在 token 空间内完成跨视图信息交互。样本级门控动态调节不同视图的贡献，有界可学习残差控制图更新与频域局部更新的幅度，分支类型标签为异构 token 提供明确的来源语义。模型以包级侧信道为输入，并在开放集和时间前向评测中同时考察已知应用识别与未知流量拒识。",
    )
    _set_paragraph_text(
        paragraphs[9],
        "部署环境中的应用集合持续扩展，协议行为也会随时间改变，因此分类器需要在维持已知应用识别的同时识别训练阶段未覆盖的流量。拒识选项为未知服务提供独立决策路径[6]，网络应用与流量分布的演进进一步凸显开放集评价的必要性[7]。本文按应用身份隔离真实未知流量，以独立噪声生成族构造补充测试来源，并使用已知验证流量校准拒识阈值。TLS 与 QUIC 均采用历史窗口训练、后续窗口测试，系统评价模型面对开放类别和时间漂移时的泛化表现。",
    )
    _set_paragraph_text(paragraphs[10], "本文的主要贡献包括")
    _set_paragraph_text(
        paragraphs[11],
        "（1）提出面向加密流量的多视图交互融合方法。该方法联合刻画包序列演化、包间关系与频域变化，并在统一表示空间中建立跨视图交互，使互补侧信道能够共同服务于流量判别。",
    )
    _set_paragraph_text(
        paragraphs[12],
        "（2）设计样本级门控和有界可学习残差机制。门控依据流量内容自适应分配多视图权重，可学习残差尺度调节结构关系传播与频域局部更新，共同增强跨协议建模的稳定性，并为适应时间分布变化提供稳健的特征更新路径。",
    )
    _set_paragraph_text(
        paragraphs[13],
        "（3）引入额外的分支类型标签以标识视图来源。该标签与位置编码共同保留时序、结构和频域 token 的来源语义，为融合过程提供清晰的异构信息组织方式，并支持模型在开放集流量与时间漂移场景中整合多源判别线索。",
    )

    # Problem definition and architecture.
    _set_paragraph_text(
        paragraphs[29],
        "设一条双向流按到达顺序排列，其前 T 个数据包构成输入序列。第 t 个包的观测特征由包级侧信道组成，得到输入矩阵 X。长度不足 T 的流在尾部补零，超过 T 的流截断至前 T 个包。模型输入不包含明文载荷、域名、应用名称和审计元数据，特征在输入模型前使用训练集统计量标准化。将一条流表示为按到达顺序排列的包级观测矩阵，可写为",
    )
    _set_paragraph_text(
        paragraphs[30],
        "X=[x₁,x₂,…,xₜ]ᵀ∈Rᵀˣᵈ，   xₜ∈Rᵈ    （1）",
    )
    _set_paragraph_text(
        paragraphs[31],
        "其中，xₜ表示第 t 个包的标准化侧信道向量，d 表示输入特征维度，X 为一条流的输入矩阵，T 为保留的最大包数。具体特征组成在模型结构部分说明。",
    )
    _set_paragraph_text(
        paragraphs[32],
        "已知类别集合记为 K，训练阶段未覆盖的应用和噪声流量汇总为 unknown 类 U。MVIF-Net 的输出空间为 K∪{U}，训练时的 unknown 支持流量和训练噪声参与 unknown 监督，已知验证流量只用于校准拒识阈值。类别数量和时间划分在实验设计中说明。",
    )
    _set_paragraph_text(
        paragraphs[34],
        "开放集测试集合同时包含已知类别流量、训练阶段没有出现的真实应用流量以及训练阶段没有使用的噪声生成族。未知应用在合并为 U 之前按照应用身份划分训练支持集、验证留出集和测试留出集，保证同一未知应用不会跨集合出现。标准化参数只由训练期数据估计。为区分已知类别判定和未知流量拒识，定义未知分数",
    )
    _set_paragraph_text(
        paragraphs[35],
        "r(X)=pθ(U|X)    （2）",
    )
    _set_paragraph_text(
        paragraphs[36],
        "其中，pθ(·|X) 是参数为 θ 的分类器输出概率，K 是已知类别集合，U 表示 unknown 类。模型直接使用 unknown 概率作为未知分数，并在验证集校准的阈值规则下决定是否拒识。",
    )
    _set_paragraph_text(
        paragraphs[37],
        "阈值 τ 仅使用已知验证流量进行校准。当 r(X)>τ 时，将样本判定为 unknown，否则保留分类器的已知类别输出。训练目标采用包含已知类别和 unknown 类的多类交叉熵。正式报告同时保留 raw argmax 和 threshold rejection 两种输出，以区分分类器自身的 unknown 概率与验证集工作点下的拒识行为。",
    )
    _set_paragraph_text(
        paragraphs[39],
        "其中，N 是一个训练批次中的样本数，Xi 和 yi 分别是第 i 个输入及其标签，θ 表示模型全部可训练参数。标签 yi 可以取已知类别之一或 unknown，训练目标与开放集输出空间保持一致。",
    )
    _set_paragraph_text(
        paragraphs[22],
        "MVIF-Net 的图分支在单条流内部构造包关系，并与时间表示及频域表示并行产生 token，随后在统一的注意力空间中交互。该做法把流内局部关系和特征相似关系作为序列信息的补充，同时避免依赖跨流连接或类别标签生成邻接关系。",
    )
    _set_paragraph_text(
        paragraphs[42],
        "MVIF-Net 对同一条流建立三种互补表示。Mamba 时间视图输出 30 个包级 token，包级结构图视图输出 30 个图消息传递 token，DFT 频域视图输出 16 个频率 token，三路表示均投影到 256 维。图分支和 DFT-CNN 分支各在前两层之间加入一条有界可学习残差；Mamba 的两个块直接堆叠。每条分支独立归一化后，由分支 gate 根据三个分支的掩码平均摘要产生样本级 Softmax 权重，并按 3g_b 对该分支 token 重加权，最后拼接为 76 个 token。包级 token 加入包位置编码，频率 token 加入频率位置编码，三路 token 均加入对应的可学习分支类型编码。带 key-padding mask 的四头 SDPA Transformer 融合块完成跨视图交互，之后对全部有效 token 做一次全局掩码均值池化，再送入单一线性分类头。",
    )
    related_work = paragraphs[17].text.replace(
        "。这些研究为序列分支提供了基础",
        "。NetMamba+进一步将预训练模型用于网络流量分类[32]。MPAF 从多阶段属性指纹建模流量特征[36]，RBLJAN 联合字节与标签信息进行鲁棒建模[37]，FS-Net 以流序列网络开展加密流量分类[38]。这些研究为序列分支提供了基础",
    )
    if related_work == paragraphs[17].text:
        raise ValueError("未找到相关工作段落的插入位置")
    _set_paragraph_text(paragraphs[17], related_work)
    _set_paragraph_text(
        paragraphs[44],
        "图 1  MVIF-Net 整体结构。输入流的前 30 个包及 3 个可观测特征分别经 Mamba 时序编码、相邻与特征相似双关系包图消息传递和联合实虚部的 DFT 卷积编码，形成 30、30、16 个 token；图与 DFT-CNN 分支在层间使用有界可学习残差，Mamba 两块直接堆叠。分支归一化和 Softmax gate 进行样本级重加权，加入包位置、频率位置与分支类型编码后，经带 padding mask 的 4 头 SDPA Transformer 和全局有效 token 掩码均值池化，接入 61 类 open-set 分类头。",
    )
    _set_paragraph_text(
        paragraphs[46],
        "输入首先经线性层由三维特征投影到 256 维，随后通过两个官方 Mamba Block[17]。NetMamba 的网络流量实验表明，选择性状态空间模型能够在较低开销下保留长程序列信息[15]；S4 从结构化状态空间角度解释了状态递推的高效实现[16]，Mamba 则利用输入相关的选择性更新增强了对不同位置内容的适应性[17]。每个 Block 包含 LayerNorm、选择性状态空间混合器、dropout 和残差连接，并沿包序列保留 30 个时间步。分支末端使用 LayerNorm，并加入共享包位置编码和时间分支类型编码。Mamba 选择性块在正式配置中以 FP32 计算，以避免 CUDA 自动混合精度下的数值不稳定。",
    )
    _set_paragraph_text(
        paragraphs[47],
        "4.3 包级结构图分支",
    )
    _set_paragraph_text(
        paragraphs[48],
        "每条流的 30 个包作为图节点。序列上相邻的包以及自身形成局部关系；对于非相邻包，根据标准化后的三维包特征距离选取 4 个近邻，构成非局部特征相似关系，并将非局部边对称化。两类邻接矩阵分别进行对称度归一化，两个图消息传递块独立聚合两类邻居信息，经线性变换、GELU 和 dropout 后以有界残差形式更新节点表示。设第 l 层节点表示为 Hˡ，双关系消息传递的残差更新可写为：",
    )
    _set_paragraph_text(
        paragraphs[49],
        "Hˡ⁺¹=Hˡ+αˡ Dropout(GELU(WₐAₐLN(Hˡ)+WₛAₛLN(Hˡ)))，  αˡ=0.5σ(βˡ)∈(0,0.5)  （4）",
    )
    _set_paragraph_text(
        paragraphs[50],
        "其中，Hˡ 是第 l 层的节点表示，Aₐ 和 Aₛ 分别是相邻包关系矩阵与特征相似关系矩阵，Wₐ 和 Wₛ 是对应的线性变换，LN、GELU 和 Dropout 分别表示层归一化、激活函数和随机失活。αˡ 是由可学习参数 βˡ 经 sigmoid 映射得到的有界残差尺度，限制每一层图更新的扰动幅度。上述图构造只在单条流内部完成，不使用跨流信息和类别标签生成邻接关系。",
    )
    _set_paragraph_text(
        paragraphs[53],
        "30 点 DFT 分支沿长度为 30 的包序列轴执行正交归一化的实值快速傅里叶变换（rFFT）。实部和虚部在通道方向拼接，每个频率位置包含六维特征，共保留 16 个单边频率 token。随后使用 LayerNorm 和 1×1 卷积投影到 256 维，再通过两个带有有界可学习残差尺度的 Conv1d 模块进行局部变换，卷积核依次为 1 和 3。沿包序列轴进行离散傅里叶变换，其第 k 个频率系数为：",
    )
    _set_paragraph_text(
        paragraphs[55],
        "其中，Zₖ 是第 k 个频率位置的复数系数，j 为虚数单位，k 为频率索引，t 为包序列索引。模型将 Zₖ 的实部和虚部在通道维拼接，并保留单边 rFFT 的 16 个频率 token，再通过 1×1 和 3×1 Conv1d 模块进行变换。每个 DFT 残差块的更新幅度由 γˡ=0.5σ(ηˡ) 约束在 (0,0.5) 内。保留实部和虚部使频域表示同时携带幅度和相位相关信息；频点只表示包序列轴上的频域变化，不直接等同于物理时间周期。",
    )
    _set_paragraph_text(
        paragraphs[58],
        "三路 token 经过各自的 LayerNorm 后先分别做掩码平均，三个分支摘要拼接后输入一个小型 MLP，并通过 Softmax 得到样本级分支权重 g。每路 token 按 3g_b 缩放后再按 Mamba、包级结构图和 DFT 顺序拼接，经过线性层和 GELU 进行维度整合，并输入单个 SDPA Transformer 融合块。该块采用四个头，单头维度为 64；模块包含 QKV 投影、带 key-padding mask 的缩放点积注意力、输出投影、LayerNorm，以及注意力和前馈子层各自的残差连接。跨视图交互后，对全部有效 token 做一次全局掩码均值池化，得到流级表示 h。三路 token 的编码、交互和分类过程概括为：",
    )
    _set_paragraph_text(
        paragraphs[59],
        "T′=Concat(3gᴹTᴹ, 3gᴳTᴳ, 3gᶠTᶠ)，H=FA(T′+E)，h=(hᴹ+hᴳ+hᶠ)/3，ŷ=softmax(Wh+b)",
    )
    _set_paragraph_text(
        paragraphs[60],
        "其中，Tᴹ、Tᴳ 和 Tᶠ 分别表示 Mamba、包级结构图和 DFT 卷积分支的 token，gᴹ、gᴳ 和 gᶠ 是 Softmax gate 权重，T′ 表示按 3g_b 重加权后拼接的 76 个 token。E 表示与 T′ 逐位置对应的编码张量：Mamba 与图分支使用包位置编码，DFT 分支使用频率位置编码，三类 token 均加入各自的分支类型编码。分支类型编码用于区分 token 的来源语义，不是额外的类别标签。A 表示带 key-padding mask 的 SDPA Transformer；其输出对全部有效 token 做一次全局掩码均值，得到 h，W 和 b 是唯一线性分类头参数。代码中保留 auxiliary heads 仅为已完成 checkpoint 的 state-dict 兼容；正式前向不计算辅助 logits，训练损失也不包含辅助项。",
    )
    _set_paragraph_text(
        paragraphs[61],
        "当前正式实现由上述三路主干、分支归一化与 gate、一个带 key-padding mask 的 SDPA Transformer 融合块、全局 masked mean 读出和一个线性分类头组成。辅助头仅用于已完成 checkpoint 的 state-dict 兼容，正式前向和训练损失均采用主分类路径。",
    )

    # Experimental setup.
    _set_paragraph_text(
        paragraphs[64],
        "实验以上游公开的 CESNET-TLS22 和 CESNET-QUIC22 数据集为来源，分别依据细粒度 TLS 服务分类数据集论文[6]和 CESNET-QUIC22 数据集论文[29]。数据读取与任务封装遵循 DataZoo 的流量分类实验流程[31]。本文在两个数据集上重新构造统一的流级开放集任务，不沿用源论文的原始类别划分。已知类别根据训练窗口内的应用流量频数选取，每个数据集取前 60 个应用；每类流量在训练、验证和测试集的目标上限分别为 10,000、2,000 和 2,000 条。TLS 使用 2021-10-04 至 2021-10-10 训练、2021-10-11 验证和 2021-10-12 至 2021-10-17 测试；QUIC 使用 2022-10-31 至 2022-11-13 训练、2022-11-14 至 2022-11-15 验证和 2022-11-16 至 2022-11-27 测试。",
    )
    _set_paragraph_text(
        paragraphs[65],
        "已知类别之外的可识别应用构成 unknown 候选池，候选应用先按身份分为训练支持、验证留出和测试留出，再折叠为 U。训练、验证和测试分别使用 gaussian_iid_v1、shuffle_spike_v2 和 mixture_burst_v3 三种互不复用的噪声生成族。日期、流 ID、原始应用身份、来源组和噪声族只用于审计，不作为模型输入；输入始终是每条流前 30 个包的标准化包大小、方向和包间到达间隔。",
    )
    _set_paragraph_text(paragraphs[66], "表 1  CESNET-TLS22 数据划分与流量规模")
    _set_paragraph_text(paragraphs[69], "表 2  CESNET-QUIC22 数据划分与流量规模")
    _set_paragraph_text(
        paragraphs[73],
        "图 2  CESNET-TLS22 与 CESNET-QUIC22 的开放集数据构建流程。流记录按 flow ID 重建并按日期划分，在训练窗口统计前 60 个已知类别；其余可识别应用按身份分到 unknown 支持集和留出集，训练、验证、测试使用互不复用的噪声生成族，标准化参数仅由训练期数据估计。",
    )
    _set_paragraph_text(
        paragraphs[75],
        "对比方法包括 30pktTCNET、NetMamba[15]、SRViT[33]、TrafficAudio[34] 和 BPF-GNN[35]。各模型均采用统一的每流前 30 个数据包和三维侧信道输入协议，并保留各自的核心网络路径。TrafficAudio 保留其 BiGRU 路径，各模型按照相近的容量范围配置宽度和深度，从而在同一数据协议下比较已知类别识别和开放集拒识能力。",
    )
    _set_paragraph_text(paragraphs[76], "表 3  MVIF-Net 与适配基线的实际规模设置")
    _set_paragraph_text(
        paragraphs[78],
        "训练最多 100 轮，依据已知验证流量 Macro-F1 调整学习率并执行早停。有效训练批次设置为 4,096，评估批次为 512；固定使用种子 599、5009 和 813。MVIF-Net 的 Mamba 选择性块使用 FP32 计算，其他兼容算子在硬件条件允许时使用自动混合精度；SDPA 由 PyTorch 自动选择兼容的注意力后端。正式结果包含五个对比模型在 TLS/QUIC 上的 30 次运行，以及 MVIF-Net 在 TLS/QUIC 开放集和闭集条件下的 12 次运行，共 42 次运行。",
    )
    _set_paragraph_text(
        paragraphs[80],
        "已知类别评价包括 Accuracy 和 Macro-F1。开放集评价包括 Unknown Precision、Recall、F1、AUROC、AUPR、已知流量误拒率、未知流量误判为已知的比例，以及混合测试集 Accuracy 和 Macro-F1。正式对比表统一采用已知验证流量校准的拒识阈值，五种适配基线以 1−maxₖ p(k|X) 构造未知分数后使用同样的阈值规则。来源分层结果分别统计真实未知应用、合成噪声及其与已知测试流量混合后的指标。",
    )

    # Results text and captions.
    _set_paragraph_text(paragraphs[83], "本节先比较已知类别识别能力，再评估整体开放集识别、未知来源分层和阈值拒识工作点。所有指标均按三个随机种子的均值与样本标准差报告。表 4 和表 5 分别汇总 CESNET-TLS22 与 CESNET-QUIC22 上的已知类别 Accuracy 和 Macro-F1。")
    _set_paragraph_text(paragraphs[84], "表 4  CESNET-TLS22 已知类别测试结果（百分比，均值±样本标准差）")
    _set_paragraph_text(paragraphs[86], "表 5  CESNET-QUIC22 已知类别测试结果（百分比，均值±样本标准差）")
    _set_paragraph_text(
        paragraphs[88],
        "MVIF-Net 在 CESNET-TLS22 上取得 %s 的 Accuracy 和 %s 的 Macro-F1，在 CESNET-QUIC22 上取得 %s 的 Accuracy 和 %s 的 Macro-F1。两个数据集的 Macro-F1 均高于五种对比模型中的最佳结果，分别领先 %s 和 %s 个百分点，表明多视图表征在不同协议和后续时间窗口中均能保持有竞争力的已知类别判别能力。"
        % (
            _format_result_stat(_latest_value(latest, "known", "tls60", "MVIF-Net", "accuracy")),
            _format_result_stat(tls_known),
            _format_result_stat(_latest_value(latest, "known", "quic60", "MVIF-Net", "accuracy")),
            _format_result_stat(quic_known),
            _format_point_gain(tls_known, tls_best[1]),
            _format_point_gain(quic_known, quic_best[1]),
        ),
    )
    _set_paragraph_text(paragraphs[89], "6.2 整体开放集识别")
    _set_paragraph_text(paragraphs[90], "表 6 和表 7 对比各模型在含已知类别与未知流量的测试集上的整体表现，报告开放集 Accuracy、Macro-F1、Unknown F1 和 AUROC。未知分数阈值由已知验证流量校准，测试集保持时间前向并包含按身份留出的真实未知应用及独立噪声来源。")
    _set_paragraph_text(paragraphs[91], "表 6  CESNET-TLS22 开放集总体结果（百分比，均值±样本标准差）")
    _set_paragraph_text(paragraphs[93], "表 7  CESNET-QUIC22 开放集总体结果（百分比，均值±样本标准差）")
    _set_paragraph_text(
        paragraphs[95],
        "MVIF-Net 在整体开放集测试中，TLS 的 Accuracy 和 Macro-F1 分别达到 %s 和 %s，QUIC 分别达到 %s 和 %s，均为对应数据集的最佳结果。未知流量检测方面，TLS 的 Unknown F1、AUROC 和 AUPR 分别为 %s、%s 和 %s；QUIC 分别为 %s、%s 和 %s。整体结果表明，多视图交互为已知类别保持与未知流量检测提供了互补判别信息，在两个真实加密协议数据集的时间前向测试中均形成较强的开放集识别能力。"
        % (
            _format_result_stat(_latest_value(latest, "open", "tls60", "MVIF-Net", "accuracy")), _format_result_stat(tls_open),
            _format_result_stat(_latest_value(latest, "open", "quic60", "MVIF-Net", "accuracy")), _format_result_stat(quic_open),
            *(_format_result_stat(value) for value in (tls_unknown, tls_auroc, tls_aupr, quic_unknown, quic_auroc, quic_aupr)),
        ),
    )
    _set_paragraph_text(paragraphs[96], "图 3 汇总最新正式结果中的已知类别 Macro-F1 和整体开放集 Macro-F1。点表示三个随机种子的均值，误差线表示样本标准差。")
    _set_paragraph_text(paragraphs[99], "图 3  CESNET-TLS22 与 CESNET-QUIC22 上的分类性能。左图比较已知类别 Macro-F1，右图比较整体开放集 Macro-F1；点表示三个随机种子的均值，误差线表示样本标准差。")
    _set_paragraph_text(
        paragraphs[100],
        "在未知流量检测方面，TLS 最佳对比模型 %s 的 Unknown F1 为 %s，MVIF-Net 达到 %s；QUIC 最佳对比模型 %s 为 %s，MVIF-Net 达到 %s。MVIF-Net 在两个数据集上的 Unknown F1 分别提升 %s 和 %s 个百分点，同时保持领先的整体开放集 Macro-F1。多视图交互、样本级门控和有界残差共同支持模型从差异化协议流量中提取稳定的未知判别线索。"
        % (
            tls_best_unknown[0],
            _format_result_stat(tls_best_unknown[1]),
            _format_result_stat(tls_unknown),
            quic_best_unknown[0],
            _format_result_stat(quic_best_unknown[1]),
            _format_result_stat(quic_unknown),
            _format_point_gain(tls_unknown, tls_best_unknown[1]),
            _format_point_gain(quic_unknown, quic_best_unknown[1]),
        ),
    )
    tls_real = _source_stats(source, tls, "unknown_test_heldout", "unknown_f1")
    tls_noise = _source_stats(source, tls, "noise_test", "unknown_f1")
    quic_real = _source_stats(source, quic, "unknown_test_heldout", "unknown_f1")
    quic_noise = _source_stats(source, quic, "noise_test", "unknown_f1")
    _set_paragraph_text(
        paragraphs[101],
        "来源分层结果显示，TLS 真实未知应用和合成噪声的 Unknown F1 分别为 %s 和 %s，QUIC 分别为 %s 和 %s。真实未知应用测试检验类别开放条件下的识别能力，独立噪声族补充评估对分布扰动的响应。结合已知流量混合结果，两种来源共同呈现未知覆盖与整体分类保持情况。由于测试时段位于训练时段之后，这些结果也反映了模型应对协议流量变化和时间漂移的能力。"
        % (
            _fmt_percent(*tls_real),
            _fmt_percent(*tls_noise),
            _fmt_percent(*quic_real),
            _fmt_percent(*quic_noise),
        ),
    )
    _set_paragraph_text(paragraphs[102], "6.3 未知来源分层与时间前向泛化")
    _set_paragraph_text(
        paragraphs[103],
        "表 8 和表 9 分别报告真实未知应用、合成噪声及其与已知测试流量混合后的分类结果。该分层呈现不同未知来源下的拒识覆盖及整体 Macro-F1，并与训练期至测试期的时间前向划分结合，刻画模型在应用开放和分布演化条件下的泛化表现。",
    )
    _set_paragraph_text(paragraphs[104], "表 8  CESNET-TLS22 未知来源分层结果（百分比，均值±样本标准差）")
    _set_paragraph_text(paragraphs[105], "注 纯未知来源行仅含未知流量，因此 Mixed Macro-F1 记为 N/A。混合行统计该来源与已知测试流量合并后的结果。拒识阈值由已知验证流量校准。")
    _set_paragraph_text(paragraphs[106], "表 9  CESNET-QUIC22 未知来源分层结果（百分比，均值±样本标准差）")
    _set_paragraph_text(paragraphs[107], "注 所有数值均来自三个正式随机种子的最终来源分层结果。表内 N/A 项表示该评估对象不包含已知流量混合样本。")

    tls_real_mix = _source_stats(source, tls, "unknown_test_heldout+known", "open_set_macro_f1")
    tls_noise_mix = _source_stats(source, tls, "noise_test+known", "open_set_macro_f1")
    quic_real_mix = _source_stats(source, quic, "unknown_test_heldout+known", "open_set_macro_f1")
    quic_noise_mix = _source_stats(source, quic, "noise_test+known", "open_set_macro_f1")
    _set_paragraph_text(
        paragraphs[108],
        "在来源与已知流量混合的测试集上，TLS 的真实未知组和合成噪声组 Macro-F1 分别为 %s 和 %s，QUIC 分别为 %s 和 %s。纯未知组召回率反映未知流量覆盖，混合 Macro-F1 则反映已知类别保持与未知拒识的综合效果。两个数据集上的时间前向结果共同显示，MVIF-Net 能够在应用集合扩展和时间分布变化下维持稳定的开放集识别表现。"
        % (
            _fmt_percent(*tls_real_mix),
            _fmt_percent(*tls_noise_mix),
            _fmt_percent(*quic_real_mix),
            _fmt_percent(*quic_noise_mix),
        ),
    )
    _set_paragraph_text(paragraphs[109], "6.4 未知流量拒识与已知流量误拒分析")
    _set_page_break_before(paragraphs[109])
    reject_models = ["30pktTCNET", "NetMamba", "SRViT", "TrafficAudio", "BPF-GNN", "MVIF-Net"]
    reject_rows = []
    for model in reject_models:
        reject_rows.append(
            [
                model,
                _latest_value(latest, "unknown", "tls60", model, "tpr"),
                _latest_value(latest, "unknown", "tls60", model, "fpr"),
                _latest_value(latest, "unknown", "quic60", model, "tpr"),
                _latest_value(latest, "unknown", "quic60", model, "fpr"),
            ]
        )
    _set_paragraph_text(
        paragraphs[110],
        "本文在验证集校准阈值下统计未知流量拒识工作点。TPR 定义为被正确判为 unknown 的未知流量数占未知流量总数的比例，对应 threshold_unknown_recall。FPR 定义为被错误拒绝为 unknown 的已知流量数占已知流量总数的比例，对应 threshold_known_false_unknown_rate。拒识阈值仅由已知验证流量校准，测试集标签不参与阈值选择。"
    )
    reject_caption = _insert_paragraph_after(
        paragraphs[110],
        "表 10  正式结果中的未知流量拒识 TPR 与已知流量误拒 FPR（百分比，均值±样本标准差）",
        style=paragraphs[91].style,
    )
    reject_table = _insert_table_after(
        reject_caption,
        ["Model", "TLS TPR", "TLS FPR", "QUIC TPR", "QUIC FPR"],
        reject_rows,
        bold_last=True,
    )
    _set_table_column_widths(reject_table, [1.30, 1.30, 1.30, 1.30, 1.30])
    _insert_paragraph_after_table(
        reject_table,
        "表 10 显示，MVIF-Net 在 TLS 和 QUIC 上的 TPR 分别为 %s 和 %s，较高的未知覆盖能力与 %s 和 %s 的 FPR 工作点相结合，形成了稳定的开放集拒识配置。该结果说明在相同的验证集阈值校准规则下，模型能够提高未知流量识别率并保持已知流量误拒水平可控，为时间前向开放网络中的部署提供了直接的工作点证据。"
        % tuple(_format_result_stat(value) for value in (reject_rows[-1][1], reject_rows[-1][3], reject_rows[-1][2], reject_rows[-1][4])),
        style=paragraphs[108].style,
    )
    _set_paragraph_text(
        paragraphs[112],
        "本文提出 MVIF-Net，一种基于多视图交互融合的加密流量分类模型。模型以每条流前 30 个包的标准化包大小、方向和包间到达间隔为输入，通过 Temporal Sequence、Packet Relations 和 DFT Spectral Conv 三个分支分别组织序列状态、包间关系和频域变化；图与 DFT-CNN 分支使用层间有界可学习残差，Mamba 两块直接堆叠。模型再使用分支归一化、Softmax gate、包位置编码、频率位置编码和分支类型编码完成统一 token 融合，并以带 padding mask 的 SDPA Transformer 建立跨视图交互，最后对有效 token 做全局掩码均值读出。",
    )
    _set_paragraph_text(
        paragraphs[113],
        "本文还基于 CESNET-TLS22 和 CESNET-QUIC22 构建了 60 类开放集时间前向评测协议，将真实未知应用身份隔离、噪声生成族隔离和验证集阈值校准纳入同一评价流程。36 次正式运行显示，MVIF-Net 在两个协议的后续测试窗口中同时保持领先的已知类别识别、整体开放集识别和未知流量拒识能力。实验结果从整体性能和未知来源分层两个层面体现了多视图交互、门控与有界残差、分支类型标签的组合价值。",
    )
    _set_paragraph_text(
        paragraphs[119],
        "本文使用 CESNET-TLS22 和 CESNET-QUIC22 作为上游公开数据来源，数据集说明见对应论文[6,29]，数据读取和任务封装流程参见 DataZoo 工作[31]。本文构建的 60 类开放集 CSV、审计报告、实验配置和轻量结果快照随代码仓库提供，原始 H5、checkpoint、日志和预测文件不随本文重新分发。",
    )

    # Tables 1-9. Existing widths and positions are preserved.
    _set_table(
        tables[0],
        ["Split", "Date Range", "Known Traffic", "Real Unknown", "Synthetic Noise", "Total Traffic"],
        [
            ["Train", "2021-10-04 to 10-10", "600,000", "180,000", "60,000", "840,000"],
            ["Validation", "2021-10-11", "120,000", "36,000", "12,000", "168,000"],
            ["Test", "2021-10-12 to 10-17", "120,000", "36,000", "12,000", "168,000"],
        ],
    )
    _set_table(
        tables[1],
        ["Split", "Date Range", "Known Traffic", "Real Unknown", "Synthetic Noise", "Total Traffic"],
        [
            ["Train", "2022-10-31 to 11-13", "600,000", "109,333", "60,000", "769,333"],
            ["Validation", "2022-11-14 to 11-15", "119,888", "10,189", "11,989", "142,066"],
            ["Test", "2022-11-16 to 11-27", "120,000", "36,000", "12,000", "168,000"],
        ],
    )
    param_rows = [
        ["30pktTCNET", "Residual temporal convolution", "300 channels; 4 blocks", _fmt_params(frame, "30pktTCNET")],
        ["NetMamba", "Selective state-space backbone", "292 dimensions; 4 blocks", _fmt_params(frame, "NetMamba")],
        ["SRViT", "Multi-scale front end and attention backbone", "192 dimensions; 4 blocks", _fmt_params(frame, "SRViT")],
        ["TrafficAudio", "Parallel convolution and BiGRU paths", "416 dimensions; CNN/BiGRU", _fmt_params(frame, "TrafficAudio")],
        ["BPF-GNN", "Feature-, packet-, and flow-level graph paths", "664 dimensions; depths 1, 2, 1", _fmt_params(frame, "BPF-GNN")],
        ["MVIF-Net", "Temporal Sequence; Packet Relations; DFT Spectral Conv", "256 dimensions; 4 heads; 76 tokens", _fmt_params(frame, "MVIF-Net")],
    ]
    _set_table(tables[2], ["Model", "Core Architecture", "Width and Depth", "Trainable Parameters"], param_rows, bold_last=True)

    for table_index, dataset in ((3, tls), (4, quic)):
        rows = []
        dataset_key = "tls60" if dataset == tls else "quic60"
        for model in MODEL_ORDER:
            accuracy = _latest_value(latest, "known", dataset_key, model, "accuracy")
            macro_f1 = _latest_value(latest, "known", dataset_key, model, "macro_f1")
            rows.append([model, accuracy, macro_f1])
        _set_table(tables[table_index], ["Model", "Accuracy (%)", "Macro-F1 (%)"], rows, bold_last=True)

    for table_index, dataset in ((5, "tls60"), (6, "quic60")):
        rows = []
        for model in MODEL_ORDER:
            rows.append([
                model,
                _latest_value(latest, "open", dataset, model, "accuracy"),
                _latest_value(latest, "open", dataset, model, "macro_f1"),
                _latest_value(latest, "unknown", dataset, model, "f1"),
                _latest_value(latest, "unknown", dataset, model, "auroc"),
            ])
        _set_table(
            tables[table_index],
            ["Model", "Open Acc. (%)", "Open Macro-F1 (%)", "Unknown F1 (%)", "AUROC (%)"],
            rows,
            bold_last=True,
        )
        _set_table_column_widths(tables[table_index], [1.20, 1.35, 1.45, 1.30, 1.20])

    for table_index, dataset in ((7, tls), (8, quic)):
        rows = []
        for label, group, mixed in (
            ("Real Unknown", "unknown_test_heldout", False),
            ("Synthetic Noise", "noise_test", False),
            ("Real Unknown + Known", "unknown_test_heldout+known", True),
            ("Synthetic Noise + Known", "noise_test+known", True),
        ):
            recall = _fmt_percent(*_source_stats(source, dataset, group, "unknown_recall"))
            f1 = _fmt_percent(*_source_stats(source, dataset, group, "unknown_f1"))
            mixed_f1 = _fmt_percent(*_source_stats(source, dataset, group, "open_set_macro_f1")) if mixed else "N/A"
            rows.append([label, recall, f1, mixed_f1])
        _set_table(tables[table_index], ["Unknown Source", "Unknown Recall (%)", "Unknown F1 (%)", "Mixed Macro-F1 (%)"], rows)

    for table in tables:
        _apply_three_line_table(table)
    _normalize_document_text(doc)
    _normalize_dataset_names(doc)
    _renumber_references(doc)

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    if figure_path.exists():
        architecture_path = _clean_architecture_figure(template, output.parent)
        dataset_path = _clean_dataset_figure(template, output.parent)
        try:
            _replace_media(output, "word/media/image1.png", architecture_path)
            _replace_media(output, "word/media/image2.png", dataset_path)
            _replace_media(output, "word/media/image3.png", figure_path)
        finally:
            architecture_path.unlink(missing_ok=True)
            dataset_path.unlink(missing_ok=True)
    else:
        raise FileNotFoundError(f"缺少正式结果图: {figure_path}")
    if _sha256(template) != original_hash:
        raise RuntimeError("模板文件在重构过程中发生变化")
    print(f"已写入 {output}")
    print(f"模板 SHA-256: {original_hash}")
    print(f"输出 SHA-256: {_sha256(output)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path("../paper/源稿归档/重制版3.docx"))
    parser.add_argument("--output", type=Path, default=Path("../paper/源稿归档/重制版3_MVIF-Net_重构版.docx"))
    parser.add_argument("--results", type=Path, default=Path("results/formal60/all_results.csv"))
    parser.add_argument("--source-groups", type=Path, default=Path("results/formal60/formal60_source_groups.csv"))
    parser.add_argument("--latest-metrics", type=Path, required=True)
    parser.add_argument("--figure", type=Path, default=Path("../paper/源稿归档/figure3_formal60.png"))
    args = parser.parse_args()
    rebuild(args.template, args.output, args.results, args.source_groups, args.latest_metrics, args.figure)


if __name__ == "__main__":
    main()
