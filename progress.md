## 2026-07-01 - Task: Improve JNCA English SCI manuscript package
### What was done
- Strengthened the JNCA English manuscript generation flow into a fuller SCI-style article while preserving author, affiliation, funding, email, and repository placeholders.
- Added automatic result-figure generation for main Macro-F1, attention-position ablation, and cross-protocol transfer, with figures embedded in the Word manuscript and included in the Overleaf package.
- Refreshed the English Word manuscript, Chinese companion manuscript, English PDF, Overleaf package, and submission checklist from repository CSV summaries without rerunning training experiments.
- Documented the manuscript generation entry points and added the missing manuscript-generation dependencies.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; generated `paper/submission_jnca/overleaf_jnca`, result PNG figures, and `paper/submission_jnca/overleaf_jnca_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; generated `JNCA_HSTA_Encrypted_Traffic_CN.docx`, `JNCA_HSTA_Encrypted_Traffic_EN.docx`, `JNCA_HSTA_Encrypted_Traffic_EN.pdf`, and `submission_checklist.md`.
- Verified `JNCA_HSTA_Encrypted_Traffic_EN.pdf` exists, has nonzero size, and starts with `%PDF-`.
- Verified the English Word manuscript has 13 tables and 3 embedded generated result figures; spot-checked HSTA-Hybrid main table values: QUIC-40 Macro-F1 `91.09±0.20`, QUIC-60 Macro-F1 `90.28±0.39`, TLS-40 Macro-F1 `96.78±0.14`, and TLS-60 Macro-F1 `96.29±0.17`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_overleaf.py`.

### Notes
- `requirements.txt`: added `python-docx` and `matplotlib` for reproducible manuscript and figure generation.
- `scripts/generate_jnca_submission.py`: updated the Word/PDF manuscript generator to select an existing source manuscript, generate/reuse result figures, embed figures, translate extracted English table headers, and refresh checklist figure status.
- `scripts/generate_jnca_overleaf.py`: updated the Overleaf generator to produce result figures, include them in LaTeX, and expand the English SCI-style narrative.
- `docs/jnca_submission_generation.md`: documented how to regenerate the JNCA manuscript package and which placeholders remain before submission.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated the Chinese companion manuscript from the updated script.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated the strengthened English SCI manuscript with embedded result figures.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated the English PDF through Microsoft Word COM.
- `paper/submission_jnca/submission_checklist.md`: refreshed generated-artifact, data-consistency, and figure-status checks.
- `paper/submission_jnca/figures/`: added generated PNG result figures for main Macro-F1, ablation, and transfer comparisons.
- `paper/submission_jnca/overleaf_jnca/`: regenerated the Overleaf package contents, including `main.tex`, README, figure note, references, and result PNG figures.
- `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated the upload package.
- Rollback: restore the previous manuscript package and scripts from the prior git state, or delete `paper/submission_jnca/figures`, `docs/jnca_submission_generation.md`, and `progress.md`, then revert `requirements.txt`, `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, and regenerated files under `paper/submission_jnca`.

## 2026-07-01 - Task: Add standalone bilingual LaTeX manuscript package
### What was done
- Added a reproducible bilingual LaTeX generation flow for a dedicated `paper/jnca_bilingual_latex` folder.
- Generated `JNCA_HSTA_Encrypted_Traffic_EN.tex` as an English JNCA/Elsevier LaTeX manuscript and `JNCA_HSTA_Encrypted_Traffic_CN.tex` as the corresponding Chinese LaTeX manuscript.
- Aligned the two LaTeX manuscripts around the same structure, core results, generated figures, tables, declarations, references, and appendices.
- Updated the generation documentation to include the bilingual LaTeX entry point and compiler guidance.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; generated `paper/jnca_bilingual_latex`.
- Verified `JNCA_HSTA_Encrypted_Traffic_EN.tex` exists, contains 12 table environments, 4 figures, an appendix, generated result figures, adapted-baseline boundary wording, and key scores `91.09`, `90.28`, `96.78`, and `96.29`.
- Verified `JNCA_HSTA_Encrypted_Traffic_CN.tex` exists, contains 12 table environments, 4 figures, an appendix, generated result figures, and the same key scores.
- Verified shared figure files exist under `paper/jnca_bilingual_latex/figures/`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py`.
- Checked for local `pdflatex` and `xelatex`; neither command is available in this environment, so local PDF compilation was not performed.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: added a generator for the standalone bilingual LaTeX package.
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`: generated the English LaTeX manuscript.
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_CN.tex`: generated the corresponding Chinese LaTeX manuscript.
- `paper/jnca_bilingual_latex/figures/`: copied generated result figures used by both manuscripts.
- `paper/jnca_bilingual_latex/references.bib` and `paper/jnca_bilingual_latex/elsarticle-num.bst`: copied bibliography support for the English manuscript.
- `paper/jnca_bilingual_latex/README.md`: added package-level compilation and submission notes.
- `paper/jnca_bilingual_latex_package.zip`: generated the standalone bilingual LaTeX upload package.
- `docs/jnca_submission_generation.md`: documented the bilingual LaTeX generation command and compiler expectations.
- Rollback: delete `paper/jnca_bilingual_latex` and `paper/jnca_bilingual_latex_package.zip`, revert `scripts/generate_jnca_bilingual_latex.py`, and restore `docs/jnca_submission_generation.md` and `progress.md` to the previous state.

## 2026-07-01 - Task: Finalize JNCA package integrity checks
### What was done
- Added standard `README.md` and `figure_notes.md` outputs to the Overleaf package while keeping the previous Overleaf README and figure note filenames for compatibility.
- Regenerated the Overleaf upload package, English/Chinese Word manuscripts, English PDF, and submission checklist from the scripted workflow.
- Updated the generation documentation and checklist wording so the required Overleaf package files are explicit.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; regenerated `paper/submission_jnca/overleaf_jnca` and `paper/submission_jnca/overleaf_jnca_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; regenerated `JNCA_HSTA_Encrypted_Traffic_CN.docx`, `JNCA_HSTA_Encrypted_Traffic_EN.docx`, `JNCA_HSTA_Encrypted_Traffic_EN.pdf`, and `submission_checklist.md`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`.
- Verified the English PDF starts with `%PDF-`.
- Verified English and Chinese Word manuscripts exist, contain at least 10 tables, at least 3 embedded generated figures, key scores `91.09`, `90.28`, `96.78`, and `96.29`, and adapted-baseline boundary wording.
- Verified the Overleaf package contains `main.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `figure_notes.md`, and generated PNG result figures.
- Verified `paper/jnca_bilingual_latex_package.zip` still contains the English/Chinese LaTeX files, README, bibliography files, and generated figure assets.
- Checked local LaTeX compiler availability; `pdflatex`, `xelatex`, `latexmk`, `tectonic`, and `lualatex` were not found, so local LaTeX PDF compilation was not performed.

### Notes
- `scripts/generate_jnca_overleaf.py`: now writes `README.md` and `figure_notes.md` into the Overleaf package and includes them in the generated zip.
- `scripts/generate_jnca_submission.py`: checklist generation now states the required Overleaf support files.
- `docs/jnca_submission_generation.md`: documented the Overleaf README and figure-notes outputs.
- `paper/submission_jnca/overleaf_jnca/`: regenerated with standard README and figure-notes files.
- `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated with the required Overleaf files.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/submission_checklist.md`: refreshed with the Overleaf package integrity note.
- Rollback: revert the three script/documentation changes from this task, restore the previous generated files under `paper/submission_jnca`, and remove `README.md` and `figure_notes.md` from `paper/submission_jnca/overleaf_jnca` if strict old package layout is required.

## 2026-07-01 - Task: Polish bilingual LaTeX manuscript formatting
### What was done
- Improved the standalone bilingual LaTeX generator so formula-sensitive problem-definition text is emitted as proper inline LaTeX math in both English and Chinese manuscripts.
- Improved long explanatory table formatting with `tabularx` and fixed-width columns to reduce overflow risk in the adapted-baseline description table.
- Tightened appendix long-table layout for label maps and expanded the bilingual package README with formatting and submission-check guidance.
- Regenerated the standalone bilingual LaTeX folder and zip package from the updated script.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; regenerated `paper/jnca_bilingual_latex` and `paper/jnca_bilingual_latex_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_bilingual_latex.py`.
- Verified both `JNCA_HSTA_Encrypted_Traffic_EN.tex` and `JNCA_HSTA_Encrypted_Traffic_CN.tex` include `tabularx`, use math forms for `$x_t$`, `$f_\theta:X\rightarrow y$`, and `$30\times3$`, contain no internal `@@` markers, and do not contain the previous broken mapping form.
- Verified both LaTeX manuscripts contain 4 figures, at least 10 table environments, 2 appendix long tables, key scores `91.09`, `90.28`, `96.78`, and `96.29`, adapted-baseline boundary wording, and preserved author/funding placeholder fields.
- Verified generated figure PNG files and support files `README.md`, `references.bib`, and `elsarticle-num.bst` exist in `paper/jnca_bilingual_latex`.
- Verified `paper/jnca_bilingual_latex_package.zip` contains the English and Chinese LaTeX files, README, bibliography support, and generated figure assets.
- Checked local LaTeX compiler availability earlier in this task; `pdflatex`, `xelatex`, `latexmk`, `tectonic`, and `lualatex` were not found, so local PDF compilation was not performed.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: improved LaTeX escaping for formula-sensitive text, added `tabularx` support, tightened long-table layout, and expanded README guidance.
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`: regenerated with corrected math notation and more stable long-table formatting.
- `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_CN.tex`: regenerated with corresponding corrected math notation and more stable long-table formatting.
- `paper/jnca_bilingual_latex/README.md`: regenerated with formatting notes and submission checks.
- `paper/jnca_bilingual_latex_package.zip`: regenerated from the polished bilingual LaTeX folder.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: refreshed as a side effect of the bilingual generator copying current Overleaf support files and result figures.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, restore the previous `paper/jnca_bilingual_latex` folder and zip package, and remove this progress entry if strict restoration to the prior LaTeX output is required.

## 2026-07-01 - Task: Fix Overleaf entry-point and package structure
### What was done
- Diagnosed the likely Overleaf error source: the bilingual zip previously had no default `main.tex`, so Overleaf could auto-select the Chinese `ctexart` file and compile it with pdfLaTeX, causing many cascading errors.
- Added a default English `main.tex` with a pdfLaTeX hint and a Chinese `main_cn.tex` with a XeLaTeX hint in `paper/jnca_bilingual_latex`.
- Added two safer upload packages: an English-only Overleaf package for the JNCA submission draft and a Chinese-only XeLaTeX package for companion checking.
- Updated the bilingual README to explain which package and compiler should be used.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; regenerated the bilingual folder plus `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_bilingual_latex.py`.
- Verified `main.tex`, `main_cn.tex`, the English `.tex`, and the Chinese `.tex` have balanced LaTeX environments, no internal `@@` markers, 4 figures, key scores `91.09`, `90.28`, `96.78`, and `96.29`, valid figure paths, and complete citation keys.
- Verified `jnca_english_overleaf_package.zip` contains English `main.tex`, bibliography support, README, and figure assets, and does not include the Chinese main file.
- Verified `jnca_chinese_xelatex_package.zip` contains a XeLaTeX `main.tex`, Chinese manuscript, README, and figure assets.
- Checked local LaTeX compiler availability; `pdflatex`, `xelatex`, `latexmk`, `tectonic`, and `lualatex` were not found, so true local PDF compilation still must be done in Overleaf or another LaTeX environment.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: now writes default entry files and builds separate English and Chinese upload zips.
- `paper/jnca_bilingual_latex/main.tex`: added as the English default Overleaf entry file.
- `paper/jnca_bilingual_latex/main_cn.tex`: added as the Chinese XeLaTeX entry file.
- `paper/jnca_bilingual_latex/README.md`: updated with recommended upload packages and compiler guidance.
- `paper/jnca_bilingual_latex_package.zip`: regenerated as the archival bilingual package with explicit entry files.
- `paper/jnca_english_overleaf_package.zip`: added as the recommended English JNCA upload package.
- `paper/jnca_chinese_xelatex_package.zip`: added as the recommended Chinese companion upload package.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, delete the two specialized zip packages, and restore the previous `paper/jnca_bilingual_latex` folder and bilingual zip if the old package layout is required.

## 2026-07-01 - Task: Harden Overleaf compiler selection
### What was done
- Added `latexmkrc` compiler hints so the bilingual and English packages default to pdfLaTeX while the Chinese package defaults to XeLaTeX.
- Replaced the shared README inside the specialized English and Chinese zip files with package-specific instructions to avoid main-file and compiler confusion.
- Regenerated all LaTeX packages after the compiler-selection changes.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; regenerated `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_bilingual_latex.py`.
- Verified `main.tex`, `main_cn.tex`, and both named manuscript files have balanced LaTeX environments, no internal `@@` markers, key result scores, and valid generated figure paths.
- Verified the bilingual zip contains `main.tex`, `main_cn.tex`, `README.md`, `latexmkrc`, bibliography support, and generated figures, with `latexmkrc` set to pdfLaTeX.
- Verified the English Overleaf zip contains only the English `main.tex`, README, `latexmkrc`, bibliography support, and figures, with no Chinese manuscript file.
- Verified the Chinese XeLaTeX zip contains a Chinese `main.tex`, README, `latexmkrc`, and figures, with `latexmkrc` set to XeLaTeX.
- Local TeX engines remain unavailable, so final PDF compilation must still be verified on Overleaf or another LaTeX installation.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: now writes compiler-specific README and `latexmkrc` files into specialized upload packages and the bilingual folder.
- `paper/jnca_bilingual_latex/latexmkrc`: added pdfLaTeX default for the mixed bilingual folder.
- `paper/jnca_bilingual_latex/README.md`: updated to explain specialized upload packages and compiler hints.
- `paper/jnca_bilingual_latex_package.zip`: regenerated with root `latexmkrc`.
- `paper/jnca_english_overleaf_package.zip`: regenerated with English-only README and pdfLaTeX `latexmkrc`.
- `paper/jnca_chinese_xelatex_package.zip`: regenerated with Chinese-specific README and XeLaTeX `latexmkrc`.
- Rollback: revert the package-writing changes in `scripts/generate_jnca_bilingual_latex.py`, delete regenerated zip packages, and remove `paper/jnca_bilingual_latex/latexmkrc` if the previous package behavior is required.

## 2026-07-01 - Task: Improve LaTeX float and figure formatting robustness
### What was done
- Reduced remaining Overleaf formatting risk by resizing the TikZ HSTA architecture figure to `\linewidth` in both English and Chinese manuscripts.
- Changed manuscript table and figure floats to `[!htbp]` to reduce float-placement pileups in the long manuscript.
- Added `placeins` section-level float barriers while avoiding unnecessary `float` package dependency.
- Regenerated the bilingual folder and all three upload packages after these format changes.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; regenerated `paper/jnca_bilingual_latex`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_bilingual_latex.py`.
- Verified `main.tex`, `main_cn.tex`, and both named manuscript files have balanced LaTeX environments, no internal `@@` markers, key result scores, valid generated figure paths, resized TikZ figures, `[!htbp]` figure/table floats, and `placeins` support.
- Verified all three zip packages contain `main.tex`, README, `latexmkrc`, and generated figure assets.
- Confirmed local TeX engines remain unavailable, so final PDF compilation still needs Overleaf or another TeX installation.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: updated figure/table float options, resized TikZ architecture figures, retained section float barriers, and regenerated packages.
- `paper/jnca_bilingual_latex/main.tex` and `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`: regenerated with improved figure/table formatting.
- `paper/jnca_bilingual_latex/main_cn.tex` and `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_CN.tex`: regenerated with corresponding Chinese formatting changes.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the formatting changes.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, restore the previous generated LaTeX folder and zip packages, and remove this progress entry if the prior formatting is required.

