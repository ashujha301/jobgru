# Board runbooks

JSON navigation recipes for Jobgru Phase 1. Read before searching a job board — do not rediscover filters each pass.

| File | Board | Focus | Status |
| --- | --- | --- | --- |
| `linkedin-jobs.json` | LinkedIn Jobs | All roles, all locations | active |
| `wellfound.json` | Wellfound | Startups | active |
| `remote-rocketship.json` | Remote Rocketship | Remote (aggregator, 190k+ jobs) | active |
| `dailyremote.json` | DailyRemote | Remote (fresh 24h listings) | active |
| `remoteok.json` | RemoteOK | Remote (high volume, salary tags) | active |
| `weworkremotely.json` | We Work Remotely | Remote (largest dedicated board) | active |
| `remotive.json` | Remotive | Remote (curated tech/startup) | active |
| `himalayas.json` | Himalayas | Remote (salary + country eligibility) | discovery needed (browser only — Cloudflare) |
| `working-nomads.json` | Working Nomads | Remote (nomad/region browse) | discovery needed |
| `indeed.json` | Indeed | All roles (country domains) | discovery needed (browser only — anti-bot) |
| `yc-jobs.json` | YC / Work at a Startup | Startups | discovery needed |

## How agents use these

1. Read runbook for each board in the user prompt.
2. **Active runbook:** open `search_urls[0]`, run `extract_js` via CDP. First search = health check.
3. **Links >= min_links:** rotate remaining URLs (max 3–4 per board), verify finalists only.
4. **Links < min_links:** try `fallback_urls` → bounded discovery → patch this JSON on success.
5. **no_runbook_yet:** bounded discovery (max 5 navigates), write runbook on success.

Boards marked `verify: browser_listing` block WebFetch — verify finalists with browser tools only.

Only patch JSON runbooks on failure or first discovery — never rewrite `.cursor/skills/jobgru/SKILL.md` automatically.

See `.cursor/skills/jobgru/SKILL.md` → Board runbook protocol.
