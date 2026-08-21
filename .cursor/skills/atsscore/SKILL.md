---
name: atsscore
description: Jobgru pipeline Phase 2b — score local resume PDFs against job Skills in the sheet. Writes column I (ATS score) and column J (Suggestions on Resume). Runs in parallel with LeadGru after Phase 1. Python-only scoring, rule-based suggestions, no LLM. Auto-on when data/resumes/ has PDFs; off when folder empty or prompt says ATS scoring no. Backfills all to apply rows with empty ATS score.
---

# ATSScore (Pipeline Phase 2b)

Score resume fit for each `to apply` job using **sheet data only** (title + Skills in Details) and local PDF resumes.

**Writes:**

| Col | Header | Content |
| --- | --- | --- |
| **I** | **ATS score** | Numeric scores per resume label |
| **J** | **Suggestions on Resume** | Rule-based improvement tips for best-matching resume |

No job URL fetch. No LLM. No browser.

Runs **in parallel with LeadGru** (Phase 2) — LeadGru uses browser for G/H; ATSScore uses one Python CLI for I/J.

## Pipeline mode (default)

**When:** Jobgru Phase 1 verified sheet append. Triggered automatically alongside LeadGru — no separate user prompt.

**On/off:**

| Condition | Action |
| --- | --- |
| No PDFs in `data/resumes/` | Skip; set `atsscore_status: skipped` in run JSON |
| User prompt contains `ATS scoring: no` | Skip |
| Resumes present + not disabled | Run |

**Scope:** All rows where Status = `to apply` AND column **I (ATS score)** is empty — includes new rows and backfill of older rows.

```bash
.venv/bin/python scripts/ats_score.py score --all
```

Optional dry-run first:

```bash
.venv/bin/python scripts/ats_score.py score --all --dry-run
```

## Standalone mode (backfill only)

**When:** User explicitly asks to run ATS scoring without Jobgru/LeadGru.

Use [prompts/atsscore-run.md](../../prompts/atsscore-run.md).

```bash
.venv/bin/python scripts/ats_score.py score --all
```

## Prerequisites

Run **Jobgru check**: `.venv/bin/python scripts/jobgru_check.py` — resumes in `data/resumes/` are optional (warn if missing).

Setup: [jobgru-setup skill](../jobgru-setup/SKILL.md). To add a resume via chat, use **add-resume** mode in that skill.

**Sheet headers (row 1)** must include:

- **I1** = `ATS score`
- **J1** = `Suggestions on Resume`

If missing, write via Sheets API:

```bash
.venv/bin/python scripts/sheets_write.py write --range "I1:J1" --json '[["ATS score", "Suggestions on Resume"]]'
```

**Resumes:**

1. Place PDF(s) in `data/resumes/` (manifest auto-syncs from filenames)
2. Optional: edit `manifest.json` only to customize `label` or `id`

```bash
.venv/bin/pip install -r scripts/requirements.txt
```

## Destination sheet (constants)

Read **`config/sheet.json`** (copy from `config/sheet.json.example` if missing).

| Constant | Source |
| --- | --- |
| Sheet URL | `sheet_url` in `config/sheet.json` |
| Spreadsheet ID | `spreadsheet_id` in `config/sheet.json` |
| Tab name | `tab` in `config/sheet.json` |
| ATS script | `scripts/ats_score.py` |
| Resumes | `data/resumes/` + `manifest.json` |

### Full column layout (Job Applications tab)

| Col | Header | Phase | ATSScore |
| --- | --- | --- | --- |
| A | Company Name | Jobgru writes | Read |
| B | Position | Jobgru writes | Read |
| C | Apply link | Jobgru writes | — |
| D | Status | Jobgru writes | Read (`to apply` only) |
| E | Date Applied | Jobgru writes | — |
| F | Details if any | Jobgru writes (incl. Skills) | Read |
| G | Leads | LeadGru writes | Never touch |
| H | Add note Message | LeadGru writes | Never touch |
| **I** | **ATS score** | — | **Write** when empty |
| **J** | **Suggestions on Resume** | — | **Write** when scoring succeeds |
| K | Summary | — | Never touch |
| L+ | Count, Latest Resume, templates (Q) | — | Never touch |

