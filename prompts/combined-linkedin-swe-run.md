# Jobgru pipeline — LinkedIn only (SWE / Backend / AI)

Copy the block below into Cursor Agent. **One prompt** runs the full pipeline: 5 LinkedIn jobs → automatic LeadGru + ATSScore for those rows.

```text
Use the jobgru skill (full pipeline — Phase 1 Jobgru + Phase 2 LeadGru + Phase 2b ATSScore automatic).
Also read .cursor/skills/leadgru/SKILL.md and .cursor/skills/atsscore/SKILL.md before Phase 2.

Google Sheet (read URL from config/sheet.json → sheet_url):

═══════════════════════════════════════
PHASE 1 — Jobgru (LinkedIn Jobs ONLY)
═══════════════════════════════════════

Target: exactly 5 verified unique jobs (stop at 5 unless more strong matches are trivial).
Search ONLY LinkedIn Jobs — one researcher. Do NOT search Wellfound, Indeed, YC, Glassdoor, remote boards, or company career pages.

Read data/board-runbooks/linkedin-jobs.json and follow the Board runbook protocol in the jobgru skill (runbook mode, failure ladder).

Read sheet first and build duplicate index:
  .venv/bin/python scripts/sheets_write.py read --range "A2:H500"

Filters:
Role/domain: Software Engineer, Backend Engineer, Backend AI Engineer, SWE AI, Software Engineer AI/ML
Acceptable role variants: Full Stack Engineer (AI/backend focus), Platform Engineer (AI), Backend Developer, Software Engineer II/III with AI/ML, Founding Backend Engineer, API Engineer with LLM/agents
Location: India or worldwide remote (India-friendly time zones)
Work arrangement: remote, hybrid Bangalore, onsite Bangalore
Experience: 1–3 years (include Associate / Mid-level)
Visa sponsorship: irrelevant for India roles
Required skills: Python and/or Node/Go/Java backend; building APIs, services, or platforms; AI/ML integration is a plus not required for pure backend SWE
Excluded roles: data annotation, QA-only, sales, internships, DevOps/SRE-only, 5+ years senior/staff, frontend-only
Maximum posting age: 30 days
Exclude staffing agencies: yes
ATS scoring: yes

Note: dont skip if the exp matches

Researchers must verify FULL job listings (not snippets) and must NOT write to the sheet.

Coordinator writes via Sheets API only (never Cursor Browser for cells):
  .venv/bin/python scripts/sheets_write.py first-empty
  .venv/bin/python scripts/sheets_write.py append --file data/runs/pending-rows-<date>.json --start-row <N>
  .venv/bin/python scripts/sheets_write.py read --range "A<N>:H<N+4>"  # verify 5 rows

New row columns A–H:
- A Company, B Position, C Apply link (bare LinkedIn job URL), D to apply, E today D/M/YYYY
- F Details: Pay: ..., Exp: ..., Visa: ..., Remote|Hybrid|Onsite, location, Posted: ... | Skills: ... (NO URL in F)
- G Leads blank, H Add note Message blank

Save run summary: data/runs/<YYYY-MM-DD-HHMM>.json (updated again after Phase 2)

═══════════════════════════════════════
PHASE 2 + 2b — LeadGru + ATSScore (parallel — do not stop or ask user)
═══════════════════════════════════════

Immediately after Phase 1 verify passes, launch both in parallel:

LeadGru (start_row–end_row only):
  .venv/bin/python scripts/sheets_write.py read --range "Q1:Q7"

For each new row in range where Status is "to apply" and Leads (G) is empty:
- LinkedIn people search in Cursor Browser (one company at a time) — follow leadgru skill runbook
- 4–10 verified /in/ profiles + Company: linkedin.com/company/... line
- Fill Add note Message from templates Q2–Q7 (rotate); replace {Position}, {Company}, {Link}; Hi {Name}, → Hi,
- Write via Sheets API:
    .venv/bin/python scripts/sheets_write.py write --range "G{R}:H{R}" --json '[["<leads>", "<note>"]]'

ATSScore (parallel — skip if no resumes in data/resumes/ or ATS scoring: no):
  .venv/bin/python scripts/ats_score.py score --all

After both complete:
  .venv/bin/python scripts/sheets_write.py read --range "A<start>:J<end>"
  .venv/bin/python scripts/sheets_write.py format-layout

Do not send LinkedIn messages, InMails, or connection requests.
Stop and report CAPTCHA, login, or rate-limit warnings (mark pipeline partial, list unprocessed rows).

Combined completion report: 5 jobs + 5 LeadGru rows + ATS scores + pipeline status + sheet link.
```
