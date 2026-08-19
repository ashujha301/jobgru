# Jobgru + LeadGru + ATSScore pipeline (default)

**Single prompt → full pipeline.** Phase 2 (LeadGru) and Phase 2b (ATSScore) run automatically in parallel after jobs are written. No second prompt needed.

For LinkedIn-only SWE/backend presets, see [combined-linkedin-swe-run.md](combined-linkedin-swe-run.md).

For backfill: [leadgru-run.md](leadgru-run.md) (leads) or [atsscore-run.md](atsscore-run.md) (ATS scores).

```text
Use the jobgru skill (full pipeline — Phase 1 + Phase 2 LeadGru + Phase 2b ATSScore automatic).

Google Sheet (read URL from config/sheet.json → sheet_url):

Phase 1 — Jobgru: find up to 50 verified unique jobs (LinkedIn max 25), dedupe, append via Sheets API.
  Details (F) must include | Skills: keyword1, keyword2, ... (5–12 from listing)

Phase 2 — LeadGru + Phase 2b ATSScore (parallel, automatic):
  LeadGru: fill Leads (G) + Add note Message (H) for new rows
  ATSScore: .venv/bin/python scripts/ats_score.py score --all (fills I/J; backfills all to apply with empty ATS)

Before searching each board, read its runbook from data/board-runbooks/ and follow the Board runbook protocol in the jobgru skill.

Do not stop after Phase 1. Do not ask the user to run LeadGru or ATSScore separately.

Filters:
Role/domain:
Acceptable role variants:
Location:
Work arrangement:
Experience:
Visa sponsorship:
Required skills:
Excluded roles:
Maximum posting age:
Exclude staffing agencies:
ATS scoring: yes

Boards: LinkedIn Jobs, Wellfound, Indeed, YC Jobs, remote boards, company career pages
(one LinkedIn researcher only for Jobgru)

Note: dont skip if the exp matches

After all phases: format-layout, combined completion report, save data/runs/<timestamp>.json
```
