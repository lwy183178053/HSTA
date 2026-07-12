# HSTA Graphical Abstract Design

## Purpose

Create a standalone graphical abstract that summarizes the complete HSTA paper in one high-density, publication-ready visual. It complements the seven formal figures and does not replace or modify them.

## Visual Direction

- Use an original editorial-technical composition inspired by the supplied examples and common Elsevier graphical abstracts.
- Combine layered packet objects, numbered model stages, compact microcharts, full confusion patterns, protocol-transfer ribbons, and concise evidence callouts.
- Keep the hierarchy clear despite the high information density: input and privacy boundary, HSTA mechanism, then experimental evidence.
- Use the established blue, violet, green, orange, and neutral HSTA palette with orange reserved for the proposed method and strongest findings.
- Use English-only text and native draw.io shapes. Do not embed screenshots or raster charts inside the editable source.

## Composition

### Header

- Large `HSTA` identifier.
- Subtitle: `Hybrid state-space transition-attention modeling for encrypted QUIC/TLS traffic classification`.
- Compact badges for `30 packets`, `3 side-channel features`, and `No payload / DPI`.

### Upper Narrative

- Left input panel: CESNET-TLS22 and CESNET-QUIC22, bidirectional packet glyphs, first-30-packet window, and `[B, 30, 3]` tensor.
- Center model panel: projection and positional embedding, two Mamba blocks, Transition MLP, Attention, Refinement MLP, LayerNorm and mean pooling, and class logits.
- Mechanism ribbon: sequential dependency modeling, discriminative packet reweighting, and compact flow representation.

### Lower Evidence Panels

- `A Four-task performance`: mini grouped bars and the four HSTA Macro-F1 values.
- `B Attention placement`: four architecture strips and the complete-HSTA result.
- `C Efficiency and transfer`: parameter-performance scatter plus cross-protocol full-fine-tuning values.
- `D Error structure`: native QUIC-40 and QUIC-60 confusion matrices with the two dominant confusion pairs.

## Outputs

- `paper/figures_drawio/JNCA_HSTA_Graphical_Abstract.drawio`
- `paper/figures_drawio/graphical_abstract_hsta.png`

Export the PNG at 3000 pixels wide on white. Keep the existing seven-page `JNCA_HSTA_Figures.drawio` and seven PNGs unchanged.

## Verification

- Every plotted value comes from the existing validated `FigureData` object.
- The draw.io source contains one page, native vector objects, no Chinese text, no `-adapted` labels, and no embedded bitmap data.
- The PNG is nonblank, 3000 pixels wide, and visually legible at full resolution and reduced manuscript preview size.
