# JNCA Submission Generation

This project generates the JNCA manuscript package from repository results and manuscript scripts.

## Entry Points

Use the project Anaconda interpreter:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py
```

The first command rebuilds the fallback Overleaf package and generated result figures. The second command rebuilds a standalone bilingual LaTeX package under `paper/jnca_bilingual_latex` and refreshes the recommended English and Chinese Overleaf zip packages.
The third command rebuilds the Chinese and English Word manuscripts, embeds the generated result figures, exports the English PDF through Microsoft Word COM, refreshes the submission checklist, and creates the recommended upload bundle using the latest English Overleaf zip.
The fourth command validates the generated submission package, including PDF header/EOF/page-object/content-stream/font-image-resource/raw-metadata-marker/timestamp checks, Word table/image counts, Word in-text citation markers, Highlights length, author statements, declaration of interest, upload manifest, format audit, LaTeX figure paths/citations, expanded BibTeX coverage, Overleaf import hygiene, upload-bundle contents, zip contents, and zip-entry hygiene.

## Generated Outputs

- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`
- `paper/submission_jnca/Highlights.docx`
- `paper/submission_jnca/Author_Statements.docx`
- `paper/submission_jnca/Declaration_of_Interest_Statement.docx`
- `paper/submission_jnca/Cover_Letter.docx`
- `paper/submission_jnca/Figure_Captions.docx`
- `paper/submission_jnca/Graphical_Abstract.png`
- `paper/submission_jnca/Graphical_Abstract.tif`
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`
- `paper/submission_jnca/submission_checklist.md`
- `paper/submission_jnca/submission_upload_manifest.md`
- `paper/submission_jnca/submission_format_audit.md`
- `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`
- `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`
- `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`
- `paper/submission_jnca/LATEX_IMPORT_TROUBLESHOOTING.md`
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`
- `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`
- `paper/submission_jnca/editorial_manager_latex_source/`
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`
- `paper/submission_jnca/overleaf_jnca/`
- `paper/submission_jnca/overleaf_jnca_package.zip`
- `paper/submission_jnca/figures/`
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_CN.tex`
- `paper/jnca_bilingual_latex/figures/`
- `paper/jnca_bilingual_latex_package.zip`
- `paper/jnca_english_overleaf_package.zip`
- `paper/jnca_chinese_xelatex_package.zip`

## Overleaf Upload Guidance

Use `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` as the preferred direct upload package for Overleaf preview and editing. It is copied from `paper/jnca_english_overleaf_package.zip` and contains only the English `main.tex`, bibliography files, generated figures under `figures/`, README, and `latexmkrc`.

Use `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` when an Elsevier/Editorial Manager-style submission system asks for LaTeX source files or rejects subfolder-based figures. This package is intentionally flat: `main.tex`, `references.bib`, `elsarticle-num.bst`, `latexmkrc`, README, and all PNG figures are at the zip root, and `main.tex` references figures without a `figures/` prefix.

Use `paper/submission_jnca/JNCA_recommended_upload_bundle.zip` as the preferred one-file handoff bundle when sending the package to a collaborator or submission operator. It contains the English Word manuscript, PDF preview, Highlights, author statements, declaration of interest, cover letter, manifest/checklist/audit notes, and the direct English Overleaf source zip. Do not import this handoff bundle directly into Overleaf because its root is a mixed submission bundle, not a LaTeX project root.

Recommended Overleaf settings:

- Main file: `main.tex`
- Compiler: pdfLaTeX
- Bibliography: BibTeX

`paper/submission_jnca/overleaf_jnca_package.zip` is kept as a fallback English package and is synchronized with the full English Overleaf source. It includes `latexmkrc` and the same pdfLaTeX-oriented import guidance.

Use `paper/jnca_chinese_xelatex_package.zip` only when checking the Chinese companion manuscript. It must be compiled with XeLaTeX; compiling it with pdfLaTeX will produce many CJK/ctex-related errors.

If Overleaf reports many errors immediately after import, check these items first:

