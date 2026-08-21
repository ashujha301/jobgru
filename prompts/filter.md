# Jobgru filter

```text
Jobgru filter
```

Lists every filter type you can use in a job-search prompt — plain-English names with **e.g.** examples.

Run limits: **no sheet row cap**; this run uses your **Count**; **LinkedIn has no job-count cap**; LeadGru **5 people + company people page**.

Terminal:

```bash
jobgru filter
jobgru prompts
```

GitHub template: [jobgru-run.md](https://github.com/ashujha301/jobgru/blob/main/prompts/jobgru-run.md)

---

## Example prompt (all filters filled)

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

Blank template with every filter: `jobgru prompts --which template`