## 2026-07-01 - Task: Check and harden Overleaf import formatting
### What was done
- Diagnosed the likely source of many Overleaf import errors as package/entry/compiler confusion, especially the coexistence of older English package, bilingual package, and Chinese XeLaTeX package.
- Hardened the original `submission_jnca` Overleaf generator so its English package now has a pdfLaTeX `latexmkrc`, clearer README import checks, resized TikZ architecture figure, and `[!htbp]` table/figure floats.
- Updated the submission checklist and generation documentation to explicitly recommend `paper/jnca_english_overleaf_package.zip` for the English SCI draft, with `main.tex` as the main file and pdfLaTeX + BibTeX as the compile path.
- Regenerated the original Overleaf package, English/Chinese Word manuscripts, English PDF, standalone bilingual LaTeX folder, English-only Overleaf zip, Chinese-only XeLaTeX zip, and bilingual archive zip.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Verified `paper/submission_jnca/overleaf_jnca/main.tex`, `paper/jnca_bilingual_latex/main.tex`, `main_cn.tex`, and both named `.tex` manuscripts have balanced LaTeX environments, no internal `@@` markers, valid generated figure paths, complete citation keys, resized TikZ figures, and `[!htbp]` floats.
- Verified `paper/jnca_english_overleaf_package.zip`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex_package.zip`, and `paper/jnca_chinese_xelatex_package.zip` contain their required main files, README, `latexmkrc`, bibliography or figure support files as applicable.
- Verified the English-only Overleaf zip does not include Chinese `.tex` files, and the Chinese-only zip uses `$pdf_mode = 5;` for XeLaTeX.
- Verified the regenerated English and Chinese Word manuscripts each contain 13 tables and 3 embedded images.
- Verified `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.
- Verified key values `91.09`, `90.28`, `96.78`, `96.29`, `30pktTCNET-adapted`, and `NetMamba-adapted` remain present in the regenerated English LaTeX manuscript.
- Local TeX engines are still unavailable in this environment, so true PDF compilation must be checked on Overleaf or another TeX installation.

### Notes
- `scripts/generate_jnca_overleaf.py`: added pdfLaTeX entry comments, `latexmkrc` generation, README import troubleshooting, table/figure float hardening, wide-table resizing, and resized TikZ architecture figure.
- `scripts/generate_jnca_submission.py`: updated checklist guidance to distinguish the recommended English package, fallback English package, and Chinese XeLaTeX package.
- `docs/jnca_submission_generation.md`: documented the preferred Overleaf upload package, compiler settings, fallback package, and Chinese XeLaTeX package boundary.
- `paper/submission_jnca/overleaf_jnca/`: regenerated the original English Overleaf package folder with `latexmkrc` and updated README.
- `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated the fallback English Overleaf zip.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/submission_checklist.md`: refreshed with package-selection and compiler guidance.
- `paper/jnca_bilingual_latex/`: regenerated the bilingual LaTeX folder from the current scripts.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the import-format checks.
- Rollback: revert `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated folders/zips under `paper/submission_jnca` and `paper/jnca_bilingual_latex`.

## 2026-07-01 - Task: Add stable generated HSTA architecture figure
### What was done
- Added automatic generation of `fig1_hsta_architecture.png` so the HSTA architecture appears as a real figure in Word, PDF, and Overleaf outputs instead of a Word placeholder or a TikZ-only figure.
- Updated the original Overleaf package and standalone bilingual LaTeX package to include Figure 1 as a PNG, reducing main-manuscript package dependencies and making Overleaf import more robust.
- Kept `fig_hsta_block.tex` as an editable TikZ replacement source and documented that the generated Figure 1 PNG can be replaced by polished draw.io artwork before final submission.
- Regenerated the original Overleaf package, English/Chinese Word manuscripts, English PDF, bilingual LaTeX folder, English-only Overleaf zip, Chinese-only XeLaTeX zip, and bilingual archive zip.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Verified `paper/submission_jnca/overleaf_jnca/main.tex`, `paper/jnca_bilingual_latex/main.tex`, `main_cn.tex`, and both named `.tex` manuscripts have balanced LaTeX environments, no internal `@@` markers, no missing figure paths, complete citation keys, four figures, and `[!htbp]` floats.
- Verified English LaTeX main files contain no non-ASCII characters and no longer require `\usepackage{tikz}` in the main manuscript.
- Verified `paper/jnca_english_overleaf_package.zip`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex_package.zip`, and `paper/jnca_chinese_xelatex_package.zip` include `figures/fig1_hsta_architecture.png` and their required main files, README, `latexmkrc`, bibliography, and figure support files as applicable.
- Verified the regenerated English and Chinese Word manuscripts each contain 12 tables and 4 embedded images, including Figure 1.
- Verified `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.
- Visually inspected `paper/submission_jnca/figures/fig1_hsta_architecture.png`; text is legible and does not overlap.
- Verified key values `91.09`, `90.28`, `96.78`, `96.29`, `30pktTCNET-adapted`, and `NetMamba-adapted` remain present in the regenerated English LaTeX manuscript.
- Local TeX engines remain unavailable in this environment, so true LaTeX PDF compilation still needs Overleaf or another TeX installation.

### Notes
- `scripts/generate_jnca_submission.py`: added generated HSTA architecture figure creation and embedded it as Figure 1 in Word manuscripts.
- `scripts/generate_jnca_overleaf.py`: added generated Figure 1 PNG, cleaned the Overleaf output folder before regeneration, switched the main manuscript from embedded TikZ to PNG Figure 1, and updated figure notes.
- `scripts/generate_jnca_bilingual_latex.py`: switched English and Chinese LaTeX manuscripts to the generated Figure 1 PNG and updated package README guidance.
- `docs/jnca_submission_generation.md`: documented that Figure 1 is generated for stable preview and can be replaced by polished draw.io artwork.
- `paper/submission_jnca/figures/fig1_hsta_architecture.png`: added generated HSTA architecture overview.
- `paper/submission_jnca/overleaf_jnca/`: regenerated with the PNG Figure 1 and updated notes.
- `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated with the PNG Figure 1.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated with embedded Figure 1.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated with embedded Figure 1.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/submission_checklist.md`: refreshed with Figure 1 generation status.
- `paper/jnca_bilingual_latex/`: regenerated with Figure 1 PNG references in both language manuscripts.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with the PNG Figure 1.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips under `paper/submission_jnca` and `paper/jnca_bilingual_latex`.

## 2026-07-01 - Task: Align Highlights with Elsevier submission expectations
### What was done
- Shortened the English Highlights to four concise bullets, each under the usual Elsevier 85-character limit.
- Added a separate `Highlights.docx` file for Elsevier-style submission upload while keeping the same Highlights in the manuscript and LaTeX packages.
- Updated the original Overleaf fallback package and standalone bilingual LaTeX package so their Highlights match the Word manuscript.
- Updated generation documentation and the submission checklist to list `Highlights.docx` and record the character-limit check.
- Regenerated the original Overleaf package, English/Chinese Word manuscripts, English PDF, bilingual LaTeX folder, English-only Overleaf zip, Chinese-only XeLaTeX zip, and bilingual archive zip.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; generated `Highlights.docx` and exported the English PDF successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Verified `paper/submission_jnca/Highlights.docx` exists, contains four Highlights, and every bullet is under 85 characters.
- Verified the previous `paper/submission_jnca/JNCA_Highlights.docx` alias is removed to avoid upload-file ambiguity.
- Verified the Highlights in `paper/jnca_bilingual_latex/main.tex` and `paper/submission_jnca/overleaf_jnca/main.tex` match the shortened four bullets and remain under 85 characters.
- Verified `paper/submission_jnca/submission_checklist.md` and `docs/jnca_submission_generation.md` mention `Highlights.docx` and do not mention the removed alias.
- Verified `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.
- Verified the regenerated English Overleaf zips contain `main.tex`, `latexmkrc`, and `figures/fig1_hsta_architecture.png`.

### Notes
- `scripts/generate_jnca_submission.py`: shortened English Highlights, added `Highlights.docx` generation, removed the old highlights alias during regeneration, and updated checklist wording.
- `scripts/generate_jnca_overleaf.py`: shortened Highlights in the fallback English Overleaf manuscript.
- `docs/jnca_submission_generation.md`: added `Highlights.docx` to generated outputs and documented the highlights file.
- `paper/submission_jnca/Highlights.docx`: added separate highlights upload file.
- `paper/submission_jnca/submission_checklist.md`: regenerated with highlights-file and character-limit evidence.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated with shortened Highlights.
- `paper/jnca_bilingual_latex/`: regenerated with shortened Highlights.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with shortened Highlights.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, and `docs/jnca_submission_generation.md`; delete `paper/submission_jnca/Highlights.docx`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add separate author statements file
### What was done
- Added a separate `Author_Statements.docx` submission-support file covering CRediT-style author contributions, funding, competing interests, data/code availability, and acknowledgements.
- Centralized declaration text in the Word generator so the manuscript declaration section and standalone author-statements file stay aligned.
- Updated the English, Chinese, fallback Overleaf, and bilingual LaTeX declaration text to use CRediT-style author contribution wording while preserving placeholders for final author confirmation.
- Updated the submission checklist and generation documentation to list the author-statements file and call out the need for all-author confirmation.
- Regenerated the original Overleaf package, English/Chinese Word manuscripts, English PDF, bilingual LaTeX folder, English-only Overleaf zip, Chinese-only XeLaTeX zip, and bilingual archive zip.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; generated `Author_Statements.docx` and exported the English PDF successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Verified `paper/submission_jnca/Author_Statements.docx` exists and contains sections for CRediT author contributions, funding, declaration of competing interest, data/code availability, and acknowledgements.
- Verified `Author_Statements.docx` retains placeholder warnings so it is not mistaken for final signed author approval.
- Verified the regenerated English and Chinese Word manuscripts each contain 12 tables, 4 embedded images, CRediT wording, and competing-interest/declaration content.
- Verified `paper/jnca_bilingual_latex/main.tex` and `paper/submission_jnca/overleaf_jnca/main.tex` contain `Author contributions (CRediT)` and the competing-interest declaration.
- Verified Chinese Word and LaTeX manuscripts contain author contribution, CRediT, funding, conflict-of-interest, data/code availability, and acknowledgement sections.
- Verified `paper/submission_jnca/submission_checklist.md` and `docs/jnca_submission_generation.md` mention `Author_Statements.docx` and CRediT.
- Verified `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.
- Verified the regenerated English Overleaf zips contain `main.tex`, `latexmkrc`, and `figures/fig1_hsta_architecture.png`, and their `main.tex` includes CRediT wording.

### Notes
- `scripts/generate_jnca_submission.py`: added shared declaration data, generated `Author_Statements.docx`, updated manuscript declarations, and refreshed checklist wording.
- `scripts/generate_jnca_overleaf.py`: updated fallback Overleaf declaration wording to use CRediT-style contributions.
- `scripts/generate_jnca_bilingual_latex.py`: updated English and Chinese LaTeX declaration wording to use CRediT-style contributions.
- `docs/jnca_submission_generation.md`: documented the generated author-statements file.
- `paper/submission_jnca/Author_Statements.docx`: added separate author-statements upload/support file.
- `paper/submission_jnca/submission_checklist.md`: regenerated with author-statements evidence.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated with updated declarations.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated with updated declarations.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated with updated declarations.
- `paper/jnca_bilingual_latex/`: regenerated with updated declarations.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with updated declarations.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, and `docs/jnca_submission_generation.md`; delete `paper/submission_jnca/Author_Statements.docx`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add cover letter draft and upload manifest
### What was done
- Added a draft `Cover_Letter.docx` for Journal of Network and Computer Applications with placeholders for date, editor, corresponding author, originality confirmation, conflict statement, and optional reviewer/funding details.
- Added `submission_upload_manifest.md` as an upload-oriented file map that lists recommended upload files, optional support files, and final manual checks.
- Updated the submission checklist and generation documentation to include the cover letter and upload manifest.
- Regenerated the original Overleaf package, English/Chinese Word manuscripts, English PDF, bilingual LaTeX folder, English-only Overleaf zip, Chinese-only XeLaTeX zip, and bilingual archive zip.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; generated `Cover_Letter.docx`, `submission_upload_manifest.md`, and exported the English PDF successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Verified `paper/submission_jnca/Cover_Letter.docx` exists and contains Journal of Network and Computer Applications, originality/no-concurrent-submission wording, competing-interest wording, and placeholders.
- Verified `paper/submission_jnca/submission_upload_manifest.md` exists and lists the main manuscript, PDF, Highlights, Author Statements, Cover Letter, recommended English Overleaf zip, optional support files, and final manual checks.
- Verified `paper/submission_jnca/submission_checklist.md` and `docs/jnca_submission_generation.md` mention `Cover_Letter.docx` and `submission_upload_manifest.md`.
- Verified regenerated English and Chinese Word manuscripts still contain 12 tables and 4 embedded images.
- Verified `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.
- Verified regenerated English Overleaf zips contain `main.tex`, `latexmkrc`, `figures/fig1_hsta_architecture.png`, Highlights under 85 characters, and CRediT wording.

