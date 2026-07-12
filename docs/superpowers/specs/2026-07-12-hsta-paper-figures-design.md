# HSTA Paper Figures Design Specification

## Objective

Create a coherent seven-figure set for the HSTA encrypted QUIC/TLS traffic-classification paper. The figures must be visually distinctive enough to communicate a strong publication standard while remaining accurate, editable, and legible in an Elsevier/JNCA manuscript.

This task produces figure assets only. It does not insert or replace images in any Word or LaTeX manuscript.

## Approved Direction

The approved direction is the **editorial hybrid** style selected by the user. It combines:

- SAT-Net-like numbered technical regions, clearly bounded modules, and explicit local detail;
- TrafficFormer-like layered packet objects, stacked tensors, repeated model layers, and narrative data flow;
- restrained journal typography, direct labels, and evidence-first charts.

The references provide visual-language inspiration only. Their layouts, logos, application icons, and figure-specific artwork must not be copied.

## Visual System

### Composition

- Use a white canvas with compact colored technical zones rather than one flat row of boxes.
- Use numbered regions only where they clarify a multi-stage process.
- Use packet strips, feature matrices, stacked sheets, timelines, and tensor layers as meaningful technical objects.
- Use solid fills, thin borders, dashed boundaries, and restrained shadows for depth. Do not use gradients, decorative blobs, or presentation-style backgrounds.
- Keep the revised model architecture compact, with a two-row HSTA path rather than the previous extra-wide single row.

### Color Roles

- Deep blue `#3F78A3`: packet/flow acquisition and primary comparison models.
- Soft blue `#DCEBF6`: input and state-space processing zones.
- Muted violet `#7C6A96` with `#F2EDF7`: feature encoding and attention-related content.
- Muted green `#6F9477` with `#E8F1EA`: data partitioning, normalization, and validated preparation steps.
- HSTA orange `#D87935` with `#FFF3E8`: focal HSTA modules, the proposed model, and selected results.
- Neutral charcoal `#35414A` and gray `#AEB6BD`: axes, baselines, boundaries, and context.

Orange remains the unique focal color for HSTA in result figures. Other accent colors communicate stages or distinct baselines and must not compete with HSTA.

### Typography and Labels

- Use Arial or Helvetica-compatible sans-serif text.
- All text inside figures must be English.
- Do not place `Figure`, `Fig.`, figure numbers, Chinese captions, or full figure titles inside exported images.
- Use concise labels such as `Packet size`, `Direction`, `Inter-arrival time`, `Train-only standardization`, and `Class logits`.
- Paper captions remain external to the image.
- Text must remain readable when a figure is placed at full two-column width. Avoid font sizes below the visual equivalent of 8 pt at final placement.

## Figure Set

### Figure 1: HSTA Model Architecture

- Use a compact two-row composition with three visual regions: input embedding, HSTA module, and classification head.
- Show input tensor `[B, 30, 3]`, linear projection `3 -> 128`, and learned positional embedding.
- Inside the HSTA boundary, show the actual sequence: Mamba block 1, Mamba block 2, Transition MLP, Attention, Refinement MLP, and LayerNorm.
- Use layered state sheets and a focused attention inset to add technical depth without changing the computational order.
- End with mean pooling, linear classifier, and class logits `[B, C]`. Do not show Softmax as a model layer.

### Figure 2: Main Macro-F1 Comparison

- Use grouped bars for QUIC-40, QUIC-60, TLS-40, and TLS-60.
- Include GRU, Transformer, 30pktTCNET, NetMamba, and HSTA.
- Show mean and standard-deviation error bars where multi-seed values are available.
- Use compact direct value labels. Use neutral, violet, blue, and orange method colors with HSTA as the only orange series.
- Source values from the four task result files and `results/sota_adapted/all_results.csv`; paper-facing labels must omit `-adapted`.

### Figure 3: Attention-Position Ablation

- Use grouped bars for No attention, Front attention, Middle attention, and HSTA across the four tasks.
- Use mean and standard-deviation error bars.
- Add a small schematic above or beside the legend showing the attention position in each five-stage sequence; this is explanatory, not decorative.
- Source values from `results/ablation_s/all_results.csv` and the main HSTA task results.

### Figure 4: Parameter-Performance Trade-off

