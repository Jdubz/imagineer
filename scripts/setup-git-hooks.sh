#!/bin/bash
# Setup script for Git hooks
# This script installs pre-push hooks for code quality checks

set -e

echo "🔧 Setting up Git hooks for code quality checks..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a Git repository. Please run from the project root."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -f "pyproject.toml" ]; then
    echo "❌ Not in project root directory. Please run from the project root."
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy the pre-push hook
echo "📝 Installing pre-push hook..."
cp scripts/pre-push-hook .git/hooks/pre-push
chmod +x .git/hooks/pre-push

echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-push hook will now run the following checks before any push:"
echo "  • Black formatting check"
echo "  • isort import sorting check" 
echo "  • Flake8 linting check"
echo ""
echo "If any check fails, the push will be blocked until the issues are fixed."
echo ""
echo "To bypass the hook (not recommended), use:"
echo "  git push --no-verify"