### Notes
- `scripts/generate_jnca_submission.py`: added cover-letter generation, upload-manifest generation, and checklist entries for both files.
- `docs/jnca_submission_generation.md`: documented the cover letter and upload manifest outputs.
- `paper/submission_jnca/Cover_Letter.docx`: added draft cover letter.
- `paper/submission_jnca/submission_upload_manifest.md`: added upload-oriented file map and final manual checks.
- `paper/submission_jnca/submission_checklist.md`: regenerated with cover-letter and upload-manifest entries.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated after the submission-material update.
- `paper/jnca_bilingual_latex/`: regenerated after the submission-material update.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the submission-material update.
- Rollback: revert `scripts/generate_jnca_submission.py` and `docs/jnca_submission_generation.md`; delete `paper/submission_jnca/Cover_Letter.docx` and `paper/submission_jnca/submission_upload_manifest.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add reproducible JNCA package validator
### What was done
- Added `scripts/validate_jnca_submission.py` to make the main manuscript package checks reproducible instead of relying on ad hoc manual inspection.
- The validator checks the English PDF header, English/Chinese Word table and image counts, Highlights length and legacy-file absence, author statements, cover letter, upload manifest, checklist/docs references, LaTeX environment balance, LaTeX figure paths, citation keys, key result values, and zip package contents.
- Updated the generation documentation and generated submission checklist to mention the validator as the post-generation check.
- Regenerated the Word/PDF/checklist outputs after adding the validator note.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py` after adding the checklist validator note; regenerated Word manuscripts, Highlights, author statements, cover letter, PDF, checklist, and upload manifest.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py` again; validation passed after regeneration.

### Notes
- `scripts/validate_jnca_submission.py`: added reproducible validation for the JNCA submission package.
- `scripts/generate_jnca_submission.py`: checklist generation now points to the validator as the post-regeneration check.
- `docs/jnca_submission_generation.md`: documented the validator command and coverage.
- `paper/submission_jnca/submission_checklist.md`: regenerated with validator guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, `paper/submission_jnca/Cover_Letter.docx`, and `paper/submission_jnca/submission_upload_manifest.md`: regenerated from the scripted workflow.
- Rollback: delete `scripts/validate_jnca_submission.py`, revert the validator references in `scripts/generate_jnca_submission.py` and `docs/jnca_submission_generation.md`, then rerun the previous generation scripts or restore the prior generated checklist/manuscript files.

## 2026-07-01 - Task: Harden JNCA Overleaf import format and upload bundle
### What was done
- Added `JNCA_recommended_upload_bundle.zip` as a one-file handoff package containing the English Word manuscript, PDF preview, Highlights, author statements, cover letter, manifest/checklist notes, and the recommended English Overleaf source zip.
- Strengthened validation around common Overleaf import failures: root-level zip layout, `main.tex` selection, English `elsarticle` class, pdfLaTeX compiler hint, nested English Overleaf zip content, citation/figure paths, brace balance, and obvious non-table LaTeX special-character issues.
- Updated the upload manifest, checklist, and generation documentation so the recommended upload path is explicit and the common "many Overleaf errors" cases point to wrong package, wrong main file, or wrong compiler.
- Regenerated fallback Overleaf, bilingual LaTeX, English-only Overleaf, Chinese-only XeLaTeX, Word/PDF submission files, and the final recommended upload bundle without changing result CSVs or training outputs.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; generated `JNCA_recommended_upload_bundle.zip` and exported the English PDF successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the stricter Overleaf import and upload-bundle checks.
- Verified `JNCA_recommended_upload_bundle.zip` contains `JNCA_HSTA_Encrypted_Traffic_EN.docx`, `JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `Highlights.docx`, `Author_Statements.docx`, `Cover_Letter.docx`, `submission_upload_manifest.md`, `submission_checklist.md`, and `jnca_english_overleaf_package.zip`.
- Checked local TeX commands and found no local `pdflatex`, `xelatex`, `latexmk`, or `bibtex`; final TeX compilation still needs Overleaf or a TeX installation.

### Notes
- `scripts/generate_jnca_submission.py`: added recommended upload-bundle generation and updated checklist/manifest wording for Overleaf import troubleshooting.
- `scripts/validate_jnca_submission.py`: added stricter LaTeX and zip checks for brace balance, obvious non-table special-character issues, root-level zip layout, compiler hints, English `elsarticle` main file, nested Overleaf zip content, and upload-bundle freshness.
- `docs/jnca_submission_generation.md`: updated regeneration order, recommended upload-bundle guidance, and Overleaf error troubleshooting notes.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: added the recommended one-file handoff package.
- `paper/submission_jnca/submission_upload_manifest.md`: regenerated with the recommended bundle and Overleaf troubleshooting guidance.
- `paper/submission_jnca/submission_checklist.md`: regenerated with the recommended bundle and stricter validation guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, and `paper/submission_jnca/Cover_Letter.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated as the fallback English Overleaf package.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated from the bilingual LaTeX workflow.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; delete `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add JNCA declaration-of-interest and format audit files
### What was done
- Added a separate `Declaration_of_Interest_Statement.docx` so the package is ready for submission systems that request a standalone competing-interest file.
- Added `submission_format_audit.md` to summarize Word/PDF structure, margins, headings, table and figure counts, separate submission files, figure/source package status, and remaining manual formatting checks.
- Updated the recommended upload bundle to include the declaration-of-interest file and format audit alongside the manuscript, PDF, Highlights, author statements, cover letter, checklist, manifest, and English Overleaf source zip.
- Extended the validator and generation documentation so the new files are generated, listed, packaged, and checked automatically.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; regenerated Word/PDF submission files, the declaration-of-interest file, format audit, and recommended upload bundle.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with declaration-of-interest and format-audit checks.
- Verified `Declaration_of_Interest_Statement.docx` contains the no-known-competing-financial-interests placeholder statement.
- Verified `submission_format_audit.md` records 12 tables and 4 embedded figures for both English and Chinese manuscripts, Word margins, headings, PDF header status, figure paths, and Overleaf compiler guidance.
- Verified `JNCA_recommended_upload_bundle.zip` contains `Declaration_of_Interest_Statement.docx` and `submission_format_audit.md`.

### Notes
- `scripts/generate_jnca_submission.py`: added declaration-of-interest document generation, format-audit generation, bundle inclusion, checklist wording, and upload-manifest entries.
- `scripts/validate_jnca_submission.py`: added validation for the declaration-of-interest file, format audit, docs/checklist/manifest references, and recommended upload-bundle entries.
- `docs/jnca_submission_generation.md`: documented the new files, validation coverage, and updated bundle contents.
- `paper/submission_jnca/Declaration_of_Interest_Statement.docx`: added standalone declaration-of-interest upload/support file.
- `paper/submission_jnca/submission_format_audit.md`: added generated format audit for Word/PDF/Overleaf readiness checks.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the new declaration-of-interest and format-audit files.
- `paper/submission_jnca/submission_upload_manifest.md`: regenerated with the declaration-of-interest and format-audit entries.
- `paper/submission_jnca/submission_checklist.md`: regenerated with new file coverage and validator scope.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated through Microsoft Word COM.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, and `paper/submission_jnca/Cover_Letter.docx`: regenerated from the scripted workflow.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated as the fallback English Overleaf package.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated from the bilingual LaTeX workflow.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; delete `paper/submission_jnca/Declaration_of_Interest_Statement.docx` and `paper/submission_jnca/submission_format_audit.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Prevent wide-table overflow in JNCA LaTeX packages
### What was done
- Updated the bilingual/recommended English LaTeX generator so generated tables with five or more columns are wrapped in `\resizebox{\linewidth}{!}{...}` unless they already use `tabularx`.
- Added validator coverage for wide LaTeX tables so future 5+ column tables cannot silently remain unscaled and overflow in Overleaf.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, recommended English Overleaf zip, Chinese XeLaTeX zip, Word/PDF submission files, and final recommended upload bundle.
- Documented the LaTeX table policy in `docs/jnca_submission_generation.md`.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py` before regeneration and confirmed the new validator detected the old unscaled 5-column tables in `paper/jnca_bilingual_latex/main.tex` and `JNCA_HSTA_Encrypted_Traffic_EN.tex`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new wide-table checks.
- Verified `paper/jnca_bilingual_latex/main.tex` now wraps the 5-column main-result, ablation, and confusion tables with `resizebox`, while the 3-column adapted-baseline table remains `tabularx`.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: changed LaTeX table generation so 5+ column tables are automatically scaled to `\linewidth`.
- `scripts/validate_jnca_submission.py`: added wide-table detection based on table column count and `resizebox`/`tabularx` coverage.
- `docs/jnca_submission_generation.md`: documented the generated LaTeX wide-table policy.
- `paper/jnca_bilingual_latex/`: regenerated with scaled 5-column English and Chinese tables.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with the wide-table fix.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated as the fallback English Overleaf package.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated so the nested English Overleaf source zip contains the wide-table fix.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add LaTeX cross-reference validation for key result tables and figures
### What was done
- Added cross-references in the generated English LaTeX Results and Analysis section for the main 40-class table, main 60-class table, ablation table/figure, efficiency table, and transfer table/figure.
- Added matching Chinese LaTeX cross-reference text for the corresponding main, ablation, efficiency, and transfer outputs.
- Extended the validator to check that LaTeX `\ref{...}` targets exist and that the full English manuscript references the key result tables and figures.
- Documented the cross-reference policy in `docs/jnca_submission_generation.md`.
- Regenerated the bilingual LaTeX package, recommended English Overleaf zip, Chinese XeLaTeX zip, Word/PDF submission files, and recommended upload bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py` before regeneration and confirmed the new validator detected the old missing key result references.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with cross-reference checks.
- Verified `paper/jnca_bilingual_latex/main.tex` contains references to `tab:main40-en`, `tab:main60-en`, `tab:ablation-en`, `fig:ablation-macro-f1-en`, `tab:efficiency-en`, `tab:transfer-en`, and `fig:transfer-macro-f1-en`.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: added generated English and Chinese Results-section cross-reference wording and protected `~\ref{...}` during LaTeX escaping.
- `scripts/validate_jnca_submission.py`: added label/ref extraction, missing-reference detection, and key result table/figure reference checks.
- `docs/jnca_submission_generation.md`: documented the generated LaTeX cross-reference policy.
- `paper/jnca_bilingual_latex/`: regenerated with key result table and figure references.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with cross-reference fixes.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated as the fallback English Overleaf package.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated so the nested English Overleaf source zip contains the cross-reference fixes.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Reference every non-appendix table and figure in the English LaTeX manuscript
### What was done
- Expanded generated English LaTeX cross-references so every non-appendix table and figure is mentioned in the manuscript text, including the method figure, dataset table, adapted-baseline table, main-result figure, scaling table, depth table, and confusion table in addition to the core result tables and figures.
- Added matching Chinese LaTeX cross-reference wording for the same non-appendix content.
- Tightened validation from checking a fixed key subset to checking that all non-appendix `tab:` and `fig:` labels in the full English manuscript are referenced.
- Regenerated the bilingual LaTeX package, recommended English Overleaf zip, Chinese XeLaTeX zip, Word/PDF submission files, and recommended upload bundle.
- Updated the generation documentation to state the non-appendix table/figure reference policy.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the all-non-appendix table/figure reference check.
- Verified every non-appendix label in `paper/jnca_bilingual_latex/main.tex` is referenced: `fig:hsta-en`, `tab:dataset-en`, `tab:adapted-baselines-en`, `tab:main40-en`, `fig:main-macro-f1-en`, `tab:main60-en`, `tab:scaling-en`, `tab:ablation-en`, `fig:ablation-macro-f1-en`, `tab:efficiency-en`, `tab:depth-en`, `tab:transfer-en`, `fig:transfer-macro-f1-en`, and `tab:confusion-en`.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: expanded English and Chinese generated cross-reference wording and protected additional `~\ref{...}` references during LaTeX escaping.
- `scripts/validate_jnca_submission.py`: changed the English LaTeX reference check to require all non-appendix table and figure labels to be referenced.
- `docs/jnca_submission_generation.md`: updated the LaTeX cross-reference policy.
- `paper/jnca_bilingual_latex/`: regenerated with all non-appendix table and figure references.
- `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated with the expanded cross-reference coverage.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated as the fallback English Overleaf package.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated so the nested English Overleaf source zip contains the expanded cross-reference coverage.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Prevent Overleaf import-package confusion in the JNCA submission bundle
### What was done
- Added a clearly named direct Overleaf import zip in the submission folder so the English SCI/JNCA LaTeX source can be uploaded without opening the mixed handoff bundle.
- Added an Overleaf import guide beside the generated submission files to distinguish the direct LaTeX source zip from the Word/PDF/support-file handoff bundle.
- Updated checklist, upload manifest, format audit, and generation documentation so the recommended upload path points to `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`.
- Tightened validation so the direct Overleaf zip must match the canonical English package, contain root-level `main.tex`, exclude Chinese TeX files, and remain distinct from the handoff bundle.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, English/Chinese source zips, Word/PDF submission files, direct Overleaf zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new direct-Overleaf-package and handoff-bundle checks.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; root entries include `main.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, and generated figures.
- Inspected `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`; root entries are Word/PDF/support files plus `OVERLEAF_IMPORT_GUIDE.md` and the nested `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, with no root-level `main.tex`.

### Notes
- `scripts/generate_jnca_submission.py`: added `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `OVERLEAF_IMPORT_GUIDE.md`, and updated checklist/manifest/audit generation to warn against importing the handoff bundle into Overleaf.
- `scripts/generate_jnca_bilingual_latex.py`: updated the English Overleaf README text to mention the clearly named submission-folder copy.
- `scripts/validate_jnca_submission.py`: added validation for the direct Overleaf zip, guide file, canonical zip equivalence, and handoff-bundle shape.
- `docs/jnca_submission_generation.md`: documented the direct Overleaf import zip and the reason not to import the mixed handoff bundle.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`: generated quick diagnosis for common Overleaf import errors.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`: generated direct English Overleaf import package.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_upload_manifest.md`, and `paper/submission_jnca/submission_format_audit.md`: regenerated with the direct Overleaf import guidance.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the new guide and nested direct Overleaf source zip.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated as source packages.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Align English LaTeX author metadata with Elsevier e-mail conventions
### What was done
- Updated the English Elsevier LaTeX generators so the corresponding-author email is emitted with `\ead{email@example.com}` instead of being embedded only in the `\cortext` note.
- Kept the corresponding-author note as a placeholder-only `\cortext[cor1]{...}` entry so final author metadata can still be filled before submission.
- Added validator checks requiring the English `elsarticle` manuscripts to contain both the `\ead` email placeholder and the corresponding-author note.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, English/Chinese source zips, Word/PDF submission files, direct Overleaf zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new Elsevier author-metadata checks.
- Inspected `paper/jnca_bilingual_latex/main.tex`, `paper/submission_jnca/overleaf_jnca/main.tex`, and the nested `main.tex` inside `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; all contain `\ead{email@example.com}` and the corresponding-author note.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: changed the generated English `elsarticle` front matter to use `\ead` for the email placeholder.
- `scripts/generate_jnca_overleaf.py`: changed the fallback English Overleaf front matter to use the same `\ead` convention.
- `scripts/validate_jnca_submission.py`: added checks for the Elsevier email placeholder and corresponding-author note in English `elsarticle` manuscripts.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the metadata format change.
- `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the updated front matter.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_overleaf.py`, and `scripts/validate_jnca_submission.py`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add in-text citation markers to Word/PDF manuscripts
### What was done
- Added generated numerical in-text citation markers to the English and Chinese Word manuscripts for protocol standards, encrypted-traffic surveys, datasets, related sequence models, the adapted NetMamba baseline, LoRA adaptation, and long-term drift/generalization limitations.
- Kept the reference list unchanged and mapped the new Word markers to the existing numbered references.
- Extended validation so both generated Word manuscripts must contain the expected in-text citation markers in addition to table and image counts.
- Updated the submission checklist, format audit, and generation documentation to state that Word/PDF manuscripts now include in-text citation markers.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, English/Chinese source zips, Word/PDF submission files, direct Overleaf zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new Word in-text citation checks.
- Inspected `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`; the expected markers `[1,2]`, `[4,5,8]`, `[3,6,7]`, `[16,20,24,25]`, `[14]`, `[26]`, and `[28]` appear in body paragraphs rather than only in the reference list.

### Notes
- `scripts/generate_jnca_submission.py`: added citation-marker injection for selected Word manuscript paragraphs and updated generated checklist/audit text.
- `scripts/validate_jnca_submission.py`: added Word in-text citation marker checks for both English and Chinese manuscripts.
- `docs/jnca_submission_generation.md`: documented that validation covers Word in-text citation markers.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated with in-text citation markers.
- `paper/submission_jnca/submission_checklist.md` and `paper/submission_jnca/submission_format_audit.md`: regenerated with the new Word/PDF citation status.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the updated Word/PDF manuscripts and documentation.
- `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated for package consistency.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Align Overleaf BibTeX coverage with the Word manuscript references
### What was done
- Expanded the English Overleaf BibTeX file from 15 to 28 entries so it covers the same reference set used by the generated Word manuscript.
- Added LaTeX in-text citation coverage for additional encrypted-traffic surveys, QUIC/dataset/pretraining work, deep/pretrained traffic models, state-space/SSM context, and the adapted NetMamba baseline context.
- Updated the Chinese companion LaTeX bibliography list and citation coverage to stay aligned with the English Overleaf package.
- Extended validation so the English BibTeX must include the expanded survey/dataset/model reference keys and the English LaTeX manuscripts must cite the key expanded references.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, English/Chinese source zips, Word/PDF submission files, direct Overleaf zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with expanded BibTeX and citation-key checks.
- Inspected `paper/jnca_bilingual_latex/references.bib` and `paper/submission_jnca/overleaf_jnca/references.bib`; both contain 28 BibTeX entries.
- Inspected `paper/jnca_bilingual_latex/main.tex` and `paper/submission_jnca/overleaf_jnca/main.tex`; both cite the expanded survey/dataset/model keys required by the validator.

