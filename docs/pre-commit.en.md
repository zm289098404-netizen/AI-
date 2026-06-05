# pre-commit Hooks Guide

[中文](pre-commit.md) | **English**

This project uses [pre-commit](https://pre-commit.com) to run checks automatically before each
`git commit`, ensuring code quality and preventing accidental commits of sensitive data.

## Install
```bash
pip install pre-commit          # or: pip install -r requirements-dev.txt
pre-commit install              # install the hook into .git/hooks
```

## Included Checks
Config file: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml)

| Hook | Purpose |
|------|---------|
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with a single newline |
| `check-yaml` | Validate YAML syntax |
| `check-json` | Validate JSON syntax |
| `check-added-large-files` | Block files larger than 1MB |
| `detect-private-key` | Detect accidentally committed private keys |
| `check-merge-conflict` | Detect leftover merge-conflict markers |
| `pytest-unit` (local) | Run `pytest -q` unit tests (48 tests, Mock mode) |

## Usage
- After installation, `git commit` triggers the checks automatically; **any failure blocks the commit**.
- Some hooks (e.g. trailing-whitespace) auto-fix files; re-`git add` and commit again afterwards.

## Common Commands
```bash
pre-commit run --all-files      # run once across all files
pre-commit run pytest-unit      # run only the unit-test hook
pre-commit autoupdate           # upgrade hook versions
SKIP=pytest-unit git commit ... # temporarily skip one hook (not recommended)
git commit --no-verify ...      # skip all hooks (emergencies only)
```

## Notes
- `pytest-unit` uses `language: system` and relies on a locally installed Python and pytest
  (`pip install -r requirements-dev.txt`).
- **Activate your virtual environment before committing** (`.\.venv\Scripts\Activate.ps1` or
  `source .venv/bin/activate`) so that `python -m pytest` uses the interpreter with dependencies installed.
- Unit tests redirect data paths to a temp directory via `tests/conftest.py`, so they do not
  pollute local data.
