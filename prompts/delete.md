# Jobgru delete rows

```text
Jobgru delete rows 42-44
```

Also works: `42`, `42,43,44`, or `42,44-46`.

Agent previews with `--dry-run`, confirms with you, then deletes. Rows below shift up automatically.

Terminal:

```bash
jobgru delete --rows 42-44 --dry-run
jobgru delete --rows 42-44
```
