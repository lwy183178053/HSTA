# HSTA Paper Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one editable seven-page draw.io source and seven high-resolution English PNG figures for the HSTA JNCA manuscript without modifying any manuscript file.

**Architecture:** A focused Python generator will load and validate repository experiment data, build uncompressed native diagrams.net XML pages from reusable shape primitives, and write the multi-page `.drawio` file. A short PowerShell script will invoke the installed draw.io CLI for deterministic page-by-page PNG export. Unit tests will validate numeric mappings, page structure, required/forbidden labels, and output contracts.

**Tech Stack:** Python 3.13 standard library (`csv`, `json`, `statistics`, `xml.etree.ElementTree`), `unittest`, PowerShell, diagrams.net/draw.io desktop CLI.

---

## File Structure

- Create `scripts/generate_hsta_drawio_figures.py`: validated data loading, draw.io shape primitives, and seven page builders.
- Create `scripts/export_hsta_drawio_figures.ps1`: page-indexed CLI export to stable PNG names.
- Create `tests/test_generate_hsta_drawio_figures.py`: data, XML, terminology, and output-contract tests.
- Create `paper/figures_drawio/JNCA_HSTA_Figures.drawio`: generated seven-page editable source.
- Create `paper/figures_drawio/fig1_hsta_architecture.png` through `fig7_data_processing_pipeline.png`: exported formal assets.
- Modify `progress.md`: append implementation and verification evidence.

### Task 1: Lock Data Extraction and Paper-Facing Labels

**Files:**
- Create: `tests/test_generate_hsta_drawio_figures.py`
- Create: `scripts/generate_hsta_drawio_figures.py`

- [ ] **Step 1: Write tests for validated chart data**

Create tests that import `load_figure_data(PROJECT_ROOT)` and assert:

```python
def test_main_macro_f1_values(self):
    data = load_figure_data(PROJECT_ROOT)
    self.assertEqual(data.main["HSTA"]["QUIC-40"], (91.09, 0.20))
    self.assertEqual(data.main["HSTA"]["QUIC-60"], (90.28, 0.39))
    self.assertEqual(data.main["HSTA"]["TLS-40"], (96.78, 0.14))
    self.assertEqual(data.main["HSTA"]["TLS-60"], (96.29, 0.17))

def test_paper_labels_remove_adapted_suffix(self):
    data = load_figure_data(PROJECT_ROOT)
    self.assertIn("30pktTCNET", data.main)
    self.assertIn("NetMamba", data.main)
    self.assertNotIn("30pktTCNET-adapted", data.main)
    self.assertNotIn("NetMamba-adapted", data.main)

def test_confusion_dimensions(self):
    data = load_figure_data(PROJECT_ROOT)
    self.assertEqual(len(data.confusion["QUIC-40"].matrix), 40)
    self.assertEqual(len(data.confusion["QUIC-60"].matrix), 60)
```

- [ ] **Step 2: Run tests and verify the module is initially missing**

Run:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m unittest tests.test_generate_hsta_drawio_figures -v
```

Expected: failure because `scripts.generate_hsta_drawio_figures` does not yet exist.

- [ ] **Step 3: Implement minimal validated data loaders**

Implement dataclasses for mean/std series and confusion data, CSV readers for the main, adapted baseline, ablation, efficiency, and transfer results, and JSON readers for the two confusion matrices. Normalize display names only at the paper-facing boundary. Raise `ValueError` when required rows, dimensions, or key metrics are absent.

- [ ] **Step 4: Run data tests**

Run the same `unittest` command. Expected: all data-loading tests pass and the four HSTA values match the manuscript values exactly.

- [ ] **Step 5: Commit data loading**

```powershell
git add -- scripts/generate_hsta_drawio_figures.py tests/test_generate_hsta_drawio_figures.py
git commit -m "test: lock HSTA figure data mappings"
```

### Task 2: Build Native Draw.io Primitives and Document Contract

**Files:**
- Modify: `scripts/generate_hsta_drawio_figures.py`
- Modify: `tests/test_generate_hsta_drawio_figures.py`

- [ ] **Step 1: Add XML contract tests**

Add tests that generate to a temporary directory and assert seven named `<diagram>` pages, native `mxCell` vertices/edges, the expected PNG basename contract, and absence of embedded bitmap `data:image` content.

```python
def test_drawio_document_has_seven_native_pages(self):
    xml_text = build_drawio_document(load_figure_data(PROJECT_ROOT))
    root = ET.fromstring(xml_text)
    pages = root.findall("diagram")
    self.assertEqual([page.attrib["name"] for page in pages], PAGE_NAMES)
    self.assertGreater(len(root.findall(".//mxCell[@vertex='1']")), 100)
    self.assertNotIn("data:image", xml_text)