- Use a scatter plot with parameters in millions on the x-axis and average Macro-F1 over QUIC-40 and TLS-40 on the y-axis.
- Include GRU, Transformer, 30pktTCNET, NetMamba, and HSTA.
- Use direct labels and small model-family glyphs made from simple geometric marks.
- Source parameter counts from `results/efficiency_benchmark/summary.csv` and performance values from the validated task result CSVs.

### Figure 5: Cross-Protocol Transfer

- Use a horizontal dot plot with four rows: QUIC to TLS-40, TLS to QUIC-40, QUIC to TLS-60, and TLS to QUIC-60.
- Compare zero-shot, LoRA, full fine-tuning, and target-from-scratch results.
- Include a compact source-to-target protocol ribbon at the left of each row.
- State inside the plot area that zero-shot values are covered-class Macro-F1, using a short footnote rather than a title.
- Source values from `results/transfer_s/all_results.csv` and the corresponding task result files.

### Figure 6: Class-Level Confusion Patterns

- Draw two aligned vector heatmaps for QUIC-40 and QUIC-60 with one shared colorbar.
- Build every matrix cell as an editable draw.io shape rather than embedding a raster heatmap.
- Use the validated confusion data in the experiment metrics JSON files.
- Use restrained orange callouts for the two strongest confusion pairs in each task, including AdAvoid to Gmail and Play.cz Radio to Overleaf Compile.
- Avoid unreadable full class names around all 40 or 60 cells. Use indexed axes and a concise side annotation for highlighted pairs.

### Figure 7: Data Processing and Input Construction

- Use four numbered editorial zones with a second preparation row:
  1. encrypted traffic acquisition from CESNET-TLS22 and CESNET-QUIC22;
  2. flow reconstruction and extraction of packet size, direction, and inter-arrival time;
  3. fixed-length construction by retaining the first 30 packets and zero-padding shorter flows;
  4. leakage-aware partitioning, train-only standardization, and model-ready tensor generation.
- Visualize packet direction and size as meaningful packet glyphs, the three features as a `30 x 3` matrix, and the output as stacked tensors `[B, 30, 3]`.
- Show the privacy boundary explicitly: no payload, DPI, domain, or application-layer metadata.
- Reflect actual behavior in `data/sampler.py` and `data/dataset.py`. Do not claim an explicit padding mask because the current model does not use one.

## Deliverables

Create a new directory without overwriting the current editable source:

- `paper/figures_drawio/JNCA_HSTA_Figures.drawio`: one editable page per figure, seven pages total.
- `paper/figures_drawio/fig1_hsta_architecture.png`
- `paper/figures_drawio/fig2_main_macro_f1.png`
- `paper/figures_drawio/fig3_attention_position_ablation.png`
- `paper/figures_drawio/fig4_parameter_performance.png`
- `paper/figures_drawio/fig5_cross_protocol_transfer.png`
- `paper/figures_drawio/fig6_confusion_patterns.png`
- `paper/figures_drawio/fig7_data_processing_pipeline.png`

Each PNG should be exported at approximately 2400 pixels wide on a white background. The editable draw.io file is the source of truth.

## Data Integrity

- Preserve published paper-facing values and labels; do not rerun experiments or invent missing results.
- Compare plotted data against the relevant CSV or metrics JSON before export.
- Keep internal experiment identifiers unchanged in the repository, but display `30pktTCNET` and `NetMamba` in figures.
- Use mean and standard deviation consistently and do not present a single-run value as a multi-seed mean.

## Verification

- Open and export all seven draw.io pages with `C:\Program Files\draw.io\draw.io.exe`.
- Confirm seven PNG files exist, are nonblank, and have the expected high-resolution dimensions.
- Inspect every PNG at full resolution and at manuscript-scale reduction for clipping, overlap, unreadable labels, or misleading visual emphasis.
- Scan draw.io XML for Chinese characters, `Figure`, `Fig.`, stale `-adapted` labels, and accidental internal titles.
- Programmatically compare every chart value with its source CSV or JSON.
- Confirm Figure 1 includes positional embedding and LayerNorm and ends at class logits.
- Confirm Figure 7 accurately reflects truncation/zero-padding and train-only standardization.
- Confirm no Word or LaTeX manuscript file changes during this task.

## Rollback Boundary

All formal outputs are isolated under `paper/figures_drawio/`. Rollback consists of removing that directory and reverting the associated `progress.md` entry. Existing manuscript files and `paper/论文全部图_精修可编辑.drawio` remain untouched.
