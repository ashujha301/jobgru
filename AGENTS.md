# Jobgru — agent instructions

Portable skills in `.cursor/skills/`. Install globally with [install.sh](install.sh) for `/jobgru` in any chat.

## Install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
jobgru mcp install
cp resume.pdf ~/.jobgru/data/resumes/
jobgru check
```

Engine: `~/.jobgru` · Router skills: `~/.cursor/skills/jobgru/`, `~/.claude/skills/jobgru/`, `~/.codex/skills/jobgru/`

## Chat commands

| Command | Action |
| --- | --- |
| `Jobgru setup` + sheet URL | [jobgru-setup/SKILL.md](.cursor/skills/jobgru-setup/SKILL.md) |
| `Jobgru help` | Full command list (`jobgru help`) |
| `Jobgru check` | `jobgru check` |
| `Jobgru mcp` | Playwright MCP for Claude/Codex |
| `Jobgru filter` | List filter types for prompts |
| `Jobgru prompts` | Example prompts to copy, edit, paste |
| `Jobgru delete` | Delete sheet rows |
| Job search | [jobgru/SKILL.md](.cursor/skills/jobgru/SKILL.md) |

## Manual terminal (user only)

```bash
gcloud auth login --enable-gdrive-access --update-adc
```

## Platform notes

| Agent | Skills | Browser |
| --- | --- | --- |
| **Cursor** | Auto-discovers `~/.cursor/skills/jobgru/` | Cursor Browser (built-in) |
| **Claude Code** | `~/.claude/skills/jobgru/` | `jobgru mcp install` → Playwright |
| **Codex** | `~/.codex/skills/jobgru/` | `jobgru mcp install` → Playwright |
| **Repo mode** | `.cursor/skills/` in project | Per agent |

## Skill index

| Skill | Path |
| --- | --- |
| Global router | [skill-global/jobgru/SKILL.md](skill-global/jobgru/SKILL.md) |
| Setup / help / check / filter / delete / mcp | `.cursor/skills/jobgru-setup/SKILL.md` |
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
