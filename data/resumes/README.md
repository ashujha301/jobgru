# Resumes for ATS scoring

Drop PDF resume(s) in this folder — **no manual manifest editing required**. The scorer auto-discovers `*.pdf` files and keeps `manifest.json` in sync.

## Quick setup

1. Copy your resume PDF here, e.g. `Ayush_Jha_Resume.pdf` or `ai-ml-engineer.pdf`.
2. Run scoring (manifest is updated automatically):

```bash
.venv/bin/python scripts/ats_score.py score --all
```

That's it. Multiple PDFs are all scored; column **I** lists every score; column **J** suggests improvements for the best match.

## Optional: custom labels

`manifest.json` is auto-generated from filenames:

| File | Auto label |
| --- | --- |
| `Ayush_Jha_Resume.pdf` | Ayush Jha Resume |
| `ai-ml-engineer.pdf` | Ai Ml Engineer |

To override a label (or stable `id`), edit `manifest.json` once — your entry is kept as long as the PDF file exists:

```json
{
  "resumes": [
    {
      "id": "backend",
      "file": "Ayush_BE.pdf",
      "label": "backend",
      "share_url": "https://bit.ly/aj_be"
    }
  ]
}
```

Optional `share_url` (Bitly or any public link) is used in Add note Message when that resume wins ATS scoring. Sync to column O:

```bash
.venv/bin/python scripts/resume_catalog.py sync-sheet
```

Column O format (one row per resume): `{share_url or filename} , {role}`

Add resumes via:

```bash
.venv/bin/python scripts/resume_catalog.py add --pdf path/to/resume.pdf --url https://bit.ly/xxx --label backend
```

Refresh manifest without scoring:

```bash
.venv/bin/python scripts/ats_score.py sync
```

## Behavior

- **One resume** — one score in column I.
- **Multiple resumes** — all scored; J uses the highest match only.
- **No PDFs in folder** — ATS scoring skipped for the run.
- **Prompt override** — `ATS scoring: no` disables scoring even when PDFs exist.

PDFs are gitignored (`data/resumes/*.pdf`). `manifest.json` is safe to commit (no secrets).
