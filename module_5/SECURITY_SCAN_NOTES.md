# Security Scan Notes — Snyk Dependency Vulnerability Analysis

## Overview

[Snyk](https://snyk.io) scans Python projects for known CVEs (Common Vulnerabilities and
Exposures) in open-source dependencies listed in `requirements.txt`.  Two scan modes are
available:

| Command | What it scans |
|---|---|
| `snyk test` | Open-source dependency vulnerabilities (SCA) |
| `snyk code test` | Source code for security anti-patterns (SAST) |

---

## Installation

Snyk CLI requires Node.js ≥ 18 and npm.

```powershell
# Install Snyk CLI globally
npm install -g snyk

# Verify installation
snyk --version
```

On Windows, `snyk` may not be on the default PATH for Git Bash / WSL.
Use the full path if needed:

```
C:\Users\<your-username>\AppData\Roaming\npm\snyk --version
```

---

## Authentication

A free Snyk account is required.

```powershell
snyk auth
```

This opens a browser window.  Log in (or create a free account at https://app.snyk.io/login)
and click **Authenticate**.  The CLI stores the OAuth token locally.

---

## Running the Dependency Scan

From the `module_5/` directory (where `requirements.txt` lives):

```powershell
snyk test --file=requirements.txt --package-manager=pip
```

Snyk resolves the declared packages, queries the vulnerability database, and prints a report
grouped by severity: **Critical**, **High**, **Medium**, **Low**.

### Example output (condensed)

```
Testing requirements.txt...

✔ Tested 10 dependencies for known issues, no vulnerable paths found.
```

or, if vulnerabilities are found:

```
✗ High severity vulnerability found in Flask
  Description: ...
  Info: https://snyk.io/vuln/SNYK-PYTHON-FLASK-XXXXXXX
  Introduced through: Flask@3.x.x
  Fix: Upgrade to Flask@3.x.y
```

---

## Interpreting Results

| Severity | Meaning | Recommended action |
|---|---|---|
| **Critical** | Remote code execution / data breach risk | Upgrade immediately |
| **High** | Significant exploit potential | Upgrade within 1 sprint |
| **Medium** | Exploitable under specific conditions | Track and plan upgrade |
| **Low** | Minimal exploitability | Upgrade at next maintenance window |

---

## Saving Evidence

After running `snyk test`, take a screenshot of the full terminal output and save it as:

```
module_5/snyk-analysis.png
```

This file is the grading evidence for Step 6.

---

## Optional: SAST Scan

```powershell
snyk code test
```

Snyk Code analyses the Python source files for security anti-patterns (e.g., SQL injection
surface, hardcoded secrets, insecure deserialization).  It requires Snyk Code to be enabled
on your account (free tier supports it).

---

## Notes on This Run

Snyk CLI v1.1302.1 was installed via `npm install -g snyk` on 2026-02-23.

The automated `snyk test --file=requirements.txt` attempt during implementation returned:

```
ERROR   Unspecified Error (SNYK-CLI-0000)
Failed to test pip project
```

This is an **authentication error** — no API token was configured in this environment.
The scan must be run manually after `snyk auth` completes in the user's own shell.
Replace `snyk-analysis.png` with the real terminal screenshot once the scan succeeds.

If snyk test --file=requirements.txt --package-manager=pip returns SNYK-CLI-0000, run snyk test from the project root after upgrading pip/setuptools/wheel.