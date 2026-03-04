# CI Evidence Instructions — Module 5

## Workflow file locations

Two copies of the same workflow exist:

| File | Purpose |
|---|---|
| `module_5/.github/workflows/ci.yml` | **Rubric artifact** — lives inside module_5/ |
| `.github/workflows/module5-ci.yml` | **Executed by GitHub** — at repo root where GitHub reads workflows |

GitHub Actions only triggers workflows from `.github/workflows/` at the repository root.
The repo-root copy (`module5-ci.yml`) is what produces the real successful run you need to screenshot.

---

## Steps to get the CI screenshot

### 1. Commit all Task 1–3 changes

```powershell
cd C:\Users\Owner\projects\jhu_software_concepts

git add module_5/sql/least_privilege.sql
git add module_5/evidence/least-privilege-psql.txt
git add module_5/SECURITY_NOTES.md
git add module_5/packaging_notes.md
git add module_5/.github/workflows/ci.yml
git add .github/workflows/module5-ci.yml
git add module_5/ci_evidence_instructions.md

git commit -m "Add least-privilege DB role SQL and security notes"
# (adjust commit message as preferred)
```

### 2. Push to GitHub

```powershell
git push origin main
```

### 3. Open GitHub Actions

1. Go to your repository on GitHub: `https://github.com/<your-username>/jhu_software_concepts`
2. Click the **Actions** tab (top navigation bar)
3. In the left sidebar, find **"Module 5 CI"** under "All workflows"
4. Click the most recent run triggered by your push

### 4. Verify the run succeeds

The run must show all steps green:
- ✅ Check out repository
- ✅ Set up Python 3.11
- ✅ Install dependencies
- ✅ **Lint (pylint — must score 10.00/10)**
- ✅ **Test (pytest — must pass all 99 tests)**

If any step fails, click it to expand the log, fix the issue, and re-push.

### 5. Take the screenshot

Once all steps show green checkmarks:
1. Take a **full screenshot** of the Actions run page showing the green status
2. Save the file as:

   ```
   module_5/ci-success.png
   ```

### 6. Commit and push the screenshot

```powershell
git add module_5/ci-success.png
git commit -m "Add Module 5 CI success screenshot"
git push origin main
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Workflow not visible in Actions | File not at repo root `.github/workflows/` | Check `.github/workflows/module5-ci.yml` exists at repo root |
| Workflow not triggered on push | `paths:` filter mismatch | Push a change to any file under `module_5/` |
| `ModuleNotFoundError: src` | `pip install -e module_5/` failed | Check setup.py `packages=["src"]` |
| `pytest: DATABASE_URL not set` | Env var not injected into job | Check `env:` block in module5-ci.yml |
| pylint score < 10.00 | Code change in src/ | Run `.venv\Scripts\python.exe -m pylint src` locally |
| Schema creation fails | DB user lacks CREATE SCHEMA | Confirm `POSTGRES_USER: postgres` in workflow |

---

## Required evidence file

Screenshot must be saved as: **`module_5/ci-success.png`**

Do not use `actions_success.png` (that is from an earlier module's CI run).
