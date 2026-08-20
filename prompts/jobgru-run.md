# Jobgru — example prompt

Copy the template below, edit the values, paste into chat.

**One prompt runs the full pipeline:** find jobs → write sheet → LinkedIn leads → ATS scores.

See every filter type: `jobgru filter` or **Jobgru filter** in chat.

Limits: **50 jobs max per run**, **25 max from LinkedIn**.

---

## Template (edit and paste)

```text
Jobgru

Count:
Boards:
Roles:
Similar roles:
Location:
Work:
Experience:
Skills:
Exclude:
Posting age:
Staffing agencies: no
ATS scoring: yes
Note:
```

**On/off fields:** `Staffing agencies` and `ATS scoring` — use `yes` or `no`. Leave a line blank if you do not care.

---

## Example — LinkedIn SWE in Bangalore

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

---

## Even shorter (natural language)

You do not need the template — plain English works if setup is done:

```text
Find 3 software engineer jobs on LinkedIn in Bangalore. Exclude Data Scientist. Run ATS scoring.
```

Use `jobgru filter` when you want to see all filter types before writing a prompt.