```

- [ ] **Step 2: Run the XML test and confirm failure**

Expected: failure because `build_drawio_document` and shape primitives are not implemented.

- [ ] **Step 3: Implement the uncompressed diagrams.net writer**

Add small primitives for rectangles, rounded zones, labels, arrows, lines, circles, bars, error bars, packet glyphs, matrices, and stacked sheets. Use stable cell IDs and a page-local drawing context. Write uncompressed `<mxfile><diagram><mxGraphModel>...` XML so all objects remain editable.

- [ ] **Step 4: Run XML contract tests**

Expected: seven empty-but-valid page shells and native cells pass the contract tests.

- [ ] **Step 5: Commit the document framework**

```powershell
git add -- scripts/generate_hsta_drawio_figures.py tests/test_generate_hsta_drawio_figures.py
git commit -m "feat: add native drawio figure framework"
```

### Task 3: Implement Figures 1 and 7

**Files:**
- Modify: `scripts/generate_hsta_drawio_figures.py`
- Modify: `tests/test_generate_hsta_drawio_figures.py`

- [ ] **Step 1: Add required-label and forbidden-label tests**

Assert Figure 1 contains `Learned positional embedding`, `LayerNorm`, and `Class logits`, Figure 7 contains the three features, `Truncate or zero-pad to 30 packets`, and `Train-only standardization`, and the complete XML contains no Chinese characters, `Figure`, `Fig.`, or `-adapted`.

- [ ] **Step 2: Run tests and confirm missing labels**

Expected: required-label assertions fail.

- [ ] **Step 3: Build the compact editorial architecture page**

Create the two-row HSTA path with three numbered technical zones, layered state sheets, a focused attention inset, tensor dimensions, and the exact code-level operation order. End at logits rather than Softmax.

- [ ] **Step 4: Build the detailed data-processing page**

Create the approved four-zone editorial pipeline plus preparation row: CESNET sources, flow grouping, packet glyphs, the `30 x 3` feature matrix, truncation/zero-padding, official temporal partitions, train-only scaling, privacy boundary, and stacked output tensor.

- [ ] **Step 5: Run terminology and structure tests**

Expected: all Figure 1/7 required labels pass and all forbidden-text scans return zero matches.

- [ ] **Step 6: Commit architecture and preprocessing pages**

```powershell
git add -- scripts/generate_hsta_drawio_figures.py tests/test_generate_hsta_drawio_figures.py
git commit -m "feat: add HSTA architecture and data pipeline figures"
```

### Task 4: Implement Result Figures 2 Through 5

**Files:**
- Modify: `scripts/generate_hsta_drawio_figures.py`
- Modify: `tests/test_generate_hsta_drawio_figures.py`

- [ ] **Step 1: Add chart-cell and value-label tests**

Assert expected series counts, task labels, error-bar cells, direct labels, parameter values, and transfer footnote text. Assert HSTA uses orange consistently and no other series uses the same fill.

- [ ] **Step 2: Run tests and confirm missing chart pages**

Expected: page-specific chart assertions fail.

- [ ] **Step 3: Build Figure 2 grouped bars**

Draw four task groups, five methods, mean/std error bars, compact values, and an editorial legend strip. Keep axes truthful and preserve visible differences without truncating the scale misleadingly.

- [ ] **Step 4: Build Figure 3 ablation bars and placement schematic**

Draw four task groups, four ablation variants, error bars, and a small five-stage attention-position schematic that uses the violet attention role and orange complete-HSTA role.

- [ ] **Step 5: Build Figure 4 parameter-performance scatter**

Plot all five models with direct labels using validated parameter counts and average 40-class Macro-F1. Resolve label collisions manually in page coordinates.

- [ ] **Step 6: Build Figure 5 transfer dot plot**

Draw four protocol-direction ribbons and aligned points for zero-shot, LoRA, full fine-tuning, and target scratch. Add the covered-class Macro-F1 footnote inside the plot margin.

- [ ] **Step 7: Run chart tests and commit**

Expected: chart structure, numeric labels, and semantic-color tests pass.

```powershell
git add -- scripts/generate_hsta_drawio_figures.py tests/test_generate_hsta_drawio_figures.py
git commit -m "feat: add HSTA result comparison figures"
```

### Task 5: Implement the Vector Confusion-Matrix Figure

**Files:**
- Modify: `scripts/generate_hsta_drawio_figures.py`
- Modify: `tests/test_generate_hsta_drawio_figures.py`

- [ ] **Step 1: Add matrix geometry and callout tests**

Assert 1,600 QUIC-40 matrix-cell shapes, 3,600 QUIC-60 matrix-cell shapes, one shared colorbar, indexed axes, and four highlighted confusion-pair callouts.

- [ ] **Step 2: Run tests and confirm matrix cells are absent**

Expected: confusion geometry assertions fail.

- [ ] **Step 3: Build Figure 6 from metrics JSON**

Normalize each confusion-matrix row to percentages, create every cell as a native vector rectangle, share a consistent sequential blue scale, and add concise orange side annotations for the strongest pairs. Do not print 40 or 60 long class names around the matrix.

- [ ] **Step 4: Run full unit tests and commit**

Expected: all data, XML, label, chart, and matrix tests pass.

```powershell
git add -- scripts/generate_hsta_drawio_figures.py tests/test_generate_hsta_drawio_figures.py
git commit -m "feat: add vector confusion matrix figure"
```

### Task 6: Generate, Export, and Visually Verify Formal Assets

**Files:**
- Create: `scripts/export_hsta_drawio_figures.ps1`
- Create: `paper/figures_drawio/JNCA_HSTA_Figures.drawio`
- Create: seven PNG files under `paper/figures_drawio/`
- Modify: `progress.md`

- [ ] **Step 1: Implement the deterministic export script**

The script must verify `C:\Program Files\draw.io\draw.io.exe`, map page indexes 0-6 to the seven stable PNG names, export each page at 2400-pixel width on white, and stop on a nonzero exit code or missing output.

- [ ] **Step 2: Generate the draw.io source**

Run:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_hsta_drawio_figures.py
```

