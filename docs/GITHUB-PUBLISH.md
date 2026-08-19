# Publish to GitHub (ashujha301)

Ensure the CLI is authenticated as **ashujha301**:

```bash
gh auth status   # must show ashujha301 as active
```

## 1. Create private repo and push

From this project root (after tests pass):

```bash
git remote remove origin 2>/dev/null || true
gh repo create ashujha301/jobgru --private --source . --remote origin --push
```

## 3. Verify CI

Open https://github.com/ashujha301/jobgru/actions — **Validate Jobgru installer** should pass on `main`.

## 4. Users install

```bash
curl -fsSL https://raw.githubusercontent.com/ashujha301/jobgru/main/install.sh | bash
```

Private repo: users need git read access, or make the repo public later.

## 5. Update installed copies

After each push to `main`:

```bash
jobgru update
```