### Notes
- `scripts/generate_jnca_overleaf.py`: added BibTeX entries and expanded citation coverage in the fallback English Overleaf manuscript.
- `scripts/generate_jnca_bilingual_latex.py`: expanded `REF_ITEMS` and updated English/Chinese LaTeX citation coverage.
- `scripts/validate_jnca_submission.py`: added expanded BibTeX and in-text citation coverage checks.
- `docs/jnca_submission_generation.md`: documented the citation coverage policy and expanded BibTeX validation.
- `paper/jnca_bilingual_latex/references.bib`, `paper/submission_jnca/overleaf_jnca/references.bib`, `paper/jnca_bilingual_latex/main.tex`, and related LaTeX package outputs: regenerated with expanded references and citations.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/jnca_english_overleaf_package.zip`, `paper/jnca_chinese_xelatex_package.zip`, and `paper/jnca_bilingual_latex_package.zip`: regenerated with aligned reference coverage.
- Rollback: revert `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Harden JNCA LaTeX upload packages for Overleaf and Editorial Manager
### What was done
- Added a separate flat LaTeX source package for Elsevier/Editorial Manager-style upload systems so figures and source files sit at the zip root instead of relying on a `figures/` subfolder.
- Synchronized `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip` with the full English Overleaf source so the folder, canonical zip, and direct upload zip no longer diverge.
- Updated the submission checklist, upload manifest, format audit, Overleaf guide, and generation documentation to distinguish the Overleaf preview/editing zip from the flat source zip.
- Extended validation to check the flat source package, root-level figure references, synchronized Overleaf folder content, package compiler hints, and handoff-bundle contents.
- Regenerated LaTeX packages, Word/PDF manuscripts, source zips, and the recommended handoff bundle from the scripted workflow.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new flat-source and synchronized-Overleaf checks.
- Inspected `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; entries are root-level `main.tex`, `references.bib`, `elsarticle-num.bst`, `latexmkrc`, README, and four PNG figures.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; entries include root-level `main.tex` and generated figures under `figures/`.
- Confirmed `paper/submission_jnca/editorial_manager_latex_source/main.tex` references PNG figures without `figures/` prefixes.
- Confirmed `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` starts with `%PDF-`.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: added synchronized submission Overleaf-folder output and the flat Editorial Manager LaTeX source package.
- `scripts/generate_jnca_submission.py`: added the flat source zip to the handoff bundle and updated generated checklist, manifest, audit, and import-guide text.
- `scripts/validate_jnca_submission.py`: added validation for the flat source zip, root-level figure references, package contents, compiler hints, and normalized Overleaf-folder/package comparison.
- `docs/jnca_submission_generation.md`: documented when to use the Overleaf source zip versus the flat Editorial Manager source zip.
- `paper/submission_jnca/editorial_manager_latex_source/`: generated flat LaTeX source folder for submission-system source upload.
- `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`: generated flat LaTeX source zip.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated to match the full English Overleaf source.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_upload_manifest.md`, and `paper/submission_jnca/submission_format_audit.md`: regenerated with the corrected upload guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated from the scripted workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/jnca_english_overleaf_package.zip`, `paper/jnca_chinese_xelatex_package.zip`, and `paper/jnca_bilingual_latex_package.zip`: regenerated with the updated source-package structure.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Add separate figure-upload materials and fix manuscript figure numbering
### What was done
- Corrected generated Word/PDF figure numbering so the English manuscript uses continuous Figure 1-4 captions instead of skipping from Figure 3 to Figure 5.
- Renamed the generated cross-protocol transfer figure from `fig5_transfer_macro_f1.png` to `fig4_transfer_macro_f1.png` across Word, LaTeX, Overleaf, flat source, and validation outputs.
- Added a separate `Figure_Captions.docx` file containing captions for Figure 1-4 and the graphical abstract.
- Added an optional `Graphical_Abstract.png` candidate summarizing the HSTA-Hybrid workflow and main Macro-F1 results.
- Added `FIGURES_FOR_UPLOAD.zip` with separate figure PNGs, graphical abstract, and figure captions for submission systems that request independent artwork files.
- Extended validation to check continuous Word Figure 1-4 captions, absence of legacy `fig5` output, PNG header validity, figure-caption contents, and figure-upload zip contents.
- Regenerated the fallback Overleaf package, bilingual LaTeX package, English/Chinese source zips, Word/PDF submission files, direct Overleaf zip, flat source zip, figure-upload zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with the new figure-numbering and figure-upload checks.
- Inspected `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`; figure captions are Figure 1, Figure 2, Figure 3, and Figure 4.
- Inspected `paper/submission_jnca/Figure_Captions.docx`; it contains Figure 1-4 captions and a graphical abstract caption.
- Inspected `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`; it contains Figure 1-4 PNGs, `Graphical_Abstract.png`, and `Figure_Captions.docx`.
- Confirmed `paper/submission_jnca/Graphical_Abstract.png` starts with a PNG header and no `fig5` file remains under the generated submission figure folders.

### Notes
- `scripts/generate_jnca_submission.py`: renamed the transfer result figure to Figure 4, generated graphical abstract and figure-caption files, built the separate figure-upload zip, added those files to the handoff bundle, and removed legacy `fig5` output during regeneration.
- `scripts/generate_jnca_overleaf.py`: renamed the cross-protocol transfer figure reference to `fig4_transfer_macro_f1.png`.
- `scripts/generate_jnca_bilingual_latex.py`: renamed English/Chinese LaTeX figure references and flat-source package entries to `fig4_transfer_macro_f1.png`.
- `scripts/validate_jnca_submission.py`: added checks for continuous Word Figure 1-4 captions, figure-caption file contents, graphical abstract PNG header, figure-upload zip contents, and legacy `fig5` absence.
- `docs/jnca_submission_generation.md`: documented the separate figure-upload materials, graphical abstract candidate, and continuous Figure 1-4 validation.
- `paper/submission_jnca/Figure_Captions.docx`: generated separate caption file.
- `paper/submission_jnca/Graphical_Abstract.png`: generated optional graphical abstract candidate.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`: generated separate figure upload bundle.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated with continuous figure numbering.
- `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/jnca_english_overleaf_package.zip`, `paper/jnca_chinese_xelatex_package.zip`, and `paper/jnca_bilingual_latex_package.zip`: regenerated with Figure 4 naming and updated upload materials.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated manuscript folders/zips.

## 2026-07-01 - Task: Validate English Word result tables against generated CSV-derived tables
### What was done
- Added validation that compares the English Word manuscript result tables against the current generated tables derived from repository CSV summaries.
- Covered the key result-bearing Word tables: main 40-class results, main 60-class results, 40-to-60 scaling, attention-position ablation, efficiency, depth sensitivity, and cross-protocol transfer.
- Kept the validation source of truth in the existing submission generator functions so the check uses the same CSV aggregation logic as the manuscript generation path.
- Updated the generated submission checklist and generation documentation to state that validation now checks English Word result-table contents, not just table counts.
- Regenerated the Word/PDF submission files and handoff bundle after the checklist wording update.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with Table 3-9 content checks.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed after regeneration.
- Inspected `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`; Tables 3-9 include the expected generated rows, including HSTA-Hybrid main results and transfer rows.
- Inspected `paper/submission_jnca/submission_checklist.md` and `docs/jnca_submission_generation.md`; both document English Word result-table validation against generated CSV-derived tables.

### Notes
- `scripts/validate_jnca_submission.py`: added generator-module loading, Word table extraction, and Table 3-9 content comparison against the generated CSV-derived result tables.
- `scripts/generate_jnca_submission.py`: updated generated checklist text to mention English Word result-table content validation.
- `docs/jnca_submission_generation.md`: documented the new English Word result-table validation coverage.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated after checklist updates.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, and related submission support files: regenerated by the submission workflow.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation script or restore the prior generated submission files.

## 2026-07-01 - Task: Strengthen submission format checks for Word and Overleaf import
### What was done
- Updated the English Word manuscript generator to produce a review-friendly format with 12 pt Times New Roman Normal style, double-spaced body paragraphs, continuous line numbering, and footer page-number fields.
- Extended validation to inspect the English Word style settings and underlying Word XML for line numbering and page-number fields, instead of only checking table/image counts.
- Corrected stale Figure 5 wording in generated Overleaf figure notes and added validation that the notes use current Figure 1-4 numbering.
- Updated the generated checklist, format audit, and project documentation so the format standard and validation scope are explicit.
- Regenerated the Word/PDF submission files, Overleaf source zips, flat Editorial Manager source zip, figure upload bundle, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new Word review-format and Figure 1-4 note checks.
- Confirmed `paper/submission_jnca/submission_format_audit.md` records `12 pt Normal style`, `double spacing`, `continuous line numbering`, and `page-number field`.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; it contains root-level `main.tex`, bibliography/style files, README, `latexmkrc`, and figures under `figures/`.
- Inspected `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; it contains root-level `main.tex`, bibliography/style files, README, `latexmkrc`, and four root-level PNG figures, with no `figures/` prefixes in `main.tex`.

### Notes
- `scripts/generate_jnca_submission.py`: added English Word review formatting, page-number fields, continuous line numbering, and audit/checklist wording.
- `scripts/validate_jnca_submission.py`: added Word review-format validation and stale Figure 5 note validation.
- `scripts/generate_jnca_overleaf.py`: corrected generated figure-note wording from Figure 5 to Figure 4.
- `scripts/generate_jnca_bilingual_latex.py`: synchronized the submission Overleaf figure notes with current Figure 1-4 numbering.
- `docs/jnca_submission_generation.md`: documented the English Word review-format standard and expanded validation scope.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated with the stricter Word review format.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, and `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`: regenerated with updated format/import guidance.
- `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/jnca_english_overleaf_package.zip`, `paper/jnca_chinese_xelatex_package.zip`, and `paper/jnca_bilingual_latex_package.zip`: regenerated after format and import-note updates.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated submission files and zips.

## 2026-07-01 - Task: Add JNCA guide-for-authors compliance audit and TIFF graphical abstract
### What was done
- Added `Graphical_Abstract.tif` alongside the existing PNG graphical abstract so the submission package includes an Elsevier-preferred artwork candidate.
- Added `JNCA_GFA_COMPLIANCE_CHECK.md` to map the generated package to common JNCA/Elsevier author-guide checks: editable source files, direct Overleaf source, flat Editorial Manager source, abstract word count, keyword count, Highlights limits, graphical abstract size, and remaining manual checks.
- Extended validation to check English abstract word count, keyword count, PNG/TIFF graphical abstract headers and minimum dimensions, compliance-audit contents, and inclusion of the new files in figure/upload bundles.
- Updated checklist, format audit, upload manifest, and project documentation to mention the TIFF graphical abstract and Guide-for-Authors compliance audit.
- Regenerated the Word/PDF submission files, figure upload bundle, direct Overleaf zip, flat Editorial Manager source zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with abstract word count 209, keyword count 7, graphical abstract PNG/TIFF size 3570 x 1320 px, and new compliance-audit checks.
- Inspected `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`; it contains `Graphical_Abstract.tif` and `JNCA_GFA_COMPLIANCE_CHECK.md`.
- Inspected `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`; it records source package guidance, abstract/keyword/Highlights checks, graphical abstract dimensions, and remaining manual upload checks.

### Notes
- `scripts/generate_jnca_submission.py`: added TIFF graphical abstract output, Guide-for-Authors compliance-audit generation, and inclusion of the new files in upload bundles and generated guidance.
- `scripts/validate_jnca_submission.py`: added abstract/keyword validation, PNG/TIFF graphical abstract header and dimension checks, compliance-audit checks, and bundle-content checks for the new files.
- `docs/jnca_submission_generation.md`: documented `Graphical_Abstract.tif`, `JNCA_GFA_COMPLIANCE_CHECK.md`, and expanded validation coverage.
- `paper/submission_jnca/Graphical_Abstract.tif`: generated TIFF graphical abstract candidate.
- `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`: generated Guide-for-Authors compliance audit.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by the submission workflow.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, and related support files: regenerated with the new compliance and graphical abstract materials.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated submission files and zips.

## 2026-07-01 - Task: Strengthen PDF export validity checks
### What was done
- Extended PDF validation beyond the `%PDF-` header to check EOF marker, page-object count, content stream count, font resource markers, image object markers, decodable compressed streams, and PDF/Word timestamp sync.
- Avoided brittle raw title-text checks because Microsoft Word COM can split and compress PDF text streams in ways that make direct keyword search unreliable.
- Updated generated checklist, format audit, and project documentation so the PDF validation scope reflects the stronger structural checks.
- Regenerated the Word/PDF submission files and recommended handoff bundle after updating the generated guidance text.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with PDF evidence: 23 page objects, 88 content streams, 31 font resource markers, 4 image object markers, 43 decodable streams, and 9,768,609 decoded bytes.

### Notes
- `scripts/validate_jnca_submission.py`: added structural PDF checks and removed brittle raw title-marker checks.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to describe the stronger PDF validation.
- `docs/jnca_submission_generation.md`: documented the expanded PDF validation scope.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by the submission workflow.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with updated PDF validation guidance.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation script or restore the prior generated submission files.

## 2026-07-01 - Task: Strengthen Overleaf and Editorial Manager import-format checks
### What was done
- Added a generated import-format checklist that separates the direct Overleaf source zip, the flat Editorial Manager LaTeX source zip, the mixed handoff bundle, and the separate artwork zip.
- Updated generated guidance so the likely cause of many immediate import errors is explicit: wrong zip selected, wrong compiler selected, or figure subfolders used in a system that expects flat LaTeX support files.
- Extended validation to check source-zip import hygiene: English source zips exclude Word/PDF/nested-zip/artwork-only files, Overleaf graphics paths match `figures/...`, and the Editorial Manager source zip is flat with root-level figures.
- Regenerated the Word/PDF submission files, checklists, import guides, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully and generated `SUBMISSION_IMPORT_FORMAT_CHECK.md`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new import-format audit and source-zip hygiene checks.
- Inspected `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md` and `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`; both state the correct Overleaf package, Editorial Manager package, compiler choice, and wrong-package error triage.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`; the Overleaf zip has root `main.tex` plus `figures/`, the Editorial Manager zip is flat, and the handoff bundle contains support documents plus nested source zips.

