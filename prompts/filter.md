# Jobgru filter

```text
Jobgru filter
```

Lists every filter type you can use in a job-search prompt — plain-English names with **e.g.** examples.

Run limits: **50 jobs max per run**, **25 max from LinkedIn**.

Terminal:

```bash
jobgru filter
jobgru filters
```

---

## Example prompt (copy and edit)

Full template: [jobgru-run.md](jobgru-run.md)

```text
Jobgru

Count: 3
Boards: LinkedIn
Roles: Software Engineer, SWE AI
Similar roles: include Full Stack if backend stack matches
Location: Bangalore
Work: hybrid or onsite
Experience: 0–4 years
Skills: Python, FastAPI
Exclude: Data Scientist, Data Engineer
Posting age: 30 days
Staffing agencies: no
ATS scoring: yes
Note: don't skip if experience matches for similar roles
```

Edit the values you care about. Leave lines blank if a filter does not matter.
