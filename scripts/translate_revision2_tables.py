from __future__ import annotations

import argparse
import os
import re
import tempfile
import zipfile
from pathlib import Path

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
CHINESE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")

TRANSLATIONS = {
    "任务": "Task",
    "协议": "Protocol",
    "类数": "Classes",
    "序列长": "Sequence length",
    "流数(k)": "Flows (k)",
    "划分(k)": "Split (k)",
    "包记录(M)": "Packet records (M)",
    "每类流(k)": "Flows per class (k)",
    "模型": "Model",
    "HSTA（本文）": "HSTA (Ours)",
    "40 类": "40 classes",
    "60 类": "60 classes",
    "变化（百分点）": "Change (percentage points)",
    "结构变体": "Architecture variant",
    "无注意力": "No attention",
    "前置注意力": "Front attention",
    "中置注意力": "Middle attention",
    "HSTA（完整结构）": "HSTA (full architecture)",
    "参数量(M)": "Parameters (M)",
    "GFLOPs/样本": "GFLOPs/sample",
    "延迟(ms)": "Latency (ms)",
    "吞吐(samples/s)": "Throughput (samples/s)",
    "峰值显存(MB)": "Peak GPU memory (MB)",
    "堆叠深度 N": "Stacking depth N",
    "结构说明": "Architecture",
    "1 个 HSTA 模块": "1 HSTA module",
    "主模型（1×HSTA）": "Main model (1x HSTA)",
    "2 个 HSTA 模块": "2 HSTA modules",
    "2×HSTA 模块": "2x HSTA modules",
    "4 个 HSTA 模块": "4 HSTA modules",
    "4×HSTA 模块": "4x HSTA modules",
    "迁移方向": "Transfer direction",
    "重叠类 F1": "Overlapping-class F1",
    "LoRA 参数%": "LoRA parameters (%)",
    "从头训练 F1": "Target-scratch F1",
    "FT-从头训练": "Full FT - target scratch",
    "真实类别（名称）": "True class (name)",
    "预测类别（名称）": "Predicted class (name)",
    "错误数量": "Error count",
    "占真实类别比例（%）": "Percentage of true class (%)",
    "DataZoo 标签": "DataZoo label",
    "是否属于40类": "Included in 40-class subset",
    "流量名称": "Traffic name",
    "服务类别": "Service category",
    "是": "Yes",
    "否": "No",
    "Split (k)": "Train/Val/Test (k)",
    "Batch": "Batch size",
    "HSTA (full architecture)": "HSTA (full model)",
    "Stacking depth N": "Stacking depth (N)",
    "Architecture": "Configuration",
    "Overlapping-class F1": "Shared-class F1",
    "Target-scratch F1": "Scratch F1",
    "Full FT - target scratch": "Full FT - Scratch",
    "Percentage of true class (%)": "Share of true class (%)",
    "Included in 40-class subset": "In 40-class subset",
}


def cell_text(cell: etree._Element) -> str:
    return "".join(node.text or "" for node in cell.xpath(".//w:t", namespaces=NS))


def translated_text(text: str) -> str:
    translated = TRANSLATIONS.get(text, text)
    return translated.replace("（", " (").replace("）", ")")


def table_cells(root: etree._Element) -> list[etree._Element]:
    return root.xpath(".//w:tbl//w:tc", namespaces=NS)


def replace_cell_text(cell: etree._Element, value: str) -> None:
    text_nodes = cell.xpath(".//w:t", namespaces=NS)
    if not text_nodes:
        raise ValueError("Cannot replace text in a table cell without w:t nodes")
    text_nodes[0].text = value
    for node in text_nodes[1:]:
        node.text = ""


def load_document_xml(path: Path) -> tuple[bytes, etree._Element]:
    with zipfile.ZipFile(path) as archive:
        payload = archive.read("word/document.xml")
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    return payload, etree.fromstring(payload, parser)


def untranslated_cells(root: etree._Element) -> list[str]:
    return sorted({cell_text(cell) for cell in table_cells(root) if CHINESE_RE.search(cell_text(cell))})


def rewrite_docx(path: Path, document_xml: bytes) -> None:
    handle, temp_name = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=".docx", dir=path.parent)
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
            for item in source.infolist():
                payload = document_xml if item.filename == "word/document.xml" else source.read(item.filename)
                target.writestr(item, payload)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def translate_tables(path: Path) -> tuple[int, int]:
    _, root = load_document_xml(path)
    tables = root.xpath(".//w:tbl", namespaces=NS)
    changed = 0
    for cell in table_cells(root):
        before = cell_text(cell)
        after = translated_text(before)
        if after != before:
            replace_cell_text(cell, after)
            changed += 1

    remaining = untranslated_cells(root)
    if remaining:
        raise ValueError("Untranslated table cells: " + " | ".join(remaining))

    if changed:
        document_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        rewrite_docx(path, document_xml)
    return len(tables), changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate all Revision 2 table-cell text to English.")
    parser.add_argument("docx", type=Path)
    parser.add_argument("--check", action="store_true", help="Fail if any Chinese remains in table cells.")
    args = parser.parse_args()
    path = args.docx.resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    _, root = load_document_xml(path)
    if args.check:
        remaining = untranslated_cells(root)
        print(f"tables={len(root.xpath('.//w:tbl', namespaces=NS))} untranslated_cells={len(remaining)}")
        for value in remaining:
            print(value)
        raise SystemExit(1 if remaining else 0)

    table_count, changed = translate_tables(path)
    print(f"Translated {changed} cells across {table_count} tables: {path}")


if __name__ == "__main__":
    main()