### Notes
- `scripts/generate_jnca_submission.py`: added `SUBMISSION_IMPORT_FORMAT_CHECK.md`, included it in generated guidance and upload bundles, and strengthened wrong-zip import explanations.
- `scripts/validate_jnca_submission.py`: added import-format checklist validation and source-zip hygiene checks for Overleaf and Editorial Manager packages.
- `docs/jnca_submission_generation.md`: documented the import-format policy, direct Overleaf package, flat Editorial Manager package, mixed handoff bundle, and expanded validation scope.
- `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`: generated final import-format checklist.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_upload_manifest.md`, and `paper/submission_jnca/submission_format_audit.md`: regenerated with stricter import guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the import-format checklist and stricter package guidance.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation script or restore the prior generated submission files and zips.

## 2026-07-01 - Task: Tighten Elsevier keyword-count compliance
### What was done
- Reduced the generated English manuscript keywords from 7 items to 6 items by removing the broad `attention mechanism` keyword while keeping the core topic, protocol, model-family, and transfer keywords.
- Applied the same keyword count to the generated Chinese companion manuscript, English Overleaf source, bilingual LaTeX source, and regenerated submission support files.
- Tightened validation so English Word and English LaTeX keyword sections must contain 1-6 keywords instead of allowing 7.
- Updated the generated compliance audit and documentation to state the 1-6 keyword target.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed with English Word keyword count 6 and English LaTeX keyword count 6 for the generated Overleaf and bilingual sources.
- Inspected `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`; it records `Keywords: 6 item(s); target: 1-6 keywords.`
- Inspected `paper/submission_jnca/overleaf_jnca/main.tex`, `paper/jnca_bilingual_latex/main.tex`, and `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`; each keyword block contains six keyword items.

### Notes
- `scripts/generate_jnca_submission.py`: reduced Chinese and English keyword lists to six items and updated generated checklist/compliance-audit wording.
- `scripts/generate_jnca_overleaf.py`: reduced the fallback English Overleaf keyword list to six items.
- `scripts/validate_jnca_submission.py`: tightened Word keyword validation to 1-6 items and added LaTeX keyword-block count validation.
- `docs/jnca_submission_generation.md`: documented that generated English Word and LaTeX manuscripts cap keywords at six items.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated with the six-keyword manuscript text.
- `paper/submission_jnca/overleaf_jnca/`, `paper/jnca_bilingual_latex/`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/jnca_english_overleaf_package.zip`, `paper/jnca_bilingual_latex_package.zip`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with synchronized six-keyword LaTeX sources and updated support files.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation scripts or restore the prior generated submission files and zips.

## 2026-07-01 - Task: Control Word document metadata for submission files
### What was done
- Added controlled Word core document properties for the generated English manuscript, Chinese companion manuscript, Highlights, author statements, declaration of interest, cover letter, and figure captions.
- Replaced default generator metadata such as `python-docx` author/comments with controlled placeholder metadata, manuscript title, submission-support category, and six-keyword metadata.
- Extended validation to check Word title, author, last-modified-by, keywords, category, and absence of default generator metadata across main and support docx files.
- Updated generated checklist, format audit, and project documentation to state that Word core properties are now controlled.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including controlled Word core-property checks and absence of `python-docx` metadata.
- Inspected core properties for `JNCA_HSTA_Encrypted_Traffic_EN.docx`, `JNCA_HSTA_Encrypted_Traffic_CN.docx`, `Highlights.docx`, `Figure_Captions.docx`, and `Cover_Letter.docx`; each file has controlled title, placeholder author metadata, six-keyword metadata, category, and comments.

### Notes
- `scripts/generate_jnca_submission.py`: added core-property constants and helper, applied controlled metadata to generated manuscript and support Word files, and updated generated guidance text.
- `scripts/validate_jnca_submission.py`: added Word core-property validation for main manuscripts and separate support docx files.
- `docs/jnca_submission_generation.md`: documented controlled Word core document properties and validation coverage.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, `paper/submission_jnca/Declaration_of_Interest_Statement.docx`, `paper/submission_jnca/Cover_Letter.docx`, and `paper/submission_jnca/Figure_Captions.docx`: regenerated with controlled Word properties.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated after Word metadata updates.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation script or restore the prior generated submission files and zips.

## 2026-07-01 - Task: Harden submission import-format validation and PDF metadata checks
### What was done
- Added stricter generated-package validation for Overleaf, Editorial Manager, figure-upload, handoff, and nested source zips so unsafe or nonportable entries are caught before upload.
- Added PDF raw-marker validation for obvious author/tool metadata leakage in the generated English PDF.
- Updated generated import guides, checklist, format audit, and repository documentation so the likely causes of many import errors are explicit: wrong zip, wrong compiler, hidden/system archive entries, absolute paths, path traversal, backslash paths, or re-zipped packages with an extra folder.
- Regenerated the Overleaf package, bilingual LaTeX package, English Word/PDF manuscript, submission support files, and recommended upload bundles after the validation and guidance changes.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; rebuilt `paper/submission_jnca/overleaf_jnca_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; rebuilt `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully and refreshed the submission package.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new PDF raw-marker check and clean zip-entry-path checks for source, figure, handoff, and nested zips.
- Inspected key zips: `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` has root `main.tex` plus `figures/`, `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip` is flat, `JNCA_recommended_upload_bundle.zip` is a handoff bundle, and `FIGURES_FOR_UPLOAD.zip` contains only the expected figure/caption files.
- Raw-scanned `JNCA_HSTA_Encrypted_Traffic_EN.pdf`; `/Author`, `/Subject`, `/Keywords`, `python-docx`, and `Author metadata placeholder` were not found, the header is `%PDF-`, EOF is present, and file size is 636626 bytes.

### Notes
- `scripts/validate_jnca_submission.py`: added reusable zip-entry hygiene checks and PDF raw metadata/tool marker checks.
- `scripts/generate_jnca_submission.py`: updated generated Overleaf/import guides, checklist, format audit, and upload manifest wording for zip-entry hygiene and PDF metadata checks.
- `docs/jnca_submission_generation.md`: documented raw PDF metadata-marker checks, zip-entry hygiene, and the risk of re-zipping packages through external tools.
- `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`: regenerated with explicit zip-entry hygiene requirements for direct Overleaf and flat Editorial Manager packages.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`: regenerated with clean ASCII relative-path guidance for source zips.
- `paper/submission_jnca/submission_checklist.md`: regenerated with PDF raw-marker and zip-entry hygiene validation scope.
- `paper/submission_jnca/submission_format_audit.md`: regenerated with PDF raw-marker and source-package hygiene audit text.
- `paper/submission_jnca/submission_upload_manifest.md`: regenerated with the warning to keep generated zips intact and avoid re-zipping through tools that add hidden files or folders.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by Microsoft Word COM export and validated for header, EOF, structure, timestamp, and raw metadata markers.
- `paper/submission_jnca/Highlights.docx`: regenerated as a controlled-metadata support file.
- `paper/submission_jnca/Author_Statements.docx`: regenerated as a controlled-metadata support file.
- `paper/submission_jnca/Declaration_of_Interest_Statement.docx`: regenerated as a controlled-metadata support file.
- `paper/submission_jnca/Cover_Letter.docx`: regenerated as a controlled-metadata support file.
- `paper/submission_jnca/Figure_Captions.docx`: regenerated as a controlled-metadata support file.
- `paper/submission_jnca/Graphical_Abstract.png` and `paper/submission_jnca/Graphical_Abstract.tif`: regenerated as graphical-abstract candidates.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`: regenerated and validated for expected figure entries and clean zip paths.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`: regenerated as the direct English Overleaf source package and validated for clean root layout and `figures/` paths.
- `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`: regenerated as the flat Editorial Manager source package and validated for root-level figures.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated as the mixed handoff bundle and validated as not being a direct Overleaf project.
- `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated from the English Overleaf source workflow.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated from the bilingual LaTeX workflow.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation sequence or restore the prior generated submission files and zips from backup/version control.

## 2026-07-01 - Task: Align English LaTeX Highlights with Elsevier frontmatter format
### What was done
- Moved English LaTeX Highlights from a body `\section*{Highlights}` block into the official Elsevier `highlights` environment inside the frontmatter.
- Applied the same structure to the fallback English Overleaf generator and the main bilingual/English LaTeX generator so all English source packages stay synchronized.
- Extended validation so English `elsarticle` sources must contain exactly four frontmatter highlight items, each no longer than 85 characters, and must not place Highlights as a body section.
- Updated generated checklist/audit text and repository documentation to record the new LaTeX Highlights policy.
- Regenerated the Overleaf source packages, bilingual LaTeX package, English Word/PDF manuscript, submission support files, and upload bundles.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; regenerated the fallback English Overleaf package.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; regenerated the bilingual LaTeX folder and English/Chinese specialized zips.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully and refreshed the submission package.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new checks that English LaTeX uses the Elsevier `highlights` environment and does not place Highlights as a body section.
- Inspected `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` and `JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; both `main.tex` files contain a `highlights` environment with four items and no body `\section*{Highlights}`.
- Inspected `paper/submission_jnca/overleaf_jnca/main.tex`, `paper/jnca_bilingual_latex/main.tex`, and `paper/jnca_bilingual_latex/JNCA_HSTA_Encrypted_Traffic_EN.tex`; each places Highlights before the keyword block in the frontmatter.

### Notes
- `scripts/generate_jnca_overleaf.py`: moved fallback English Overleaf Highlights into the Elsevier `highlights` environment.
- `scripts/generate_jnca_bilingual_latex.py`: moved main English LaTeX Highlights into the Elsevier `highlights` environment while leaving the Chinese companion layout unchanged.
- `scripts/validate_jnca_submission.py`: added English `elsarticle` checks for frontmatter Highlights count, length, and absence of a body Highlights section.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to document the frontmatter Highlights structure.
- `docs/jnca_submission_generation.md`: added the LaTeX Highlights policy and validation expectation.
- `paper/submission_jnca/submission_checklist.md` and `paper/submission_jnca/submission_format_audit.md`: regenerated with the new Highlights policy wording.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, and `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by the submission workflow.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, `paper/submission_jnca/Declaration_of_Interest_Statement.docx`, `paper/submission_jnca/Cover_Letter.docx`, and `paper/submission_jnca/Figure_Captions.docx`: regenerated as support documents.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`: regenerated as the direct Overleaf package with frontmatter Highlights.
- `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`: regenerated as the flat source package with frontmatter Highlights.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, and `paper/submission_jnca/overleaf_jnca_package.zip`: regenerated after the source-format update.
- `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated by the LaTeX workflow.
- Rollback: revert `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation sequence or restore the prior generated LaTeX, Word/PDF, and zip outputs.

## 2026-07-01 - Task: Add Word and LaTeX manuscript alignment checks
### What was done
- Added cross-output validation between the English Word manuscript and the English Overleaf `main.tex` to prevent silent content drift during future edits.
- The validator now compares the title, keywords, Highlights, core abstract result markers, and main section titles between `JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/overleaf_jnca/main.tex`.
- Updated generated checklist, format audit, and repository documentation to record the Word/LaTeX alignment policy.
- Regenerated the English/Chinese Word manuscripts, English PDF, support documents, checklist, format audit, upload manifest, figure bundle, and recommended handoff bundle after updating the generated guidance.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\validate_jnca_submission.py scripts\generate_jnca_submission.py scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py` before regeneration; the new Word/LaTeX alignment checks passed, and the only failures were stale generated checklist/audit text.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Microsoft Word COM exported `JNCA_HSTA_Encrypted_Traffic_EN.pdf` successfully and refreshed submission support files.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including Word/LaTeX title, keyword, Highlights, abstract marker, and main-section alignment checks.
- Independently inspected `JNCA_HSTA_Encrypted_Traffic_EN.docx` and `paper/submission_jnca/overleaf_jnca/main.tex`; title equality is `True`, Highlights equality is `True`, and both files contain four Highlights.

### Notes
- `scripts/validate_jnca_submission.py`: added normalization helpers and `check_word_latex_alignment` for cross-checking Word and LaTeX outputs.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to include Word/LaTeX consistency checks.
- `docs/jnca_submission_generation.md`: added the Word/LaTeX alignment policy and expanded validation-scope documentation.
- `paper/submission_jnca/submission_checklist.md`: regenerated with Word/LaTeX alignment validation scope.
- `paper/submission_jnca/submission_format_audit.md`: regenerated with Word/LaTeX consistency audit text.
- `paper/submission_jnca/submission_upload_manifest.md`: regenerated by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated by the submission workflow and used as the Word side of the alignment check.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated by Microsoft Word COM export.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, `paper/submission_jnca/Declaration_of_Interest_Statement.docx`, `paper/submission_jnca/Cover_Letter.docx`, and `paper/submission_jnca/Figure_Captions.docx`: regenerated as support documents.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`: regenerated by the submission workflow.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated with the refreshed checklist/audit files.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation sequence or restore the prior generated Word/PDF, support documents, and upload bundle.

## 2026-07-01 - Task: Refresh and validate JNCA import-format package
### What was done
- Regenerated the English Overleaf source, bilingual LaTeX package, Word/PDF manuscripts, support documents, figure bundle, direct Overleaf zip, flat Editorial Manager source zip, and recommended handoff bundle.
- Confirmed the likely source of many import errors: the mixed handoff bundle is not a direct LaTeX project; direct Overleaf import should use the English source zip with `main.tex`, pdfLaTeX, and BibTeX.
- Rechecked the generated import guides and audits so the package clearly separates Overleaf, Editorial Manager, handoff, figure-upload, and Chinese XeLaTeX use cases.
- Verified the refreshed package against the strengthened validation suite, including Word review format, PDF structure, LaTeX structure, BibTeX integrity, Word/LaTeX alignment, zip-entry hygiene, and package contents.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; refreshed `paper/submission_jnca/overleaf_jnca/` and `paper/submission_jnca/overleaf_jnca_package.zip`.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; refreshed the bilingual, English Overleaf, and Chinese XeLaTeX source packages.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word COM exported the English PDF successfully and refreshed the submission folder.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed.
- Inspected the generated import guides and audits for `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `JNCA_recommended_upload_bundle.zip`, pdfLaTeX/BibTeX guidance, BibTeX integrity text, and clean ASCII relative-path zip hygiene.

