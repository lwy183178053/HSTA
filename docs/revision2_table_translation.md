# Revision 2 Table Translation

`scripts/translate_revision2_tables.py` converts every table cell in the Revision 2 manuscript to publication-style English while leaving body paragraphs and other DOCX parts unchanged.

## Apply

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  scripts\translate_revision2_tables.py `
  'paper\源稿归档\加密QUIC_TLS流量分类_修改版2.docx'
```

## Verify

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  scripts\translate_revision2_tables.py --check `
  'paper\源稿归档\加密QUIC_TLS流量分类_修改版2.docx'
```

The check exits with code `1` and lists remaining cells if any Chinese characters remain inside tables. The transformation is idempotent and updates only `word/document.xml` in the DOCX package.
