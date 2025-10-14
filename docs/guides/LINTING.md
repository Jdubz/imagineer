# Linting and Code Quality

This document describes the linting setup and git hooks for maintaining code quality in the Imagineer project.

## Overview

Imagineer uses automatic linting and testing via git hooks:

- **Pre-commit hook**: Lints staged files before commit
- **Pre-push hook**: Runs tests on changed code before push

The hooks are smart and only check/test the files you've actually changed (backend or frontend).

---

## Quick Start

### Install Git Hooks

```bash
make install-hooks
```

This installs two git hooks:
- `.git/hooks/pre-commit` - Lints staged files
- `.git/hooks/pre-push` - Runs tests for changed code

### Manual Linting

```bash
# Lint everything
make lint

# Lint backend only
make lint-backend

# Lint frontend only
make lint-frontend

# Auto-fix all linting issues
make lint-fix
```

---

## Backend Linting (Python)

### Tools

- **Black**: Code formatter (opinionated, no config needed)
- **Flake8**: Style guide enforcement
- **Isort**: Import sorting

### Configuration

**`pyproject.toml`**: Black and isort settings
```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100
```

**`.flake8`**: Flake8 settings
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
max-complexity = 10
```

### Running Manually

```bash
source venv/bin/activate

# Check formatting
black --check .

# Auto-format
black .

# Check style
flake8 .

# Sort imports
isort .
```

---

## Frontend Linting (JavaScript/React)

### Tools

- **ESLint**: JavaScript/React linting

### Configuration

**`web/eslint.config.js`**: ESLint settings with React rules

### Running Manually

```bash
cd web

# Check linting
npm run lint

# Auto-fix
npm run lint:fix
```

---

## Git Hooks

### Pre-Commit Hook

**What it does**: Lints only the files you're committing

**Files checked**:
- Python files (`.py`) outside of `web/`
- JavaScript files (`.js`, `.jsx`) inside `web/`

**Example output**:
```
🔍 Running pre-commit checks...

🐍 Linting Python files...
would reformat server/api.py
Oh no! 💥 💔 💥
1 file would be reformatted, 2 files would be left unchanged.
❌ Black failed. Auto-fix with: black .

❌ Pre-commit checks failed
```

**Skip if needed**:
```bash
git commit --no-verify -m "message"
```

### Pre-Push Hook

**What it does**: Runs tests only for changed code

**Logic**:
- Changed Python files? → Run backend tests
- Changed JavaScript files? → Run frontend tests
- Changed both? → Run both test suites

**Example output**:
```
🧪 Running pre-push tests...

🐍 Running backend tests...
===== test session starts =====
tests/backend/test_api.py::TestHealthEndpoint::test_health_check PASSED
...
===== 50 passed in 2.34s =====

✅ All tests passed!
```

**Skip if needed**:
```bash
git push --no-verify
```

---

## Common Workflows

### First Time Setup

```bash
# 1. Install dependencies
make install
make install-web

# 2. Install git hooks
make install-hooks

# 3. Verify everything works
make lint
make test
```

### Before Committing

```bash
# Option 1: Let the pre-commit hook catch issues
git add .
git commit -m "Your message"  # Hook runs automatically

# Option 2: Fix issues before committing
make lint-fix  # Auto-fix linting issues
git add .
git commit -m "Your message"
```

### Fixing Linting Errors

**Backend:**
```bash
# Auto-fix formatting and imports
black .
isort .

# Check remaining issues
flake8 .
```

**Frontend:**
```bash
cd web
npm run lint:fix
```

---

## Hook Behavior Examples

### Example 1: Commit Python file

```bash
$ git add server/api.py
$ git commit -m "Update API"

🔍 Running pre-commit checks...

🐍 Linting Python files...
All done! ✨ 🍰 ✨
1 file passed

✅ All checks passed!

[develop abc1234] Update API
 1 file changed, 10 insertions(+)
```

### Example 2: Commit JavaScript file

```bash
$ git add web/src/App.jsx
$ git commit -m "Update UI"

🔍 Running pre-commit checks...

⚛️  Linting JavaScript files...

✅ All checks passed!

[develop def5678] Update UI
 1 file changed, 5 insertions(+)
```

### Example 3: Push with Python changes

```bash
$ git push

🧪 Running pre-push tests...

🐍 Running backend tests...
===== test session starts =====
...
===== 50 passed in 2.34s =====

✅ All tests passed!

Enumerating objects...
```

---

## Troubleshooting

### "Black failed"

```bash
# See what would change
black --diff .

# Apply changes
black .

# Stage and retry
git add .
git commit -m "message"
```

### "Flake8 failed"

Check the specific errors and fix manually. Common issues:
- Line too long → Break into multiple lines
- Unused import → Remove it
- Undefined name → Import the module

### "ESLint failed"

```bash
cd web

# See errors
npm run lint

# Auto-fix
npm run lint:fix

# Some errors need manual fixing
```

### Hook not running

```bash
# Verify hooks exist
ls -la .git/hooks/

# Reinstall if missing
make install-hooks

# Check hook is executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

### Want to skip hooks

```bash
# Skip pre-commit
git commit --no-verify

# Skip pre-push
git push --no-verify

# Note: Only skip when absolutely necessary!
```

---

## IDE Integration

### VS Code

**.vscode/settings.json**:
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Settings → Tools → Black → Enable
2. Settings → Tools → External Tools → Add Flake8
3. Settings → Editor → Code Style → Python → Set line length to 100

---

## Best Practices

1. **Run lint-fix before committing**
   ```bash
   make lint-fix
   ```

2. **Don't skip hooks** unless absolutely necessary

3. **Fix linting errors immediately** - Don't let them accumulate

4. **Use auto-formatting** - Let black and eslint handle formatting

5. **Keep hooks fast** - Only changed files are checked

---

**Last Updated:** October 13, 2025
