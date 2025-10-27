# Git Hooks for Code Quality

This project includes pre-push Git hooks to ensure code quality before any code is pushed to the repository.

## Overview

The pre-push hook automatically runs the following checks before allowing any push:

- **Black formatting check** - Ensures code follows consistent formatting
- **isort import sorting check** - Ensures imports are properly sorted
- **Flake8 linting check** - Catches common Python code issues
- **Optional pytest tests** - Can be enabled to run tests before push

## Installation

### Automatic Installation

Run the setup script from the project root:

```bash
./scripts/setup-git-hooks.sh
```

### Manual Installation

Copy the hook file to the Git hooks directory:

```bash
cp scripts/pre-push-hook .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Usage

The hook runs automatically on every `git push`. If any check fails, the push will be blocked until the issues are fixed.

### Basic Usage

```bash
git push  # Hook runs automatically
```

### With Test Checks

To run tests before push (slower but more thorough):

```bash
RUN_TESTS=true git push
```

### Quick Test Checks

To run only critical tests (faster):

```bash
QUICK_CHECK=true RUN_TESTS=true git push
```

### Bypassing the Hook

If you need to bypass the hook (not recommended):

```bash
git push --no-verify
```

## Configuration

The hook can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_TESTS` | `false` | Set to `true` to run pytest tests before push |
| `QUICK_CHECK` | `false` | Set to `true` to run only critical tests (faster) |

## What Gets Checked

### Black Formatting
- Code formatting consistency
- Line length and spacing
- Quote style consistency

### isort Import Sorting
- Import statement ordering
- Grouping of standard library, third-party, and local imports
- Alphabetical sorting within groups

### Flake8 Linting
- Unused imports and variables
- Code complexity
- Style violations
- Potential bugs

### Pytest Tests (Optional)
- Unit tests for all modules
- Integration tests
- API endpoint tests

## Fixing Issues

When the hook fails, it will show you exactly what needs to be fixed:

### Formatting Issues
```bash
black server/ src/ examples/
git add .
git commit -m "Fix Black formatting"
```

### Import Sorting Issues
```bash
isort server/ src/ examples/
git add .
git commit -m "Fix import sorting"
```

### Linting Issues
Fix the specific issues shown in the output, then:
```bash
git add .
git commit -m "Fix linting errors"
```

### Test Failures
Fix the failing tests, then:
```bash
git add .
git commit -m "Fix test failures"
```

## Benefits

- **Prevents bad code from being pushed** - Catches issues before they reach the repository
- **Enforces consistent code style** - All team members follow the same formatting rules
- **Reduces CI/CD failures** - Most issues are caught locally before reaching GitHub Actions
- **Improves code quality** - Encourages good coding practices
- **Saves time** - Fixes issues locally instead of waiting for CI/CD feedback

## Troubleshooting

### Hook Not Running
- Ensure the hook file is executable: `chmod +x .git/hooks/pre-push`
- Check that you're in a Git repository: `git status`

### Virtual Environment Issues
- Activate your virtual environment: `source venv/bin/activate`
- Ensure required tools are installed: `pip install black isort flake8 pytest`

### Permission Issues
- Make sure the hook file is executable: `chmod +x .git/hooks/pre-push`
- Check file ownership if on a shared system

## Customization

To modify the hook behavior, edit `scripts/pre-push-hook` and reinstall:

```bash
cp scripts/pre-push-hook .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Common customizations:
- Add more linting tools (mypy, bandit, etc.)
- Change test selection criteria
- Add custom checks for your project
- Modify error messages and formatting