Expected: `paper/figures_drawio/JNCA_HSTA_Figures.drawio` exists and reports seven pages.

- [ ] **Step 3: Export all pages**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_hsta_drawio_figures.ps1
```

Expected: seven nonzero PNG files, each approximately 2400 pixels wide.

- [ ] **Step 4: Run automated verification**

Run:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m unittest tests.test_generate_hsta_drawio_figures -v
git diff --name-only -- '*.docx' '*.tex'
```

Expected: all tests pass and the manuscript diff command prints no files changed by this task.

- [ ] **Step 5: Perform visual QA and iterate**

Inspect all seven full-resolution PNGs and a montage. Check for clipping, overlaps, blank exports, text below manuscript-scale readability, overlong Figure 1 width, inconsistent colors, incorrect chart labels, or decorative elements that do not encode meaning. Fix the generator and regenerate until all seven pass.

- [ ] **Step 6: Append the implementation record**

Append a `2026-07-12` entry to `progress.md` listing generated files, exact test commands, visual-QA outcome, and rollback by removing `paper/figures_drawio/` plus the new scripts/tests.

- [ ] **Step 7: Commit formal figure assets**

```powershell
git add -- scripts/generate_hsta_drawio_figures.py scripts/export_hsta_drawio_figures.ps1 tests/test_generate_hsta_drawio_figures.py paper/figures_drawio progress.md
git commit -m "feat: create JNCA HSTA paper figures"
```
