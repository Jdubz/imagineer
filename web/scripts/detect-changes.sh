#!/bin/bash
# Detect which parts of the codebase have changed
# Returns: backend, frontend, both, or none

set -e

# Get list of changed files (staged for commit or HEAD for push)
if [ "$1" == "staged" ]; then
    # For pre-commit: check staged files
    CHANGED_FILES=$(git diff --cached --name-only --diff-filter=d)
elif [ "$1" == "push" ]; then
    # For pre-push: check commits being pushed
    # Compare against remote branch
    REMOTE_REF="$2"
    LOCAL_REF="$3"
    if [ -z "$REMOTE_REF" ] || [ -z "$LOCAL_REF" ]; then
        # Fallback: compare with HEAD
        CHANGED_FILES=$(git diff --name-only HEAD@{1} HEAD 2>/dev/null || git diff --name-only --cached)
    else
        CHANGED_FILES=$(git diff --name-only "$REMOTE_REF" "$LOCAL_REF")
    fi
else
    # Default: check all changes
    CHANGED_FILES=$(git diff --name-only --cached)
fi

# Check if no files changed
if [ -z "$CHANGED_FILES" ]; then
    echo "none"
    exit 0
fi

# Patterns for backend files
BACKEND_PATTERNS=(
    "^server/"
    "^src/"
    "^examples/"
    "^tests/backend/"
    "^scripts/"
    "requirements.txt"
    "pyproject.toml"
    ".flake8"
    "^config.yaml"
    "Makefile"
)

# Patterns for frontend files
FRONTEND_PATTERNS=(
    "^web/"
    "^tests/frontend/"
)

HAS_BACKEND=false
HAS_FRONTEND=false

# Check each changed file
while IFS= read -r file; do
    # Skip empty lines
    [ -z "$file" ] && continue

    # Check backend patterns
    for pattern in "${BACKEND_PATTERNS[@]}"; do
        if [[ "$file" =~ $pattern ]]; then
            HAS_BACKEND=true
            break
        fi
    done

    # Check frontend patterns
    for pattern in "${FRONTEND_PATTERNS[@]}"; do
        if [[ "$file" =~ $pattern ]]; then
            HAS_FRONTEND=true
            break
        fi
    done

    # Early exit if both found
    if [ "$HAS_BACKEND" = true ] && [ "$HAS_FRONTEND" = true ]; then
        break
    fi
done <<< "$CHANGED_FILES"

# Return result
if [ "$HAS_BACKEND" = true ] && [ "$HAS_FRONTEND" = true ]; then
    echo "both"
elif [ "$HAS_BACKEND" = true ]; then
    echo "backend"
elif [ "$HAS_FRONTEND" = true ]; then
    echo "frontend"
else
    echo "none"
fi