### Notes
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`: regenerated as the English Word manuscript with review-format checks.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`: regenerated and validated for PDF header, EOF marker, page/content/font/image evidence, decodable streams, metadata markers, and timestamp sync.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`: regenerated as the Chinese companion Word manuscript.
- `paper/submission_jnca/Highlights.docx`, `paper/submission_jnca/Author_Statements.docx`, `paper/submission_jnca/Declaration_of_Interest_Statement.docx`, `paper/submission_jnca/Cover_Letter.docx`, and `paper/submission_jnca/Figure_Captions.docx`: regenerated as submission support documents.
- `paper/submission_jnca/Graphical_Abstract.png`, `paper/submission_jnca/Graphical_Abstract.tif`, and `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`: regenerated as graphical abstract and separate figure-upload materials.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`: regenerated as the direct English Overleaf package.
- `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`: regenerated as the flat source package for systems that reject figure subfolders.
- `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated as a mixed handoff bundle and confirmed not suitable for direct Overleaf import.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, and `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: regenerated or checked for import-format guidance and remaining manual actions.
- `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated from the LaTeX workflows.
- Rollback: restore the previous generated submission artifacts and LaTeX packages from backup/version control, or revert the generation outputs and rerun the prior known-good generation sequence.

## 2026-07-01 - Task: Strengthen English LaTeX package-order checks
### What was done
- Updated English `elsarticle` generation so `lineno` is loaded before `hyperref`, reducing line-numbering and hyperlink-order risk in Overleaf/Elsevier-style compilation.
- Added validator coverage for English LaTeX package order so future generated `main.tex` files fail validation if `hyperref` is placed before `lineno` or either package is missing.
- Updated generated checklist, format audit, and repository documentation to describe the LaTeX package-order policy.
- Regenerated the English Overleaf package, bilingual LaTeX package, Word/PDF manuscripts, support documents, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; fallback English Overleaf package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, and Chinese XeLaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English PDF exported successfully and submission package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new checks that English `main.tex` files load `lineno` before `hyperref`.
- Inspected `paper/jnca_english_overleaf_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, and `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; each zipped `main.tex` has `\usepackage{lineno}` before `\usepackage{hyperref}`.
- Inspected `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, and `docs/jnca_submission_generation.md`; each records the LaTeX package-order policy.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: changed English `elsarticle` package order to load `lineno` before `hyperref`.
- `scripts/generate_jnca_overleaf.py`: changed fallback English Overleaf package order to match the main generator.
- `scripts/validate_jnca_submission.py`: added package-order validation for English `elsarticle` sources and required generated docs to mention the new policy.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to include LaTeX package-order checks.
- `docs/jnca_submission_generation.md`: added the LaTeX Package Order Policy.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, and `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: refreshed by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the package-order update.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_overleaf.py`, `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Add source text hygiene checks for LaTeX upload files
### What was done
- Added UTF-8/source-text hygiene validation for generated LaTeX and BibTeX sources, including checks for invalid UTF-8, UTF-8 BOM, NUL bytes, mixed newline styles, and ASCII safety where English pdfLaTeX sources require it.
- Extended the validation from folder files to packaged zip entries, so `main.tex` and `references.bib` inside the direct Overleaf and flat Editorial Manager zips are checked before upload.
- Updated generated checklist, format audit, and repository documentation with the new Source Text Hygiene Policy.
- Regenerated the English Overleaf package, bilingual LaTeX package, Word/PDF manuscripts, support documents, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; fallback English Overleaf package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, and Chinese XeLaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English PDF exported successfully and submission package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including source text hygiene checks for folder files and packaged zip entries.
- Inspected `paper/jnca_english_overleaf_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, and `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; each `main.tex` and `references.bib` entry is BOM-free, NUL-free, and ASCII-safe.
- Inspected `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, and `docs/jnca_submission_generation.md`; each records source text hygiene guidance.

### Notes
- `scripts/validate_jnca_submission.py`: added reusable source text hygiene checks and applied them to English LaTeX, BibTeX, and packaged zip entries.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to mention source text hygiene.
- `docs/jnca_submission_generation.md`: added the Source Text Hygiene Policy.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, and `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: refreshed by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after adding source text hygiene checks.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Audit Elsevier template dependency handling
### What was done
- Confirmed the bundled official Elsevier template folder contains `elsarticle.dtx`, `elsarticle.ins`, and `elsarticle-num.bst`, but no pre-extracted `elsarticle.cls`; no local TeX engine was available to generate and validate a class file.
- Kept the package policy conservative: do not fabricate `elsarticle.cls`; expect it from Overleaf or the submission-system TeX installation, and document `elsarticle.cls not found` as a platform/template-environment issue.
- Added validation that every packaged `elsarticle-num.bst` matches the official Elsevier template copy byte-for-byte.
- Updated Overleaf, Editorial Manager, checklist, format-audit, and repository documentation so template dependencies and `elsarticle.cls` triage are explicit.
- Regenerated the English Overleaf package, bilingual LaTeX package, Word/PDF manuscripts, support documents, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `where.exe pdflatex`, `where.exe latex`, and `where.exe kpsewhich`; no local TeX engine was found, so no local `elsarticle.cls` extraction or compile was attempted.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; fallback English Overleaf package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, and Chinese XeLaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English PDF exported successfully and submission package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including checks that packaged `elsarticle-num.bst` files match the official template copy.
- Inspected `paper/jnca_english_overleaf_package.zip`, `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, and `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; each README mentions `elsarticle.cls`, and each packaged `elsarticle-num.bst` matches the official template source.
- Inspected `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, and `docs/jnca_submission_generation.md`; each records the relevant template dependency or `elsarticle.cls` triage guidance.

### Notes
- `scripts/validate_jnca_submission.py`: added the official Elsevier template path and byte-for-byte `elsarticle-num.bst` package validation.
- `scripts/generate_jnca_overleaf.py`: updated fallback Overleaf README text with `elsarticle-num.bst` and `elsarticle.cls` dependency guidance.
- `scripts/generate_jnca_bilingual_latex.py`: updated bilingual, English Overleaf, and flat Editorial Manager README text with `elsarticle.cls` dependency guidance.
- `scripts/generate_jnca_submission.py`: updated generated import guide, import-format check, checklist, and format audit with Elsevier template dependency guidance.
- `docs/jnca_submission_generation.md`: added the Elsevier Template Dependency Policy and `elsarticle.cls not found` triage note.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/submission_checklist.md`, and `paper/submission_jnca/submission_format_audit.md`: regenerated with the new template-dependency text.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the template dependency update.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_overleaf.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Add LaTeX label hygiene validation
### What was done
- Added LaTeX label hygiene validation for generated manuscripts, checking duplicate labels, nonportable label names, and missing standard `fig:`/`tab:` prefixes for figure/table labels.
- Kept the existing cross-reference checks and extended them so future table or figure additions must keep labels unique and portable before Overleaf upload.
- Updated generated checklist, format audit, and repository documentation with the new LaTeX Label Hygiene Policy.
- Regenerated the English Overleaf package, bilingual LaTeX package, Word/PDF manuscripts, support documents, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; fallback English Overleaf package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, and Chinese XeLaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English PDF exported successfully and submission package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new label hygiene checks.
- Inspected `paper/submission_jnca/overleaf_jnca/main.tex`; it contains 16 labels and 14 references, with no duplicate labels and no nonportable label names.
- Inspected `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, and `docs/jnca_submission_generation.md`; each records label hygiene guidance.

### Notes
- `scripts/validate_jnca_submission.py`: added label hygiene checks for duplicate labels, nonportable names, and table/figure prefix consistency.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to include LaTeX label hygiene checks.
- `docs/jnca_submission_generation.md`: added the LaTeX Label Hygiene Policy.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, and `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: refreshed by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after adding label hygiene validation.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Strengthen Overleaf and Editorial Manager import-format validation
### What was done
- Added stricter LaTeX import-format validation for English Elsevier sources, covering frontmatter order, table/figure caption-label hygiene, portable graphics and bibliography paths, and source-package README consistency.
- Updated English Overleaf and flat Editorial Manager README generation so each zip explains its root files, compiler, figure layout, `elsarticle.cls` dependency, and why the mixed handoff bundle must not be imported as a LaTeX project.
- Updated generated checklist, format audit, and repository documentation with Elsevier frontmatter, LaTeX float hygiene, and source-package README policies.
- Regenerated the English Overleaf package, bilingual LaTeX package, Word/PDF manuscripts, support documents, direct Overleaf zip, flat Editorial Manager zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_overleaf.py`; fallback English Overleaf package regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, Chinese XeLaTeX, submission Overleaf, and flat Editorial Manager source packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English Word/PDF manuscript and submission bundle regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new frontmatter, caption-label, portable path, README/package consistency, and zip hygiene checks.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; it contains root `main.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, and figures under `figures/`.
- Inspected `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`; it contains root `main.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, and root-level PNG figures without subdirectories.
- Checked the English PDF header with a byte read; it starts with `%PDF-`.

### Notes
- `scripts/validate_jnca_submission.py`: added Elsevier frontmatter order checks, table/figure float hygiene checks, portable graphics/bibliography path checks, and source-package README consistency checks.
- `scripts/generate_jnca_bilingual_latex.py`: updated generated Overleaf and Editorial Manager README text with explicit package layout, compiler, `elsarticle.cls`, artwork-only, and wrong-bundle warnings.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to include frontmatter order, table/figure hygiene, and README/package consistency.
- `docs/jnca_submission_generation.md`: added Elsevier Frontmatter, LaTeX Float Hygiene, and Source Package README policies.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, and `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: refreshed by the submission workflow.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after strengthening import-format validation.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Expand final placeholder replacement audit across Word and LaTeX sources
### What was done
- Expanded `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md` from a coarse placeholder count into a submission-ready metadata replacement inventory.
- Added scanning for the direct Overleaf LaTeX sources and flat Editorial Manager LaTeX sources, so author, affiliation, email, funding, acknowledgement, repository, and generic placeholder markers are visible across Word and LaTeX outputs.
- Added a token inventory that reports occurrences and locations for `Author One`, `Author Two`, `Author Three`, `Corresponding Author`, `email@example.com`, affiliations, city/country placeholders, funding text, repository-policy text, and generic placeholder markers.
- Updated validation and repository documentation so the placeholder audit must continue covering Word/support files plus the LaTeX source files.
- Regenerated the submission Word/PDF/support files, placeholder audit, figure upload bundle, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English Word/PDF manuscript and submission bundle regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including checks for the expanded placeholder audit sections and LaTeX source-file coverage.
- Inspected `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`; it lists scanned Word/support files, `overleaf_jnca/main.tex`, `overleaf_jnca/JNCA_HSTA_Encrypted_Traffic_EN.tex`, `editorial_manager_latex_source/main.tex`, and `editorial_manager_latex_source/JNCA_HSTA_Encrypted_Traffic_EN.tex`.
- Inspected the token inventory in `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`; it reports counts and locations for author names, affiliation placeholders, `email@example.com`, funding text, repository-policy text, and generic placeholder markers.
- Checked the English PDF header with a byte read; it starts with `%PDF-`.

### Notes
- `scripts/generate_jnca_submission.py`: expanded placeholder replacement audit generation to scan Word/support files plus direct Overleaf and flat Editorial Manager LaTeX source files, and added token-level replacement inventory.
- `scripts/validate_jnca_submission.py`: updated generated-document validation so `FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md` must include scanned source files, token inventory, LaTeX placeholder handling, and LaTeX source-file paths.
- `docs/jnca_submission_generation.md`: updated the placeholder audit policy to state that the audit covers Word/support files and LaTeX source files with per-file and token-level counts.
- `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`: regenerated with expanded source-file coverage and token inventory.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip` and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated by the submission workflow.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Add English Word manuscript structure hygiene validation
### What was done
- Added English Word structure hygiene validation for the generated manuscript, covering the controlled title, expected heading sequence, continuous Table 1-10 plus Appendix A/B captions, duplicate table captions, CJK characters, editable figure placeholder text, and repeated plain spaces.
- Updated generated checklist and format-audit wording so Word/PDF review-format checks now include both review formatting and structure hygiene.
- Updated repository documentation with the Word Structure Hygiene Policy.
- Regenerated the submission Word/PDF/support files, checklist, format audit, figure upload bundle, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran a read-only Word inspection script on `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`; it reported 108 paragraphs, 12 tables, 4 embedded images, the expected heading sequence, Table 1-10 plus Appendix A/B captions, Figure 1-4 captions, zero CJK characters, zero editable figure placeholders, and zero repeated plain-space matches.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; English Word/PDF manuscript and submission bundle regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new English Word title, heading, table-caption, CJK, figure-placeholder, and repeated-space checks.
- Checked the English PDF header with a byte read; it starts with `%PDF-`.
- Inspected `paper/submission_jnca/submission_checklist.md` and `paper/submission_jnca/submission_format_audit.md`; both mention English Word structure hygiene.

### Notes
- `scripts/validate_jnca_submission.py`: added `check_english_word_structure_hygiene` and wired it into English manuscript validation.
- `scripts/generate_jnca_submission.py`: updated generated checklist and format-audit wording to include English Word structure hygiene.
- `docs/jnca_submission_generation.md`: added the Word Structure Hygiene Policy.
- `paper/submission_jnca/submission_checklist.md` and `paper/submission_jnca/submission_format_audit.md`: regenerated with Word structure hygiene guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip` and `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`: regenerated by the submission workflow.
- Rollback: revert `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the prior generation sequence or restore previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Fix JNCA import/format checks and Word table page-break layout
### What was done
- Investigated the likely source of many import errors after upload and confirmed the generated package separates direct Overleaf source, flat Editorial Manager source, and the mixed handoff bundle.
- Found a real Word/PDF formatting defect during rendered PDF review: several result-table rows could split across pages, causing labels such as `(Proposed)` or transfer directions to appear separated from their row values.
- Updated the Word table generation path so table captions stay with their tables, header rows repeat across page breaks, all table rows are marked as non-splitting, table text uses compact single spacing, and cell contents stay vertically centered.
- Extended validation so the English Word manuscript now fails if repeated table-header markers or non-splitting row markers are missing.
- Updated repository/submission documentation and regenerated the English/Chinese Word manuscripts, English PDF, Overleaf source zip, flat Editorial Manager source zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_overleaf.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English Overleaf, and Chinese XeLaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word manuscripts, support files, English PDF, checklists, and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including repeated table header rows, non-splitting table rows, Word/PDF structure, LaTeX source hygiene, zip layout, BibTeX integrity, and upload-bundle checks.
- Rendered `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` with Poppler; PDF info reported 20 pages, letter size, unencrypted, tagged, and valid metadata. Visual inspection of the previously problematic result pages confirmed the split-row artifacts were removed.
- Attempted DOCX-to-PNG rendering with the document skill renderer, but LibreOffice/soffice is not installed on this machine. PDF rendering was used for visual QA instead. Local LaTeX compilation was not performed because no TeX engine is available in this environment.