Jobgru leaves **I** and **J** blank on new rows. ATSScore fills them later in the same pipeline run or on backfill.

### Column I — ATS score (format)

**Multiple resumes:**

```
Backend SWE: 78, AI/ML: 62
```

**Single resume:**

```
Backend SWE: 78
```

**Insufficient data** (no `Skills:` in column F):

```
No skills data — add Skills to Details and rescore
```

Leave column **J (Suggestions on Resume)** empty for insufficient-data rows.

### Column J — Suggestions on Resume (format)

Rule-based suggestions for **highest-scoring resume only** when multiple resumes:

```
Best match: Backend SWE (78) | Add keywords: Kubernetes, GraphQL | Title fit: strong | Exp: matches
```

**Single resume:** same format, one best match.

## Coordinator workflow

1. Check `data/resumes/manifest.json` and PDF files exist. If not → skip, report in run JSON.
2. Check user prompt for `ATS scoring: no`. If set → skip.
3. Confirm row 1 headers: I = `ATS score`, J = `Suggestions on Resume`.
4. Run scorer (pipeline: immediately after Phase 1 verify, **parallel with LeadGru**):

   ```bash
   .venv/bin/python scripts/ats_score.py score --all
   ```

5. Parse stdout JSON summary into run JSON:
   - `atsscore_status`: `complete` | `skipped`
   - `atsscore_rows_scored`: row numbers
   - `atsscore_skipped_no_data`: rows missing Skills in F
   - `resumes_used`: labels from manifest
6. Do **not** run `format-layout` alone — Jobgru coordinator runs it after both Phase 2 tracks finish.

## Scoring inputs (sheet only)

Jobgru must append Skills to column F during Phase 1 verify:

```
Pay: ..., Exp: ..., Visa: ..., Remote, India, Posted: ... | Skills: Python, FastAPI, PostgreSQL, LLM
```

ATSScore reads:

- **B** — Position (title overlap)
- **F** — `Skills:` list, `Exp:` band, work arrangement
- **Local PDFs** — keyword match in resume text

Weights (deterministic Python in `scripts/ats_score.py`):

- Skills found in resume: 60%
- Title/headline overlap: 20%
- Experience band match: 20%

## Resume selection

Default: all entries in manifest with existing PDF files.

Prompt override (optional):

```text
Resumes: backend-swe, ai-ml
```

Maps to `--resumes backend-swe,ai-ml`.

## Sheet writes

Only write **I** and **J** for eligible rows:

```bash
# Done automatically by ats_score.py — example single row:
.venv/bin/python scripts/sheets_write.py write --range "I22:J22" --json '[["Backend SWE: 78", "Best match: Backend SWE (78) | Add keywords: Kubernetes | Title fit: strong | Exp: matches"]]'
```

Verify after batch:

```bash
.venv/bin/python scripts/sheets_write.py read --range "I2:J"
```

## Never do

- Fetch job URLs or use browser for ATS
- Use LLM for scoring or suggestions
- Write columns A–H or K+
- Overwrite existing values in column I (only empty cells)
- Write column J when column I gets the no-skills comment
- Score rows where Status is not `to apply`

## Run JSON fields

```json
{
  "atsscore_status": "complete",
  "atsscore_rows_scored": [27, 28, 29],
  "atsscore_skipped_no_data": [15, 16],
  "resumes_used": ["Backend SWE", "AI/ML"]
}
```

## Completion checklist

1. Resumes checked (or skip documented)
2. Headers I1/J1 confirmed (`ATS score`, `Suggestions on Resume`)
3. `score --all` executed (or `--dry-run` then live)
4. Column **I (ATS score)** written for scored rows; no-data comment for rows without Skills
5. Column **J (Suggestions on Resume)** written for successfully scored rows only
6. Run JSON updated with atsscore fields

## Completion report (merged into Jobgru summary)

- ATS status: complete | skipped (no resumes / disabled)
- Rows scored: row #, company, best ATS score
- Rows skipped — no Skills in Details (column I comment only)
- Resumes used (manifest labels)
