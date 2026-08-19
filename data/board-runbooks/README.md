# Board runbooks

JSON navigation recipes for Jobgru Phase 1. Read before searching a job board — do not rediscover filters each pass.

| File | Board | Status |
| --- | --- | --- |
| `linkedin-jobs.json` | LinkedIn Jobs | active |
| `wellfound.json` | Wellfound | active |
| `indeed.json` | Indeed | discovery needed |
| `yc-jobs.json` | YC / Work at a Startup | discovery needed |

## How agents use these

1. Read runbook for each board in the user prompt.
2. **Active runbook:** open `search_urls[0]`, run `extract_js` via CDP. First search = health check.
3. **Links >= min_links:** rotate remaining URLs (max 3–4 per board), verify finalists only.
4. **Links < min_links:** try `fallback_urls` → bounded discovery → patch this JSON on success.
5. **no_runbook_yet:** bounded discovery (max 5 navigates), write runbook on success.

Only patch JSON runbooks on failure or first discovery — never rewrite `.cursor/skills/jobgru/SKILL.md` automatically.

See `.cursor/skills/jobgru/SKILL.md` → Board runbook protocol.
