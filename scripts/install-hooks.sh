#!/bin/bash
# Install git hooks

set -e

HOOK_DIR=".git/hooks"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "📦 Installing git hooks..."

# Pre-commit hook
cat > "$PROJECT_ROOT/$HOOK_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook: Lint only staged files

echo "🔍 Running pre-commit checks..."

STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=d | grep '\.py$' | grep -v '^web/' || true)
STAGED_JS_FILES=$(git diff --cached --name-only --diff-filter=d | grep -E '\.(js|jsx)$' | grep '^web/' || true)

FAILED=false

# Backend linting
if [ -n "$STAGED_PY_FILES" ]; then
    echo ""
    echo "🐍 Linting Python files..."

    source venv/bin/activate

    echo "$STAGED_PY_FILES" | xargs black --check || {
        echo "❌ Black failed. Auto-fix with: black ."
        FAILED=true
    }

    echo "$STAGED_PY_FILES" | xargs flake8 || {
        echo "❌ Flake8 failed"
        FAILED=true
    }

    echo "$STAGED_PY_FILES" | xargs isort --check-only || {
        echo "❌ Isort failed. Auto-fix with: isort ."
        FAILED=true
    }
fi

# Frontend linting
if [ -n "$STAGED_JS_FILES" ]; then
    echo ""
    echo "⚛️  Linting JavaScript files..."

    cd web
    npm run lint || {
        echo "❌ ESLint failed. Auto-fix with: cd web && npm run lint:fix"
        FAILED=true
    }
    cd ..
fi

if [ "$FAILED" = true ]; then
    echo ""
    echo "❌ Pre-commit checks failed"
    exit 1
fi

echo ""
echo "✅ All checks passed!"
exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOK_DIR/pre-commit"
echo "✓ Installed pre-commit hook"

# Pre-push hook
cat > "$PROJECT_ROOT/$HOOK_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook: Run tests only for changed code

echo "🧪 Running pre-push tests..."

# Get files changed in commits being pushed
REMOTE="$1"
URL="$2"

# Compare with remote branch
if git rev-parse --verify "@{u}" >/dev/null 2>&1; then
    CHANGED_FILES=$(git diff --name-only "@{u}")
else
    # Fallback: check last commit
    CHANGED_FILES=$(git diff --name-only HEAD~1)
fi

HAS_PY=$(echo "$CHANGED_FILES" | grep '\.py$' | grep -v '^web/' || true)
HAS_JS=$(echo "$CHANGED_FILES" | grep -E '\.(js|jsx)$' | grep '^web/' || true)

FAILED=false

# Backend tests
if [ -n "$HAS_PY" ]; then
    echo ""
    echo "🐍 Running backend tests..."

    source venv/bin/activate
    pytest tests/backend/ -v || {
        echo "❌ Backend tests failed"
        FAILED=true
    }
fi

# Frontend tests
if [ -n "$HAS_JS" ]; then
    echo ""
    echo "⚛️  Running frontend tests..."

    cd web
    npm test || {
        echo "❌ Frontend tests failed"
        FAILED=true
    }
    cd ..
fi

if [ "$FAILED" = true ]; then
    echo ""
    echo "❌ Pre-push tests failed"
    exit 1
fi

echo ""
echo "✅ All tests passed!"
exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOK_DIR/pre-push"
echo "✓ Installed pre-push hook"

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "Hooks:"
echo "  pre-commit: Lints staged files (backend + frontend)"
echo "  pre-push:   Runs tests for changed code"
echo ""
echo "To skip hooks temporarily:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
