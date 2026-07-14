# Revision 3 Chinese Manuscript Polishing

`scripts/polish_revision3.py` creates the strengthened Chinese Revision 3 manuscript from Revision 2 without changing the source document.

## Generate

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  scripts\polish_revision3.py `
  --project-root 'E:\AllProject\流量分析python项目\MM-MLP-A-MLP'
```

The command writes:

```text
paper/源稿归档/加密QUIC_TLS流量分类_修改版3.docx
```

## Scope

- Strengthens the abstract, contributions, research positioning, method explanation, results, discussion, deployment analysis, transfer analysis, scope, and conclusion.
- Preserves Revision 2, all 11 tables, 23 OMML formula objects, 28 references, and validated experimental values.
- Replaces the six embedded figures with the current 2400-pixel exports and inserts the data-processing pipeline as Figure 2.
- Keeps every table in English, repeats header rows across pages, and prevents individual table rows from splitting.

## Verify

```powershell
$env:HSTA_PROJECT_ROOT='E:\AllProject\流量分析python项目\MM-MLP-A-MLP'
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest tests.test_polish_revision3 -v
```

The tests compare the Word result tables with the validated CSV-backed figure data and verify figure hashes, structure, references, formula count, terminology, and table language.