### Notes
- `scripts/generate_jnca_submission.py`: added Word table page-break controls, repeated header rows, non-splitting rows, compact table-cell spacing, and updated generated checklist/format-audit wording.
- `scripts/validate_jnca_submission.py`: added OOXML checks for repeated table header rows and non-splitting table rows in the English manuscript.
- `docs/jnca_submission_generation.md`: documented the Word table page-break policy and validation coverage.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/submission_checklist.md`, `paper/submission_jnca/submission_format_audit.md`, `paper/submission_jnca/submission_upload_manifest.md`, `paper/submission_jnca/JNCA_GFA_COMPLIANCE_CHECK.md`, `paper/submission_jnca/FINAL_PLACEHOLDER_REPLACEMENT_CHECK.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/LATEX_IMPORT_TROUBLESHOOTING.md`, and `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`: refreshed by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the format fix.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, and `docs/jnca_submission_generation.md`; then rerun the previous generation sequence or restore the prior generated artifacts from backup/version control.

## 2026-07-01 - Task: Recheck JNCA import-format errors and manuscript formatting hygiene
### What was done
- Rechecked the generated English JNCA Word/PDF manuscript, Overleaf source package, flat Editorial Manager source package, and mixed handoff bundle after the reported import-error concern.
- Clarified the likely source of many import errors: `JNCA_recommended_upload_bundle.zip` is a mixed handoff bundle and should not be imported as an Overleaf project; `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` is the direct Overleaf package.
- Added a first-fatal-error diagnosis section to the generated Overleaf/import troubleshooting notes, so future checks distinguish one real fatal import cause from a long LaTeX cascade.
- Kept the manuscript/result boundary unchanged: no training was run, no result CSVs were edited, and table values continue to be generated from existing result summaries.
- Regenerated the English/Chinese Word manuscripts, English PDF preview, Overleaf/Editorial Manager LaTeX source zips, checklist, import guide, troubleshooting note, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; Overleaf, bilingual, English-only, and Chinese-only LaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including Word/PDF structure, table row/header OOXML, LaTeX source hygiene, BibTeX integrity, graphics paths, zip-entry hygiene, direct Overleaf package layout, flat Editorial Manager package layout, and the new first-fatal-error guidance checks.
- Rendered the final `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` with Poppler at 120 dpi; 20 page PNGs were produced, and the rendered contact sheet showed no obvious clipping, overlap, broken tables, or large unintended gaps.
- Inspected rendered pages around the previously risky areas: page 7 no longer has an isolated `[14]`, pages 9-12 show dense result tables/figures without row-splitting artifacts, and pages 18-20 show appendix tables with repeated headers and no truncation.
- Ran a PDF text scan with the bundled document-runtime `pypdf`; it reported 20 pages and 0 isolated citation lines or suspicious internal markers.
- Checked local tool availability: no `pdflatex`, `latexmk`, `soffice`, or `libreoffice` is available, so local TeX compilation and DOCX-to-PNG rendering were not claimed.

### Notes
- `scripts/generate_jnca_submission.py`: added first-fatal-error import diagnosis to generated Overleaf/import troubleshooting notes.
- `scripts/validate_jnca_submission.py`: added validation requirements for the first-fatal-error and extra-top-level-folder import guidance.
- `docs/jnca_submission_generation.md`: documented that import-error triage should start from the first fatal log line and should preserve generated zip structure.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`: regenerated with the first fatal error map and correct package-use guidance.
- `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`: regenerated with first-fatal-line triage and package separation guidance.
- `paper/submission_jnca/LATEX_IMPORT_TROUBLESHOOTING.md`: regenerated with cascade-error handling and extra-top-level-folder guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the import-format check.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/validate_jnca_submission.py`, `docs/jnca_submission_generation.md`, and this `progress.md` entry; then rerun the previous generation sequence or restore the previous generated submission artifacts from backup/version control.

## 2026-07-01 - Task: Strengthen English SCI narrative with external-paper framing and recheck formatting
### What was done
- Reviewed strong encrypted-traffic papers and dataset papers as narrative references, including SoK-style validity framing, ET-BERT-style representation framing, NetMamba-style efficiency framing, TrafficFormer-style traffic-specific representation framing, CESNET-TLS-Year22-style dataset-boundary framing, and DataZoo-style reproducibility framing.
- Reworked the English manuscript narrative in the generation source: the Abstract now reads as one integrated SCI-style story; the Introduction now moves from observable-signal scarcity to evaluation validity and then to the HSTA stage-order mechanism; Related Work, Problem Definition, Proposed Method, Results, Discussion, and Conclusion were tightened around controlled input, mechanism evidence, and conservative deployment boundaries.
- Updated the narrative reference note and made it part of validation, so the external-paper writing references remain traceable without introducing new experimental claims.
- Fixed a rendered PDF layout issue introduced by the longer English text: Table 2 previously left only the caption/header at the bottom of a page, so the English Word generation path now starts Table 2 on the next page.
- Regenerated the English/Chinese Word manuscripts, English PDF preview, Overleaf/Editorial Manager LaTeX source zips, checklist, import guide, troubleshooting note, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\validate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; Overleaf, bilingual, English-only, and Chinese-only LaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new narrative-note checks, Word/PDF structure, Word/LaTeX alignment, LaTeX labels and cross-references, BibTeX integrity, zip-entry hygiene, direct Overleaf package layout, and flat Editorial Manager package layout.
- Rendered the final `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` with Poppler at 120 dpi; 21 page PNGs were produced. Visual inspection confirmed that the Table 2 orphan-header issue was fixed, dense result pages remained readable, and the appendix tail page was not truncated.
- Ran a PDF text scan with the bundled document-runtime `pypdf`; it reported 21 pages and 0 isolated citation lines or suspicious internal markers.
- Checked local tool availability: no `pdflatex`, `latexmk`, `soffice`, or `libreoffice` is available, so true local LaTeX compilation and DOCX-to-PNG rendering were not claimed.

### Notes
- `scripts/generate_jnca_submission.py`: rewrote English SCI narrative sections and added an English Table 2 page break to avoid an orphan table header in the rendered PDF.
- `scripts/generate_jnca_bilingual_latex.py`: updated English LaTeX cross-reference injection so the revised attention-ablation paragraph still references Table 6 and Figure 3.
- `scripts/validate_jnca_submission.py`: added checks that the narrative reference note exists and records the core external-paper framing set.
- `docs/jnca_reference_narrative_notes.md`: expanded the external-paper narrative note with TrafficFormer, CESNET-TLS-Year22, and DataZoo framing lessons, plus the manuscript adjustments derived from them.
- `docs/jnca_submission_generation.md`: documented that the narrative reference note is now part of validation coverage.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the narrative and layout updates.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, `docs/jnca_reference_narrative_notes.md`, `docs/jnca_submission_generation.md`, and this `progress.md` entry; then rerun the previous generation sequence or restore the previous generated submission artifacts from backup/version control.

## 2026-07-02 - Task: Harden JNCA LaTeX import compatibility and revalidate formatting
### What was done
- Rechecked the reported "many errors after import" path across the direct Overleaf package, flat Editorial Manager package, and mixed handoff bundle.
- Kept the main diagnosis explicit: `JNCA_recommended_upload_bundle.zip` is not a direct Overleaf project, while `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` is the direct English Overleaf package.
- Reduced a real compatibility risk in the English `elsarticle` source by replacing newer structured `\affiliation[...]` frontmatter fields with legacy-compatible `\address[...]` markers in the generation source.
- Extended validation and generated troubleshooting notes so future packages fail if the English LaTeX frontmatter returns to `\affiliation[...]`, and so an `Undefined control sequence \affiliation` error maps to the regenerated package.
- Regenerated the bilingual/English/Chinese LaTeX packages, direct Overleaf zip, flat Editorial Manager source zip, Word/PDF manuscripts, submission checklist, format audit, import guides, support documents, and recommended handoff bundle.
- No training was run, no model code was changed, and no `results/` CSV files were edited.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; Overleaf, bilingual, English-only, and Chinese-only LaTeX packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including the new legacy-compatible Elsevier `\address[...]` affiliation check, Word/PDF structure, LaTeX source hygiene, BibTeX integrity, graphics paths, zip-entry hygiene, direct Overleaf package layout, flat Editorial Manager package layout, and upload-bundle checks.
- Inspected `paper/submission_jnca/overleaf_jnca/main.tex`; it now contains `\address[aff1]` and `\address[aff2]` and no `\affiliation[` entry.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; it contains root-level `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, and `figures/`.
- Rendered `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` with Poppler at 120 dpi; `pdfinfo` reported 23 pages, Letter page size, unencrypted PDF, and Word 2024 as the exporter. Visual inspection of the full contact sheet plus pages 8-13 and 20-23 found no obvious overlap, clipping, broken tables, missing glyphs, or blank trailing page.
- Local TeX compilation was not performed because `pdflatex`, `latexmk`, `bibtex`, `tectonic`, and `chktex` are not available in this environment. DOCX-to-PNG rendering was not used because `soffice`/LibreOffice is unavailable; PDF rendering was used for visual QA.

### Notes
- `scripts/generate_jnca_bilingual_latex.py`: changed English `elsarticle` author-affiliation generation to legacy-compatible `\address[...]` and updated source-package README wording.
- `scripts/generate_jnca_overleaf.py`: changed the older Overleaf generator's English frontmatter to `\address[...]` for consistency.
- `scripts/validate_jnca_submission.py`: added validation that English `elsarticle` sources use `\address[...]` affiliations and do not use structured `\affiliation[...]` fields.
- `scripts/generate_jnca_submission.py`: updated generated checklist, format audit, import guide, import-format check, and LaTeX troubleshooting text to document the `\address[...]` compatibility rule and `\affiliation` error triage.
- `docs/jnca_submission_generation.md`: documented the Elsevier frontmatter compatibility policy.
- `paper/submission_jnca/OVERLEAF_IMPORT_GUIDE.md`, `paper/submission_jnca/SUBMISSION_IMPORT_FORMAT_CHECK.md`, `paper/submission_jnca/LATEX_IMPORT_TROUBLESHOOTING.md`, `paper/submission_jnca/submission_checklist.md`, and `paper/submission_jnca/submission_format_audit.md`: regenerated with the updated import-format and affiliation-compatibility guidance.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/submission_jnca/overleaf_jnca_package.zip`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: regenerated after the LaTeX compatibility fix.
- `progress.md`: appended this work log entry.
- Rollback: revert `scripts/generate_jnca_bilingual_latex.py`, `scripts/generate_jnca_overleaf.py`, `scripts/validate_jnca_submission.py`, `scripts/generate_jnca_submission.py`, `docs/jnca_submission_generation.md`, and this `progress.md` entry; then rerun the previous generation sequence or restore the prior generated submission artifacts from backup/version control.

## 2026-07-02 - Task: Recheck JNCA import errors and final Word/PDF formatting
### What was done
- Rechecked the English SCI manuscript, direct Overleaf zip, flat Editorial Manager source zip, and mixed handoff bundle after the reported import-error concern.
- Confirmed the likely cause of many immediate Overleaf errors: the mixed `JNCA_recommended_upload_bundle.zip` is not a direct LaTeX project; the direct Overleaf package remains `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` with root-level `main.tex`, `references.bib`, `elsarticle-num.bst`, `latexmkrc`, README, and `figures/`.
- Completed the English SCI narrative synchronization by keeping the dedicated `8 Threats to Validity` section and `9 Conclusion` aligned across Word and LaTeX outputs.
- Fixed a real rendered PDF formatting defect: the English PDF previously ended with an unintended blank final page. Appendix mapping tables now use compact 8 pt table text and a suppressed 1 pt trailing paragraph so the appendix tail finishes cleanly without a blank page or stray line number.
- Regenerated the English/Chinese Word manuscripts, English PDF preview, support documents, direct Overleaf zip, flat Editorial Manager source zip, figure upload zip, and recommended handoff bundle.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including Word/PDF structure, English Word review format, table captions, figure captions, result-table values from generated tables, Word/LaTeX alignment, BibTeX integrity, LaTeX source hygiene, graphics paths, direct Overleaf zip layout, flat Editorial Manager zip layout, import-troubleshooting guidance, and upload-bundle checks.
- Rendered `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf` with Poppler; `pdfinfo` reported 21 pages, Letter page size, unencrypted PDF, and `%PDF-`/EOF validation passed. Visual inspection confirmed that the previous blank page 22 is gone and the final page now contains the TLS appendix table cleanly.
- Inspected key rendered pages around dense result tables, Figure 4, `8 Threats to Validity`, `9 Conclusion`, and the appendix tail; no obvious overlap, clipping, orphan table header, or blank trailing page remained.
- Checked local tool availability: no `pdflatex`, `latexmk`, `bibtex`, `tectonic`, `chktex`, `soffice`, or `libreoffice` is available on this machine, so true local LaTeX compilation and DOCX-to-PNG rendering were not claimed. Final LaTeX compilation still needs Overleaf or another TeX environment.

### Notes
- `scripts/generate_jnca_submission.py`: kept the SCI narrative/Threats structure and added appendix table compacting plus a suppressed compact table trailer to remove the blank PDF tail page.
- `scripts/generate_jnca_bilingual_latex.py`: keeps the English LaTeX section sequence aligned with the Word manuscript, including `Threats to Validity`.
- `scripts/validate_jnca_submission.py`: validates the English Word/LaTeX section alignment, LaTeX source hygiene, import package layout, and generated support-note coverage.
- `docs/jnca_reference_narrative_notes.md`: records the external-paper narrative framing and the conservative validity-boundary lessons used in the English SCI rewrite.
- `docs/jnca_submission_generation.md`: documents the generated submission workflow, import-format rules, validation coverage, and local validation boundary.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, `paper/submission_jnca/overleaf_jnca/`, and generated checklist/audit/import-guide files: refreshed by the submission workflow.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, `docs/jnca_reference_narrative_notes.md`, `docs/jnca_submission_generation.md`, and this `progress.md` entry; then rerun the previous generation sequence or restore the previous generated submission artifacts from backup/version control.

## 2026-07-02 - Task: Revalidate JNCA import package and document formatting rules
### What was done
- Rechecked the reported "many errors after import" concern against the current English SCI/JNCA submission package.
- Confirmed the operational diagnosis: `UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip` is the direct Overleaf project, while `JNCA_recommended_upload_bundle.zip` is a mixed handoff bundle and should not be imported as an Overleaf project.
- Added the appendix pagination rule to the reproducible generation path and documentation: appendices now start on a new Word/PDF page after the reference list, and the generated checklist/audit state this rule explicitly.
- Regenerated the Word/PDF/support files and refreshed the direct Overleaf zip, flat Editorial Manager source zip, and recommended handoff bundle.
- No training was run, no model code was changed, and no `results/` CSV files were edited.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed, including Word/PDF structure, English Word review format, result-table values from generated tables, Word/LaTeX alignment, BibTeX integrity, LaTeX source hygiene, graphics paths, direct Overleaf zip layout, flat Editorial Manager zip layout, import-troubleshooting guidance, and upload-bundle checks.
- Ran Poppler `pdfinfo` on `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`; it reported 25 pages, Letter page size, unencrypted PDF, Word 2024 exporter, and PDF 1.7.
- Rendered the regenerated English PDF with Poppler at 110 dpi; 25 page PNGs were produced. Visual inspection of the full contact sheet confirmed no obvious blank page, clipping, overlap, broken table, or appendix stranding; Appendix A starts on page 23 after references end on page 22.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; it contains root-level `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, and `figures/` only.
- Ran `git diff --name-only -- results`; no `results/` files were modified.
- Checked local tool availability: no `pdflatex`, `latexmk`, or `soffice` is available, so true local LaTeX compilation and DOCX-to-PNG rendering were not claimed. Final LaTeX compilation still needs Overleaf or another TeX environment.

### Notes
- `scripts/generate_jnca_submission.py`: added appendix-new-page wording to generated checklist and format-audit output while preserving the existing appendix page break behavior.
- `docs/jnca_submission_generation.md`: documented that appendices start on a new Word/PDF page after the reference list.
- `paper/submission_jnca/submission_checklist.md` and `paper/submission_jnca/submission_format_audit.md`: regenerated with the appendix pagination rule.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, `paper/submission_jnca/overleaf_jnca/`, and generated import-guide files: refreshed by the submission workflow.
- `tmp/jnca_pdf_render/`: contains temporary PDF render PNGs/contact sheets used for visual QA in this round.
- Rollback: revert `scripts/generate_jnca_submission.py`, `docs/jnca_submission_generation.md`, regenerated `paper/submission_jnca/` artifacts, and this `progress.md` entry; then rerun the previous generation sequence or restore the previous generated submission artifacts from backup/version control.

## 2026-07-02 - Task: Second-pass English SCI narrative optimization and format verification
### What was done
- Rechecked high-quality encrypted-traffic and JNCA-style papers as narrative references, focusing on how they establish observable inputs, controlled evaluation scope, traffic unit, deployment pressure, and validity boundaries before presenting model gains.
- Strengthened the English manuscript narrative in the reproducible generation source: the Abstract now frames the problem as transformation of weak early-flow evidence; the Introduction now states a clearer reader contract and contribution set; the Experimental Setup now reads as an evidence ladder; the Results section now treats attention-position ablation as a negative control and cross-protocol transfer as a stress test of representation reuse.
- Updated narrative notes and generation documentation so the reader-contract, evidence-ladder, negative-control, and bounded-transfer lessons remain traceable.
- Updated validation to require the new second-pass narrative-note markers.
- Regenerated bilingual LaTeX, English Overleaf, Chinese XeLaTeX, Word/PDF, support documents, source zips, figure bundle, and the recommended handoff bundle.
- No training was run, no model code was changed, and no `results/` CSV files were edited.

### Testing
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' -m py_compile scripts\generate_jnca_submission.py scripts\generate_jnca_bilingual_latex.py scripts\generate_jnca_overleaf.py scripts\validate_jnca_submission.py`; syntax check passed.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_bilingual_latex.py`; bilingual, English-only, Chinese-only, Overleaf, and Editorial Manager LaTeX source packages regenerated.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\generate_jnca_submission.py`; Word/PDF/support files and upload bundles regenerated, with PDF export reported as ok.
- Ran `& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' scripts\validate_jnca_submission.py`; validation passed after fixing a LaTeX cross-reference injection regression caught by the validator. The passing run covered Word/PDF structure, abstract length, Word/LaTeX alignment, all non-appendix table/figure references, BibTeX integrity, source text hygiene, graphics paths, direct Overleaf package layout, flat Editorial Manager package layout, and upload-bundle checks.
- Ran Poppler `pdfinfo` on `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`; it reported 25 pages, Letter page size, unencrypted PDF, Word 2024 exporter, and PDF 1.7.
- Rendered the regenerated English PDF with Poppler at 110 dpi; 25 page PNGs were produced. Visual inspection of the full contact sheet found no obvious blank page, clipping, overlap, broken table, or appendix stranding; Appendix A still starts on page 23 after references end on page 22.
- Inspected `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`; it contains root-level `main.tex`, `JNCA_HSTA_Encrypted_Traffic_EN.tex`, `references.bib`, `elsarticle-num.bst`, `README.md`, `latexmkrc`, and `figures/` only.
- Ran `git diff --name-only -- results`; no `results/` files were modified.
- Checked local tool availability boundary from prior runs: no local `pdflatex`, `latexmk`, or `soffice` is available, so true local LaTeX compilation and DOCX-to-PNG rendering were not claimed. Final LaTeX compilation still needs Overleaf or another TeX environment.

### Notes
- `scripts/generate_jnca_submission.py`: refined English Abstract, Introduction, Background, Experimental Setup, Results, and Discussion narrative while keeping reported values and experiment scope unchanged.
- `scripts/generate_jnca_bilingual_latex.py`: updated English result-paragraph reference injection so the revised ablation and transfer paragraphs still cite their corresponding tables and figures.
- `scripts/validate_jnca_submission.py`: added checks for the new second-pass narrative-note markers.
- `docs/jnca_reference_narrative_notes.md`: recorded the reader-contract, evidence-ladder, negative-control, and bounded-transfer narrative lessons.
- `docs/jnca_submission_generation.md`: documented the second-pass narrative policy for generated English SCI outputs.
- `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.docx`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_EN.pdf`, `paper/submission_jnca/JNCA_HSTA_Encrypted_Traffic_CN.docx`, and submission support `.docx` files: regenerated by the submission workflow.
- `paper/submission_jnca/UPLOAD_TO_OVERLEAF_JNCA_ENGLISH.zip`, `paper/submission_jnca/JNCA_EDITORIAL_MANAGER_LATEX_SOURCE.zip`, `paper/submission_jnca/JNCA_recommended_upload_bundle.zip`, `paper/submission_jnca/FIGURES_FOR_UPLOAD.zip`, `paper/submission_jnca/overleaf_jnca/`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_english_overleaf_package.zip`, and `paper/jnca_chinese_xelatex_package.zip`: refreshed after the narrative optimization.
- `tmp/jnca_pdf_render/`: contains temporary PDF render PNGs/contact sheets used for visual QA in this round.
- Rollback: revert `scripts/generate_jnca_submission.py`, `scripts/generate_jnca_bilingual_latex.py`, `scripts/validate_jnca_submission.py`, `docs/jnca_reference_narrative_notes.md`, `docs/jnca_submission_generation.md`, regenerated `paper/submission_jnca/` and `paper/jnca_bilingual_latex*` artifacts, and this `progress.md` entry; then rerun the previous generation sequence or restore the previous generated submission artifacts from backup/version control.

## 2026-07-02 - Task: Organize paper directory and create HSTA group meeting materials
### What was done
- Organized `paper/` with a conservative classify-and-archive strategy: old Chinese Word drafts were moved into `paper/source_drafts/`, and the hidden draw.io backup was moved into `paper/source_drafts/_archive_or_backup/`.
- Kept `paper/submission_jnca/`, `paper/jnca_bilingual_latex/`, and the existing root-level JNCA zip packages in place so the current submission-generation chain is not broken.
- Created `paper/group_meeting_hsta_2026_07/` with `slides/`, `script/`, `paper_notes/`, `assets/`, `sources/`, and `sources/qa/`.
- Produced the requested group meeting materials: 15-slide Chinese PPT, page-matched Chinese speech DOCX, TrafficFormer 2025 notes, SAT-Net 2025 notes, HSTA own-work notes, comparison matrix, README, source links, reusable generation scripts, copied HSTA result figures, and QA render artifacts.
- No training was run, no model code was changed for this task, and no `results/` files were edited.

### Testing
- Ran the bundled artifact-tool workflow with the bundled Node runtime to generate `paper/group_meeting_hsta_2026_07/slides/HSTA_group_meeting.pptx`.
- Rendered the final PPTX with `render_slides.py`; 15 slide PNGs were produced under `paper/group_meeting_hsta_2026_07/sources/qa/pptx_rendered_slides/`.
- Ran `slides_test.py` on the final PPTX; it passed with `Test passed. No overflow detected.`
- Created and visually inspected `paper/group_meeting_hsta_2026_07/sources/qa/HSTA_group_meeting_montage.png`; fixed the initial title-slide clipping issue, regenerated the PPTX, rerendered, and rechecked the montage.
- Generated `paper/group_meeting_hsta_2026_07/script/HSTA_group_meeting_speech.docx` with the project Anaconda Python and `python-docx`.
- Structurally checked the speech DOCX with `python-docx`; it contains 15 `Heading 1` slide sections from `Slide 1: 标题与汇报目标` through `Slide 15: 总结与讨论问题`, 94 paragraphs, and required DOCX parts including `word/document.xml`, `word/styles.xml`, and `[Content_Types].xml`.
- Tried to render the speech DOCX with the documents skill `render_docx.py --emit_pdf`; rendering could not complete because this machine has no `soffice` or `libreoffice` command available. Structural DOCX validation was completed, but visual DOCX render QA is not claimed.
- Confirmed `paper/submission_jnca/`, `paper/jnca_bilingual_latex/`, `paper/jnca_bilingual_latex_package.zip`, `paper/jnca_chinese_xelatex_package.zip`, and `paper/jnca_english_overleaf_package.zip` still exist.
- Ran `git diff --name-only -- results`; no `results/` files were modified.

### Notes
- `paper/source_drafts/`: now holds the three old Chinese Word drafts (`初稿`, `修改版1`, and `最终优化版`) moved from the `paper/` root.
- `paper/source_drafts/_archive_or_backup/.$论文全部图_精修可编辑.drawio.bkp`: archived the hidden draw.io backup without deleting it.
- `paper/group_meeting_hsta_2026_07/README.md`: explains the group meeting folder structure, reporting order, modification entry points, and scope boundary.
- `paper/group_meeting_hsta_2026_07/paper_notes/TrafficFormer_2025.md`: summarizes TrafficFormer 2025 background, problem, method framing, experiment interpretation, innovation, limitations, and HSTA implications.
- `paper/group_meeting_hsta_2026_07/paper_notes/SAT-Net_2025.md`: summarizes SAT-Net 2025 background, problem, method, experiment setup, innovation, limitations, and HSTA implications.
- `paper/group_meeting_hsta_2026_07/paper_notes/HSTA_own_work.md`: reframes the current HSTA manuscript for group meeting presentation.
- `paper/group_meeting_hsta_2026_07/paper_notes/comparison_matrix.md`: compares TrafficFormer, SAT-Net, and HSTA by positioning, input view, mechanism, evidence, innovation, and boundaries.
- `paper/group_meeting_hsta_2026_07/assets/`: contains copied HSTA architecture, main-result, ablation, and transfer figures from `paper/submission_jnca/figures/`.
- `paper/group_meeting_hsta_2026_07/slides/HSTA_group_meeting.pptx`: generated 15-slide Chinese group meeting deck.
- `paper/group_meeting_hsta_2026_07/script/HSTA_group_meeting_speech.docx`: generated Chinese page-by-page speech script matching the 15-slide deck.
- `paper/group_meeting_hsta_2026_07/sources/source_links.md`: records external paper links and local manuscript/figure sources.
- `paper/group_meeting_hsta_2026_07/sources/build_group_meeting_deck.mjs`: reusable artifact-tool deck generator.
- `paper/group_meeting_hsta_2026_07/sources/build_group_meeting_speech.py`: reusable speech-DOCX generator.
- `paper/group_meeting_hsta_2026_07/sources/qa/`: stores rendered PPT slide PNGs, the montage, and PPT inspect output used for QA.
- Rollback: move the three Word drafts from `paper/source_drafts/` back to `paper/`, move `paper/source_drafts/_archive_or_backup/.$论文全部图_精修可编辑.drawio.bkp` back to `paper/`, remove `paper/group_meeting_hsta_2026_07/` if reverting the generated group meeting materials, and remove this `progress.md` entry.

## 2026-07-02 - Task: Localize group meeting paper folders and save original-paper sources
### What was done
- Renamed the user-facing group meeting materials from English folder/file names to Chinese names under `paper/组会材料_HSTA_2026年07月/`.
- Renamed the old draft archive from `paper/source_drafts/` to `paper/源稿归档/`, including the backup folder `备份与临时文件/`.
- Updated the reusable group meeting generation scripts so future PPT/DOCX generation works with the new Chinese directory and file names.
- Added `paper/目录说明.md` to explain the Chinese entry points and why a few JNCA submission-generation paths remain in English for script compatibility.
- Saved official source records for TrafficFormer 2025 and SAT-Net 2025 under `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/`, including official-page snapshots, Crossref metadata, Unpaywall open-access checks, Elsevier metadata, and `.url` shortcuts to the publisher pages.
- Kept failed PDF endpoint responses in `生成与来源/下载探测记录/` with explicit 403/418/400 names, so they are not mistaken for successfully downloaded paper PDFs.
- No training was run, no model code was changed, and no `results/` files were edited.

### Testing
- Regenerated the PPT from `paper/组会材料_HSTA_2026年07月/生成与来源/生成组会PPT.mjs` using the bundled Node/artifact-tool workflow; output was `paper/组会材料_HSTA_2026年07月/幻灯片/HSTA组会汇报.pptx`.
- Regenerated the speech DOCX from `paper/组会材料_HSTA_2026年07月/生成与来源/生成演讲稿.py` using `D:\ProgramData\anaconda3\envs\mybase\python.exe`; output was `paper/组会材料_HSTA_2026年07月/演讲稿/HSTA组会逐页演讲稿.docx`.
- Rendered the final PPTX with `render_slides.py`; 15 rendered slide PNGs were saved under `paper/组会材料_HSTA_2026年07月/生成与来源/质检记录/PPT渲染页图/`.
- Ran `slides_test.py` on the final PPTX; it passed with `Test passed. No overflow detected.`
- Created and visually inspected `paper/组会材料_HSTA_2026年07月/生成与来源/质检记录/PPT总览图.png`; no obvious blank slide, clipping, or major overlap was found.
- Structurally checked the regenerated DOCX with `python-docx`; it still contains 15 `Heading 1` slide sections from `Slide 1: 标题与汇报目标` through `Slide 15: 总结与讨论问题`.
- Checked the TrafficFormer and SAT-Net Unpaywall records; both report `is_oa: false`, so direct open-access PDFs were not available from the checked official/OA sources.
- Confirmed `paper/submission_jnca/` and `paper/jnca_bilingual_latex/` still exist for the existing JNCA generation scripts.
- Ran `git diff --name-only -- results`; no `results/` files were modified.

### Notes
- `paper/目录说明.md`: documents Chinese entry points and the remaining English technical paths retained for generation-script compatibility.
- `paper/组会材料_HSTA_2026年07月/说明.md`: Chinese group meeting folder README with updated folder and file names.
- `paper/组会材料_HSTA_2026年07月/幻灯片/HSTA组会汇报.pptx`: regenerated Chinese group meeting deck.
- `paper/组会材料_HSTA_2026年07月/演讲稿/HSTA组会逐页演讲稿.docx`: regenerated page-matched Chinese speech script.
- `paper/组会材料_HSTA_2026年07月/论文精读/`: contains the renamed TrafficFormer, SAT-Net, HSTA own-work, and comparison-matrix notes.
- `paper/组会材料_HSTA_2026年07月/图件/`: contains renamed HSTA architecture, main Macro-F1, attention-ablation, and transfer figures.
- `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/`: stores publisher links, metadata, official-page snapshots, OA checks, and the paper-source download explanation.
- `paper/组会材料_HSTA_2026年07月/生成与来源/下载探测记录/`: stores failed PDF/download endpoint responses with explicit status labels.
- `paper/组会材料_HSTA_2026年07月/生成与来源/生成组会PPT.mjs` and `生成演讲稿.py`: updated reusable generation scripts for Chinese paths.
- `paper/源稿归档/`: contains the archived old Chinese Word drafts and backup files.
- Rollback: rename `paper/组会材料_HSTA_2026年07月/` back to `paper/group_meeting_hsta_2026_07/`, rename `paper/源稿归档/` back to `paper/source_drafts/`, restore the previous English subfolder/file names inside the group-meeting folder, revert the generation-script path changes and `paper/目录说明.md`, remove the added `论文原文/` source records if not needed, and remove this `progress.md` entry.

## 2026-07-02 - Task: Download available original paper PDF
### What was done
- Successfully downloaded the TrafficFormer 2025 original PDF from the publicly reachable THUCSNet author/team page and saved it as `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/TrafficFormer_2025_原文.pdf`.
- Rechecked SAT-Net 2025 PDF routes through ScienceDirect, Elsevier Reader, and ACM DOI PDF forwarding. None returned a usable PDF in this environment.
- Moved failed PDF responses out of `论文原文/` into `生成与来源/下载探测记录/` with explicit status names, so the main original-paper folder does not contain misleading fake PDF files.
- Updated `论文原件下载说明.md` to state that TrafficFormer has a real PDF locally, while SAT-Net still requires browser/institutional access if the PDF is needed.

### Testing
- Checked `TrafficFormer_2025_原文.pdf`; it is 1,657,629 bytes and starts with `%PDF-`.
- Checked `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/` for SAT-Net PDF remnants; no `*SAT*pdf` file remains there.
- Ran `git diff --name-only -- results`; no `results/` files were modified.

### Notes
- `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/TrafficFormer_2025_原文.pdf`: downloaded real TrafficFormer PDF.
- `paper/组会材料_HSTA_2026年07月/生成与来源/论文原文/论文原件下载说明.md`: updated PDF availability notes.
- `paper/组会材料_HSTA_2026年07月/生成与来源/下载探测记录/`: now stores failed SAT-Net and IEEE PDF endpoint responses as clearly labeled non-PDF evidence.
- Rollback: remove `TrafficFormer_2025_原文.pdf`, restore the previous `论文原件下载说明.md`, move or remove the newly labeled failed endpoint response files if desired, and remove this `progress.md` entry.
