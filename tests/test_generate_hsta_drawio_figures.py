from __future__ import annotations

import os
import hashlib
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.generate_hsta_drawio_figures import (
    GRAPHICAL_ABSTRACT_FILENAME,
    OUTPUT_FILENAMES,
    PAGE_NAMES,
    build_drawio_document,
    build_graphical_abstract_document,
    load_figure_data,
    write_drawio,
    write_graphical_abstract,
)


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = WORKTREE_ROOT.parents[1]
PROJECT_ROOT = Path(os.environ.get("HSTA_PROJECT_ROOT", DEFAULT_DATA_ROOT)).resolve()
EXPORT_ROOT = Path(os.environ.get("HSTA_EXPORT_ROOT", PROJECT_ROOT / "paper" / "figures_drawio")).resolve()


class FigureDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_figure_data(PROJECT_ROOT)

    def test_main_macro_f1_values(self):
        self.assertEqual(self.data.main["HSTA"]["QUIC-40"], (91.09, 0.20))
        self.assertEqual(self.data.main["HSTA"]["QUIC-60"], (90.28, 0.39))
        self.assertEqual(self.data.main["HSTA"]["TLS-40"], (96.78, 0.14))
        self.assertEqual(self.data.main["HSTA"]["TLS-60"], (96.29, 0.17))

    def test_paper_labels_remove_adapted_suffix(self):
        self.assertIn("30pktTCNET", self.data.main)
        self.assertIn("NetMamba", self.data.main)
        self.assertNotIn("30pktTCNET-adapted", self.data.main)
        self.assertNotIn("NetMamba-adapted", self.data.main)

    def test_ablation_and_transfer_shapes(self):
        self.assertEqual(set(self.data.ablation), {"No attention", "Front attention", "Middle attention", "HSTA"})
        self.assertEqual(set(self.data.transfer), {"Zero-shot", "LoRA", "Full fine-tuning", "Target scratch"})
        self.assertEqual(len(self.data.transfer["Zero-shot"]), 4)

    def test_confusion_dimensions(self):
        self.assertEqual(len(self.data.confusion["QUIC-40"].matrix), 40)
        self.assertEqual(len(self.data.confusion["QUIC-40"].matrix[0]), 40)
        self.assertEqual(len(self.data.confusion["QUIC-60"].matrix), 60)
        self.assertEqual(len(self.data.confusion["QUIC-60"].matrix[0]), 60)


class DrawioDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_figure_data(PROJECT_ROOT)
        cls.xml_text = build_drawio_document(cls.data)
        cls.root = ET.fromstring(cls.xml_text)

    def test_drawio_document_has_seven_native_pages(self):
        pages = self.root.findall("diagram")
        self.assertEqual([page.attrib["name"] for page in pages], PAGE_NAMES)
        self.assertGreater(len(self.root.findall(".//mxCell[@vertex='1']")), 5_300)
        self.assertNotIn("data:image", self.xml_text)

    def test_output_contract(self):
        self.assertEqual(len(OUTPUT_FILENAMES), 7)
        self.assertEqual(OUTPUT_FILENAMES[0], "fig1_hsta_architecture.png")
        self.assertEqual(OUTPUT_FILENAMES[-1], "fig7_data_processing_pipeline.png")

    def test_required_labels(self):
        values = "\n".join(cell.attrib.get("value", "") for cell in self.root.findall(".//mxCell"))
        for label in (
            "Learned positional embedding",
            "LayerNorm",
            "Class logits",
            "Packet size",
            "Direction",
            "Inter-arrival time",
            "Truncate or zero-pad to 30 packets",
            "Train-only standardization",
        ):
            self.assertIn(label, values)

    def test_forbidden_visible_text(self):
        values = "\n".join(cell.attrib.get("value", "") for cell in self.root.findall(".//mxCell"))
        self.assertNotRegex(values, r"[\u4e00-\u9fff]")
        self.assertNotIn("-adapted", values)
        self.assertNotRegex(values, r"\bFigure\b|\bFig\.?")
        for internal_title in (
            "Four encrypted-traffic tasks",
            "Attention placement variants",
            "Efficiency-performance landscape",
            "Protocol transfer regimes",
            "Class-level error structure",
        ):
            self.assertNotIn(internal_title, values)

    def test_attention_schematics_match_experiment_layouts(self):
        values = [cell.attrib.get("value", "") for cell in self.root.findall(".//mxCell")]
        self.assertGreaterEqual(values.count("A"), 3)
        self.assertGreaterEqual(values.count("R"), 5)

    def test_confusion_cells_are_native_vectors(self):
        cells = self.root.findall(".//mxCell")
        quic40 = [cell for cell in cells if cell.attrib.get("id", "").startswith("p6-q40-cell-")]
        quic60 = [cell for cell in cells if cell.attrib.get("id", "").startswith("p6-q60-cell-")]
        self.assertEqual(len(quic40), 1_600)
        self.assertEqual(len(quic60), 3_600)

    def test_write_drawio(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "figures.drawio"
            write_drawio(self.data, output)
            self.assertTrue(output.exists())
            self.assertEqual(len(ET.parse(output).getroot().findall("diagram")), 7)


class GraphicalAbstractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_figure_data(PROJECT_ROOT)
        cls.xml_text = build_graphical_abstract_document(cls.data)
        cls.root = ET.fromstring(cls.xml_text)

    def test_graphical_abstract_is_one_native_page(self):
        pages = self.root.findall("diagram")
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].attrib["name"], "Graphical Abstract")
        self.assertGreater(len(self.root.findall(".//mxCell[@vertex='1']")), 5_300)
        self.assertNotIn("data:image", self.xml_text)

    def test_graphical_abstract_integrates_paper_story(self):
        values = "\n".join(cell.attrib.get("value", "") for cell in self.root.findall(".//mxCell"))
        for label in (
            "Privacy-preserving input",
            "HSTA representation and classification pipeline",
            "Four-task performance",
            "Attention placement",
            "Efficiency and transfer",
            "Class-level error structure",
            "flow_id",
            "ordered packets",
            "first 30",
            "train-only standardization",
            "No payload | No DPI | No domains",
            "91.09",
            "96.78",
            "0.602 M parameters",
        ):
            self.assertIn(label, values)
        self.assertNotRegex(values, r"[\u4e00-\u9fff]")
        self.assertNotIn("-adapted", values)

    def test_graphical_abstract_uses_three_full_width_bands(self):
        model = self.root.find(".//mxGraphModel")
        self.assertIsNotNone(model)
        self.assertEqual(model.attrib["pageWidth"], "2600")
        self.assertEqual(model.attrib["pageHeight"], "1700")

        for cell_id in ("ga-data-band", "ga-model-band", "ga-evidence-band"):
            cell = self.root.find(f".//mxCell[@id='{cell_id}']")
            self.assertIsNotNone(cell, cell_id)
            geometry = cell.find("mxGeometry")
            self.assertIsNotNone(geometry, cell_id)
            self.assertGreaterEqual(float(geometry.attrib["width"]), 2520)

    def test_write_graphical_abstract(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "graphical.drawio"
            write_graphical_abstract(self.data, output)
            self.assertTrue(output.exists())
            self.assertEqual(len(ET.parse(output).getroot().findall("diagram")), 1)


class ExportedPngTests(unittest.TestCase):
    def test_exported_png_contract(self):
        hashes = set()
        for filename in OUTPUT_FILENAMES:
            path = EXPORT_ROOT / filename
            self.assertTrue(path.exists(), filename)
            payload = path.read_bytes()
            self.assertGreater(len(payload), 100_000, filename)
            self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n", filename)
            width, height = struct.unpack(">II", payload[16:24])
            self.assertEqual(width, 2400, filename)
            self.assertGreater(height, 1000, filename)
            hashes.add(hashlib.sha256(payload).hexdigest())
        self.assertEqual(len(hashes), len(OUTPUT_FILENAMES))

    def test_graphical_abstract_png_contract(self):
        path = EXPORT_ROOT / GRAPHICAL_ABSTRACT_FILENAME
        self.assertTrue(path.exists(), path.name)
        payload = path.read_bytes()
        self.assertGreater(len(payload), 200_000)
        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        self.assertEqual(width, 3000)
        self.assertGreater(height, 1400)


if __name__ == "__main__":
    unittest.main()
