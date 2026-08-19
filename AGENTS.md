# Jobgru — agent instructions

Portable skills in `.cursor/skills/`. Install globally with [install.sh](install.sh) for `/jobgru` in any chat.

## Install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

Engine: `~/.jobgru` · Router skills: `~/.cursor/skills/jobgru/`, `~/.claude/skills/jobgru/`, `~/.codex/skills/jobgru/`

## Chat commands

| Command | Action |
| --- | --- |
| `Jobgru setup` + sheet URL | [jobgru-setup/SKILL.md](.cursor/skills/jobgru-setup/SKILL.md) |
| `Jobgru help` | help mode |
| `Jobgru check` | `jobgru check` or `scripts/jobgru_check.py --json` |
| Job search | [jobgru/SKILL.md](.cursor/skills/jobgru/SKILL.md) |

## Manual terminal (user only)

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

## Platform notes

| Agent | Skills | Browser |
| --- | --- | --- |
| **Cursor** | Auto-discovers `~/.cursor/skills/jobgru/` | Cursor Browser |
| **Claude Code** | `~/.claude/skills/jobgru/` | Playwright MCP |
| **Codex** | `~/.codex/skills/jobgru/` | Playwright MCP |
| **Repo mode** | `.cursor/skills/` in project | Per agent |

## Skill index

| Skill | Path |
| --- | --- |
| Global router | [skill-global/jobgru/SKILL.md](skill-global/jobgru/SKILL.md) |
| Setup / help / check | `.cursor/skills/jobgru-setup/SKILL.md` |
| Phase 1 | `.cursor/skills/jobgru/SKILL.md` |
| Phase 2 | `.cursor/skills/leadgru/SKILL.md` |
| Phase 2b | `.cursor/skills/atsscore/SKILL.md` |

## Health check

```bash
jobgru check
# or
~/.jobgru/.venv/bin/python ~/.jobgru/scripts/jobgru_check.py --json
```

Exit `0` = ready for pipeline.