- Read the first fatal log line first. Do not treat the later cascade as separate manuscript defects until the first fatal cause is fixed.
- The uploaded source zip should be `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, not `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, the bilingual archive, or the Chinese XeLaTeX package.
- The Overleaf main file should be `main.tex`.
- The compiler should be pdfLaTeX for the English package; use XeLaTeX only for the Chinese package.
- If the log says `elsarticle.cls not found`, the platform TeX environment lacks the Elsevier class; Overleaf normally provides it, while some submission systems may require their official template support or a platform-side LaTeX update.
- If the problem happens in the journal submission system rather than Overleaf, upload `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` instead because it avoids figure subfolders.
- If the imported project has an extra top-level folder, import the generated zip directly instead of unzipping and re-zipping it through desktop archive tools or cloud-drive exports.
- Keep the generated zips intact. Re-zipping through desktop archive tools or cloud-drive exports can add hidden/system files or an extra top-level folder that causes immediate import errors.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md` gives the same quick diagnosis next to the generated upload files.
- `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md` is the stricter import-format map: it separates the direct Overleaf source zip, the flat Editorial Manager source zip, the mixed handoff bundle, and the separate artwork zip.

## Import Format Policy

The English Overleaf package is allowed to keep figures in the `figures/` subfolder because Overleaf imports the whole project and `main.tex` references those paths. The Editorial Manager source package is intentionally flat because submission systems often handle LaTeX support files more reliably when `main.tex`, `.bib`, `.bst`, `latexmkrc`, README, and all included PNG figures are at the zip root.

Do not upload `paper/submission_jnca/JNCA_recommended_upload_bundle.zip` as a direct LaTeX project. It is a collaborator/submission-operator handoff bundle containing Word/PDF files, support notes, and nested source zips. Do not use `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip` to compile the manuscript; it is only for separate artwork upload.

The validator checks these import rules: direct source zips cannot contain Word/PDF/nested-zip/artwork-only files, Overleaf source images must match `figures/...` paths, the Editorial Manager source must be flat, and the mixed handoff bundle must remain clearly different from a direct Overleaf source package. It also checks zip-entry hygiene: generated source, figure, and handoff zips must use clean ASCII relative paths without hidden/system files, absolute paths, backslash separators, or path traversal entries.

## Bilingual LaTeX Package

`paper/jnca_bilingual_latex` is the dedicated folder for the final bilingual LaTeX deliverable. The English file uses the Elsevier `elsarticle` style for JNCA-oriented submission. The Chinese file uses `ctexart` and mirrors the same paper structure, figures, tables, core results, declarations, references, and appendices.
`paper/jnca_bilingual_latex_package.zip` is rebuilt from the same folder for direct upload or transfer.

Recommended compilers:

- English: `pdflatex -> bibtex -> pdflatex -> pdflatex`, or Overleaf with `main.tex` as the main file.
- Chinese: XeLaTeX with `main_cn.tex` as the main file in the bilingual folder, or `main.tex` in the Chinese-only zip.

## Figure Policy

Figure 1 is generated as `fig1_hsta_architecture.png` for stable Word/PDF and Overleaf preview. Result figures are generated from existing CSV summaries under `results/`. The HSTA architecture figure can still be replaced with polished artwork exported from the refined editable source `paper/论文全部图_精修可编辑.drawio` before final upload.
The Overleaf package includes `README.md` for upload guidance and `figure_notes.md` for generated-figure and replacement notes.

Word/PDF figure captions are generated with continuous Figure 1-4 numbering. `paper/submission_jnca/Figure_Captions.docx` stores the separate caption list, `paper/submission_jnca/Graphical_Abstract.png` is an optional graphical-abstract preview, `paper/submission_jnca/Graphical_Abstract.tif` is the Elsevier-preferred artwork candidate, and `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip` bundles the four figure PNGs, graphical abstract files, and captions for submission systems that request separate artwork files.

The validator checks artwork integrity before upload: Figure 1-4 PNG files must have valid PNG headers and minimum pixel dimensions, graphical abstract PNG/TIFF files must satisfy the Elsevier-style minimum size and share the same dimensions, and every artwork entry in `FIGURES_FOR_UPLOAD.zip` must match the generated source file byte-for-byte.

## Word Review Format

The English Word manuscript is generated as a review-friendly file with 12 pt Times New Roman Normal style, double-spaced body paragraphs, continuous line numbering, and footer page-number fields. Tables keep compact table text, repeat header rows across page breaks, and mark rows as non-splitting so labels and values are not separated across pages. The validator reads both python-docx style data and the underlying Word XML so missing line-number, page-number, repeated-header, or non-splitting-row markers are caught before upload.

Appendices start on a new Word/PDF page after the reference list. This keeps appendix headings and mapping tables from being stranded at the bottom of the final reference page after narrative or reference-list changes.

Generated Word files also receive controlled core document properties: title, subject, placeholder author metadata, keywords, category, and comments. This prevents the default generator metadata from leaking into the manuscript or support files. The validator checks the main Word manuscripts and separate support files for these controlled properties.

## Word Structure Hygiene Policy

The English Word manuscript must keep one controlled title, the expected heading sequence, continuous table captions from Table 1-10 plus Appendix A/B, repeated table header rows, non-splitting table rows, no duplicate table captions, no CJK characters in the English body, no editable figure placeholder text, and no repeated plain spaces. The validator checks these items so Word/PDF review artifacts do not silently drift from the LaTeX source or expose draft-only placeholders.

## LaTeX Table Policy

Generated LaTeX tables with five or more columns are wrapped in `\resizebox{\linewidth}{!}{...}` unless they already use `tabularx`. This reduces Overleaf overflow risk for the main results, ablation, efficiency, transfer, depth, and confusion tables. The validator checks this rule so newly added wide tables do not silently overflow.

## LaTeX Package Order Policy

English `elsarticle` sources load `lineno` before `hyperref` so line numbering and hyperlink support follow a conservative Overleaf/Elsevier package order. The validator checks this order for English LaTeX outputs.

## Elsevier Frontmatter Policy

English `elsarticle` sources keep the title, abstract, Highlights, and keywords inside `frontmatter`, then enable `\linenumbers` before the first numbered section. The validator checks this order because misplaced Highlights, keywords, or line numbering can cause confusing Overleaf or portal-side errors.

Author affiliations use legacy-compatible `\address[...]` markers instead of newer structured `\affiliation[...]` fields. This keeps the generated source acceptable to both current Overleaf-style Elsevier classes and older journal-portal TeX environments that do not define `\affiliation`.

## Source Text Hygiene Policy

Generated English LaTeX and BibTeX sources are kept UTF-8 decodable, BOM-free, NUL-free, and free of mixed newline styles. English `elsarticle` sources and `references.bib` are also kept ASCII-safe to reduce pdfLaTeX import and compilation surprises. The validator checks both folder files and packaged zip entries.

## Elsevier Template Dependency Policy

The generated source packages include `elsarticle-num.bst` copied from the official Elsevier template bundle, and the validator checks packaged copies against that official source. The repository's official template bundle contains `elsarticle.dtx` and `elsarticle.ins`, but not a pre-extracted `elsarticle.cls`; because no local TeX engine is available in this environment, the package does not fabricate a class file. English compilation therefore expects `elsarticle.cls` from Overleaf or from the submission system's TeX installation. If a portal reports `elsarticle.cls not found`, treat it as a platform/template-environment issue rather than a manuscript-body error.

## LaTeX Cross-Reference Policy

The generated English LaTeX manuscript references every non-appendix table and figure, including the method figure, dataset table, adapted-baseline table, main-result tables and figure, scaling table, ablation table and figure, efficiency table, depth table, transfer table and figure, and confusion table. The validator checks that `\ref{...}` targets exist and that all non-appendix table/figure labels are referenced in the full English manuscript.

## LaTeX Label Hygiene Policy

Generated LaTeX labels must be unique, portable ASCII-style names made from letters, digits, colons, and hyphens. Table and figure labels use standard `tab:` and `fig:` prefixes so cross-references remain readable and stable across Overleaf, Editorial Manager, and local TeX tools.

## LaTeX Float Hygiene Policy

Generated table and figure floats must have one nonempty caption, one label, labels placed after captions, and an expected body (`\includegraphics` for figures and a tabular-like body for tables). This catches common source-editing mistakes that otherwise create cascaded compile errors or broken references after import.

## Source Package README Policy

Generated source zips must include a README that matches the package layout, compiler, figure-path convention, and platform-specific use. The validator checks that Overleaf packages explain the `figures/` layout and warn against importing `JNCA_recommended_upload_bundle.zip`, while the Editorial Manager package explains its flat root-level layout.

## Citation Coverage Policy

The generated Word/PDF manuscripts and English Overleaf package both include numerical citations for protocol standards, traffic-classification surveys, CESNET/DataZoo datasets, representative deep/pretrained traffic models, JNCA/TNSM/ToN multimodal encrypted-traffic studies, state-space/Mamba models, adapted NetMamba baseline context, LoRA adaptation, long-term drift/generalization limitations, and shortcut-aware diagnostic work. The validator checks Word in-text citation markers and expanded BibTeX/citation-key coverage so the Word manuscript and Overleaf source do not silently diverge.

## BibTeX Integrity Policy

The generated English LaTeX packages share one synchronized `references.bib` source. The validator checks that BibTeX keys are unique, entries contain required fields for their entry type, years use four digits, entries do not contain placeholder-like text, citation keys resolve, and packaged `references.bib` files match the submission Overleaf copy.

## LaTeX Highlights Policy

English `elsarticle` sources place the four Highlights in the official `highlights` environment inside the frontmatter, before the keyword block. The validator rejects English LaTeX files that are missing this environment or place Highlights as a body `\section*{Highlights}`. The separate `Highlights.docx` file is still generated for Elsevier submission systems that request Highlights as an individual upload item.

## Word/LaTeX Alignment Policy

The English Word manuscript remains the primary editable review file, while the English LaTeX package is the reproducible Overleaf/source-upload version. To avoid silent drift between the two outputs, the validator cross-checks the title, keywords, Highlights, core abstract result markers, and main section titles between `JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/overleaf_jnca/main.tex`.

## Narrative Reference Notes

`docs/jnca_reference_narrative_notes.md` records the external encrypted-traffic papers used as writing references for the English manuscript. It is a positioning and narrative-quality note only; it does not introduce new experiments, new result values, or new claims beyond the generated manuscript.

The validator checks that this note remains present and still records the core reference set used for narrative refinement, including validity framing, representation framing, JNCA-style multimodal framing, efficiency framing, traffic-specific representation framing, dataset-boundary framing, data-drift framing, shortcut-diagnostic framing, and reproducibility framing.

The English narrative uses these reference papers to maintain a reader contract: observable inputs, controlled comparison scope, traffic unit, and bounded claims must be clear before presenting model gains. The Experimental Setup and Results sections are written as an evidence ladder, where main scores establish recognition quality, ablation provides mechanism evidence, efficiency measures deployment cost, and transfer probes representation reuse. Attention-position ablation is treated as a negative control against the simpler claim that any attention module would help.

The English SCI manuscript keeps a dedicated `Threats to Validity` section after Discussion. This section is used to state controlled-input scope, external-validity limits, construct-validity limits, and deployment-measurement limits without changing the experimental results or adding unsupported claims.

## Guide-For-Authors Compliance Audit

`paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md` is generated as a compact JNCA/Elsevier pre-upload audit. It records editable source files, direct Overleaf and flat Editorial Manager source packages, abstract word count, keyword count, Highlights count and character lengths, graphical abstract dimensions, and remaining manual checks. English keywords are capped at 6 items in the generated Word and LaTeX manuscripts. The validator checks this audit so common portal-side issues are caught before upload.

## Placeholder Replacement Audit

`paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md` is generated as the final metadata and anonymity checklist. It scans key Word/support files plus the direct Overleaf and flat Editorial Manager LaTeX sources for placeholder markers, then reports both per-file counts and a token inventory for author names, affiliations, corresponding email, funding, acknowledgements, repository policy, and generic placeholder markers. Use it to replace metadata consistently across Word and LaTeX outputs, or to prepare a separate anonymized package if the portal requires blinded review.

## Import Format Audit

`paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md` is generated as the final import-format checklist. It records which package should be used for Overleaf, which package should be used for Editorial Manager-style LaTeX source upload, which files are only for artwork upload, and why importing the mixed handoff bundle creates many immediate errors.

`paper/submission_jnca/LATEX_IMPORT_TROUBLESHOOTING.md` is generated as the first-response guide for long Overleaf or journal-portal error cascades. It maps common first errors to the likely root cause: wrong zip, wrong compiler, missing `elsarticle.cls`, figure subfolder handling, or incomplete BibTeX passes.

## Submission Placeholders

The generated manuscripts intentionally keep author names, affiliations, funding, acknowledgements, repository links, and corresponding-author email as placeholders. Replace them before formal submission, or remove them if an anonymized review file is required.

## Highlights File

`paper/submission_jnca/Highlights.docx` is generated as a separate Elsevier-style highlights file. The English manuscript and LaTeX packages use the same four concise highlights, each kept under the usual 85-character Elsevier limit.

## Author Statements File

`paper/submission_jnca/Author_Statements.docx` is generated as a submission-support file containing CRediT-style author contributions, funding, competing-interest, data/code availability, and acknowledgement sections. It intentionally keeps placeholders and must be confirmed by all authors before formal submission.

## Declaration Of Interest File

`paper/submission_jnca/Declaration_of_Interest_Statement.docx` is generated as a separate no-competing-interest statement placeholder for Elsevier-style submission systems that request this item as an individual upload file. Confirm the wording with all authors before formal submission.

## Cover Letter And Upload Manifest

`paper/submission_jnca/Cover_Letter.docx` is generated as a draft cover letter for Journal of Network and Computer Applications. It includes placeholders for the date, editor, corresponding author, originality confirmation, conflict statement, and optional reviewer/funding details; these must be confirmed before upload.

`paper/submission_jnca/submission_upload_manifest.md` is generated as a practical file map for the submission package. It lists recommended upload files, optional/internal support files, and final manual checks before submission.

`paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md` is generated beside the submission files to separate the direct Overleaf source zip from the mixed handoff bundle. This is intended to prevent importing `JNCA_recommended_upload_bundle.zip` as if it were a LaTeX project.

`paper/submission_jnca/submission_format_audit.md` is generated as a compact Word/PDF/Overleaf format audit. It records Word table and figure counts, margins, headings, PDF export status, separate submission-file coverage, source-package guidance, and remaining manual formatting checks.

## Validation

Run `scripts/validate_jnca_submission.py` with the project Anaconda interpreter after regenerating the package. The validator exits with a nonzero status if required manuscript files, PDF header/EOF/page-object/content-stream/font-image-resource/raw-metadata-marker/timestamp checks, Word table/image counts, English Word review format, repeated table header rows, non-splitting table rows, Word core document properties, abstract word count, Word/LaTeX keyword count, English Word result-table contents, Word/LaTeX title-keyword-highlight-section alignment, continuous Figure 1-4 captions, Word in-text citation markers, Highlights length, declaration files, declaration-of-interest file, figure captions, graphical abstract PNG/TIFF headers and dimensions, figure upload bundle, format audit, Guide-for-Authors compliance audit, placeholder replacement audit, import-format audit, LaTeX import troubleshooting note, LaTeX figure paths/citations, Elsevier frontmatter order, table/figure caption-label hygiene, expanded BibTeX coverage, BibTeX integrity, key result values, Overleaf zip root layout, compiler hints, README/package consistency, source-zip import hygiene, upload-bundle contents, zip contents, or zip-entry hygiene are inconsistent.
