# Jobgru — example prompt

Copy the template below, edit the values, paste into chat.

**One prompt runs the full pipeline:** find jobs → write sheet → LinkedIn leads → ATS scores.

Terminal: `jobgru prompts` · Filter catalog: `jobgru filter`

GitHub: https://github.com/ashujha301/jobgru/blob/main/prompts/jobgru-run.md

Limits: **50 jobs max per run**, **25 max from LinkedIn**.

---

## Template (edit and paste)

Every filter — leave a line blank if you do not care.

```text
Jobgru

Count:
Boards:
Roles:
Similar roles:
Location:
Remote restriction:
Work:
Experience:
Visa sponsorship:
Skills:
Exclude:
Minimum compensation:
Employment type:
Posting age:
Staffing agencies: no
ATS scoring: yes
Note:
```

**On/off fields:** `Staffing agencies` and `ATS scoring` — use `yes` or `no`.

| Filter | Line in template |
| --- | --- |
| Target / count | Count |
| Job boards / sources | Boards |
| Role / domain | Roles |
| Acceptable role variants | Similar roles |
| Location | Location |
| Remote country / time zone | Remote restriction |
| Work arrangement | Work |
| Experience | Experience |
| Visa sponsorship | Visa sponsorship |
| Required skills | Skills |
| Excluded roles | Exclude |
| Minimum compensation | Minimum compensation |
| Employment type | Employment type |
| Maximum posting age | Posting age |
| Exclude staffing agencies | Staffing agencies |
| ATS scoring | ATS scoring |
| Extra instructions | Note |

---

## Example — LinkedIn SWE in Bangalore

```text
Jobgru

Count: 3
Boards: LinkedIn
Roles: Software Engineer, SWE AI
Similar roles: include Full Stack if backend stack matches
Location: Bangalore
Remote restriction: India only
Work: hybrid or onsite
Experience: 0–4 years
Visa sponsorship: irrelevant
Skills: Python, FastAPI
Exclude: Data Scientist, Data Engineer
Minimum compensation: not required
Employment type: full-time only
Posting age: 30 days
Staffing agencies: no
ATS scoring: yes
Note: don't skip if experience matches for similar roles
```

---

## Even shorter (natural language)

You do not need the template — plain English works if setup is done:

```text
Find 3 software engineer jobs on LinkedIn in Bangalore. Exclude Data Scientist. Run ATS scoring.
```

Use `jobgru filter` when you want descriptions and e.g. values for each filter.
