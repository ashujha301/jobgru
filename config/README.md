# Sheet configuration

Created automatically by **Jobgru setup** — users do not edit this manually.

## New users

1. Copy the [starter template](https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit) → File → Make a copy
2. Chat: **Jobgru setup** with your sheet URL ([prompts/setup.md](../prompts/setup.md))
3. Terminal: `gcloud auth login --enable-gdrive-access --update-adc`
4. Chat: **Jobgru check**

## Agent writes config

```bash
.venv/bin/python scripts/sheet_config.py set --url "https://docs.google.com/spreadsheets/d/..." --name "Your Name"
```

## Shareable starter template

https://docs.google.com/spreadsheets/d/18TQRl1dh0Ivdk8YbxkdiWb6__XkpHM32T1ohPTuMJ_4/edit

Share as **Viewer** → others **File → Make a copy** → **Jobgru setup** with their copy URL.

Regenerate (maintainers): `.venv/bin/python scripts/init_template_sheet.py`
