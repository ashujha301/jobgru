# Jobgru setup

Copy into any coding agent (Cursor, Claude Code, Codex, etc.):

```text
Jobgru setup — I copied the template. My sheet: <PASTE YOUR GOOGLE SHEET URL>. My name: <YOUR NAME>. Resume link: <YOUR PUBLIC RESUME URL optional>
```

Attach your resume PDF in the same message if you want ATS scoring enabled.

After the agent finishes, run this **once** in your terminal (sheet owner Google account):

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

Then say: **Jobgru check**
