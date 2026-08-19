# Jobgru pipeline run prompt

**One prompt runs all phases:** Jobgru (find jobs → sheet) then LeadGru + ATSScore in parallel automatically.

Copy into Cursor Agent. Fill in the filter fields. Delete the `Note:` line if you do not want an override.

```text
Use the jobgru skill (full pipeline — Phase 1 Jobgru + Phase 2 LeadGru + Phase 2b ATSScore automatic).

Google Sheet (read URL from config/sheet.json → sheet_url):

Target: user-requested count (max 50 verified unique jobs this run).
Stop at 50 committed rows (hard cap).
LinkedIn Jobs: max 25 accepted jobs this run (rate-limit safety).
Other boards: single, multiple, or mix & match — share remaining quota up to 50 total.
Use only one LinkedIn researcher.

Read the sheet first via Sheets API (scripts/sheets_write.py read --range "A2:H500") and build the duplicate index.

Before searching each board, read its runbook from data/board-runbooks/ and follow the Board runbook protocol in the jobgru skill (runbook mode, failure ladder, bounded discovery for stubs).

Launch parallel read-only researchers for:
LinkedIn Jobs, Wellfound, Indeed, YC Jobs, remote-job boards, and company career pages.

Filters:
Role/domain:
Acceptable role variants:
Location:
Remote country/time-zone restriction:
Work arrangement: remote / hybrid / onsite / any
Experience:
Visa sponsorship: required / preferred / irrelevant / exclude
Required skills:
Excluded roles/skills:
Minimum compensation:
Employment type:
Maximum posting age:
Exclude staffing agencies: yes/no
ATS scoring: yes

Researchers must verify full listings and return structured candidates without writing to the sheet.

The coordinator must deduplicate by normalized company + similar role and apply URL (column C, or legacy Apply: in column F), then write rows via scripts/sheets_write.py (Sheets API). Do NOT write via Cursor Browser.

For each new row (columns A–H):
- A Company Name, B Position from listing
- C Apply link = bare direct job/apply URL (plain text, no prefix)
- D Status = to apply
- E Date Applied = today as D/M/YYYY
- F Details = Pay, Exp, Visa, arrangement, location, Posted | Skills: keyword1, keyword2, ... (5–12 from listing, NO apply URL in F)
- G Leads = blank, H Add note Message = blank
- Do not touch existing rows or columns K+

Phase 1 verify: scripts/sheets_write.py read --range "A{start}:H{end}"

═══════════════════════════════════════
PHASE 2 + 2b — LeadGru + ATSScore (parallel, automatic)
═══════════════════════════════════════

Immediately after Phase 1 verify passes, launch both in parallel:

LeadGru — read .cursor/skills/leadgru/SKILL.md, pipeline mode for start_row–end_row:
- LinkedIn people search (one company at a time, Cursor Browser + CDP)
- 4–10 verified /in/ profiles + Company: line per row
- Add note Message from templates Q2–Q7 (rotate); Hi {Name}, → Hi,
- Write G/H via Sheets API: write --range "G{R}:H{R}" --json '[["<leads>", "<note>"]]'

ATSScore — read .cursor/skills/atsscore/SKILL.md (skip if no resumes or ATS scoring: no):
  .venv/bin/python scripts/ats_score.py score --all

After both complete: format-layout, one combined completion report (jobs + leads + ATS)

Do not bypass login, CAPTCHA, or rate limits. Stop LinkedIn on verification challenges and report partial pipeline status.

Do not send LinkedIn messages, InMails, or connection requests.

Note: dont skip if the exp matches
```

## Example filled filters

```text
Role/domain: AI Engineer, Applied AI Engineer, ML Engineer, GenAI Engineer
Acceptable role variants: LLM Engineer, AI Agents Engineer, Software Engineer AI/ML
Location: India or worldwide remote
Work arrangement: remote, hybrid Bangalore, onsite Bangalore
Experience: 1–3 years
Visa sponsorship: irrelevant for India roles
Required skills: Python, LLMs, agents, backend or ML
Excluded roles: data annotation, sales, internships, 5+ years senior
Maximum posting age: 30 days
Exclude staffing agencies: yes
ATS scoring: yes
Note: include similar-domain titles when the description matches
```
