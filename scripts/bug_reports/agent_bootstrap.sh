#!/usr/bin/env bash
# shellcheck disable=SC2155
#
# Container bootstrap script executed inside the bug report remediation worker.
# It prepares the workspace, optionally invokes Claude CLI, runs quality gates,
# and attempts to push fixes back to the target branch.
#

set -euo pipefail

START_TIME="$(date --iso-8601=seconds)"
REPORT_ID="${REPORT_ID:-}"
TARGET_BRANCH="${TARGET_BRANCH:-develop}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/repo}"
CONTEXT_PATH="${CONTEXT_PATH:-/workspace/context/context.json}"
PROMPT_PATH="${PROMPT_PATH:-/workspace/context/prompt.txt}"
SESSION_SUMMARY_PATH="${SESSION_SUMMARY:-/workspace/artifacts/session_summary.json}"
LOG_DIR="${LOG_DIR:-/workspace/logs}"
TIMEOUT_MINUTES="${TIMEOUT_MINUTES:-60}"
NODE_CACHE="${IMAGINEER_NODE_MODULES_CACHE:-/opt/imagineer/node_modules}"

if [[ -z "${REPORT_ID}" ]]; then
  echo "REPORT_ID environment variable is required" >&2
  exit 2
fi

mkdir -p "${LOG_DIR}" "$(dirname "${SESSION_SUMMARY_PATH}")"

exec 3>&1
exec >>"${LOG_DIR}/session.log"
exec 2>&1

log() {
  printf '=== [%s] %s\n' "$(date --iso-8601=seconds)" "$*" | tee /dev/fd/3
}

fail_summary() {
  local message="$1"
  cat >"${SESSION_SUMMARY_PATH}" <<EOF
{
  "report_id": "${REPORT_ID}",
  "started_at": "${START_TIME}",
  "finished_at": "$(date --iso-8601=seconds)",
  "status": "failed",
  "failure_reason": ${message@Q}
}
EOF
}

success_summary() {
  local commit_sha="$1"
  shift
  local tests_json="$1"
  cat >"${SESSION_SUMMARY_PATH}" <<EOF
{
  "report_id": "${REPORT_ID}",
  "started_at": "${START_TIME}",
  "finished_at": "$(date --iso-8601=seconds)",
  "status": "success",
  "commit": "${commit_sha}",
  "tests": ${tests_json}
}
EOF
}

trap 'status=$?; if [[ $status -ne 0 ]]; then log "Session aborted with status ${status}"; fi' EXIT

run_step() {
  local title="$1"
  shift
  log "${title}"
  if "$@"; then
    log "${title} ✅"
    return 0
  else
    local code=$?
    log "${title} ❌ (exit ${code})"
    fail_summary "${title} failed with exit code ${code}"
    exit "${code}"
  fi
}

link_node_modules() {
  if [[ -d "${NODE_CACHE}" ]]; then
    mkdir -p "${WORKSPACE_DIR}/web/node_modules"
    rsync -a --delete "${NODE_CACHE}/" "${WORKSPACE_DIR}/web/node_modules/"
  fi
}

configure_git() {
  cd "${WORKSPACE_DIR}"
  git config --global user.name "${GIT_AUTHOR_NAME:-Imagineer Bug Agent}"
  git config --global user.email "${GIT_AUTHOR_EMAIL:-agent@imagineer.local}"
  local remote_url
  remote_url="${GIT_REMOTE_URL:-$(git remote get-url origin)}"

  git remote set-url origin "${remote_url}"
  if [[ -f "${HOME}/.git-credentials" ]]; then
    git config --global credential.helper "store --file=${HOME}/.git-credentials"
    log "Configured Git credential helper to use stored credentials."
  else
    log "No ~/.git-credentials found; relying on existing Git credential helper."
  fi
}

cleanup_workspace() {
  cd "${WORKSPACE_DIR}"
  # Discard all local changes from previous runs
  git reset --hard HEAD
  # Remove untracked files and directories
  git clean -fdx
  log "Workspace cleaned: ready for fresh checkout"
}

checkout_branch() {
  cd "${WORKSPACE_DIR}"
  git fetch origin "${TARGET_BRANCH}"
  # Check out target branch directly (agents commit to develop, not bugfix branches)
  git checkout "${TARGET_BRANCH}"
  git reset --hard "origin/${TARGET_BRANCH}"
}

hydrate_claude_credentials() {
  local host_creds="/tmp/host-claude-credentials.json"
  local dest="${HOME}/.claude/.credentials.json"
  if [[ -f "${host_creds}" ]]; then
    mkdir -p "$(dirname "${dest}")"
    cp "${host_creds}" "${dest}"
    chmod 600 "${dest}"
    log "Hydrated Claude credentials for automation user."
  else
    log "No Claude credentials mount detected; proceeding without automation credentials."
  fi
}

maybe_run_claude() {
  if [[ -f "${PROMPT_PATH}" ]]; then
    pushd "${WORKSPACE_DIR}" >/dev/null
    claude --print \
      --dangerously-skip-permissions \
      "$(cat "${PROMPT_PATH}")"
    popd >/dev/null
  else
    log "No prompt supplied at ${PROMPT_PATH}; skipping Claude automation."
  fi
}

LAST_TEST_RESULTS="{}"

run_tests() {
  local tests_json="{}"
  cd "${WORKSPACE_DIR}/web"
  # Ensure dependencies match the lockfile exactly for deterministic installs
  npm ci --prefer-offline
  npm run lint
  npm run tsc
  npm test -- --run
  cd "${WORKSPACE_DIR}"
  black --check server src tests
  flake8 server src tests
  pytest --maxfail=1 --disable-warnings -q
  tests_json='{
    "npm_lint": "passed",
    "npm_tsc": "passed",
    "npm_test": "passed",
    "black": "passed",
    "flake8": "passed",
    "pytest": "passed"
  }'
  LAST_TEST_RESULTS="${tests_json}"
}

validate_changes() {
  cd "${WORKSPACE_DIR}"
  git add -A

  # Check if any changes were made
  if git diff --cached --quiet; then
    log "❌ VALIDATION FAILED: No files were modified"
    fail_summary "No code changes detected"
    return 1
  fi

  local changed_files
  changed_files=$(git diff --cached --name-only)
  local file_count
  file_count=$(echo "$changed_files" | wc -l)

  log "Files changed ($file_count):"
  echo "$changed_files" | while read -r file; do
    log "  - $file"
  done

  # Red flag: only package-lock.json changed
  if [ "$file_count" -eq 1 ] && echo "$changed_files" | grep -qE '^(web/)?package-lock\.json$'; then
    log "❌ VALIDATION FAILED: Only package-lock.json was modified"
    log "This suggests npm install ran but no actual code changes were made"
    fail_summary "Only package-lock.json modified - no actual fix implemented"
    return 1
  fi

  # Red flag: only build artifacts or configs changed
  if echo "$changed_files" | grep -qvE '\.(ts|tsx|js|jsx|py|html|css|scss)$' && [ "$file_count" -lt 3 ]; then
    log "⚠️  WARNING: Changes appear to be only build artifacts/configs"
    log "Expected code changes in .ts/.tsx/.py files for typical bug fixes"
  fi

  # Warning: too many files changed
  if [ "$file_count" -gt 10 ]; then
    log "⚠️  WARNING: $file_count files changed (expected 1-3 for typical bug fix)"
    log "Large changesets may indicate unintended side effects"
  fi

  # Try to extract bug context for logging
  if [ -f "${CONTEXT_PATH}" ]; then
    local bug_desc
    bug_desc=$(jq -r '.description // "N/A"' "${CONTEXT_PATH}" 2>/dev/null || echo "N/A")
    local bug_route
    bug_route=$(jq -r '.clientMeta.locationHref // "N/A"' "${CONTEXT_PATH}" 2>/dev/null || echo "N/A")
    log "Bug context:"
    log "  Route: $bug_route"
    log "  Description: $bug_desc"
  fi

  log "✅ Change validation passed"
  return 0
}

push_changes() {
  cd "${WORKSPACE_DIR}"

  local commit_msg="fix: automated remediation (bug ${REPORT_ID})"

  git status >&2
  git commit -m "$commit_msg" >&2
  if ! git push origin "${TARGET_BRANCH}" >&2; then
    log "Git push failed to ${TARGET_BRANCH}. Check credentials or remote configuration."
    return 1
  fi
  git rev-parse HEAD
}

# -----------------------------------------------------------------------------
# Session orchestration
# -----------------------------------------------------------------------------

run_step "Link cached node_modules" link_node_modules
run_step "Configure git identity" configure_git
run_step "Clean workspace" cleanup_workspace
run_step "Prepare remediation branch" checkout_branch
run_step "Display workspace status" git -C "${WORKSPACE_DIR}" status
run_step "Hydrate Claude credentials" hydrate_claude_credentials
run_step "Execute Claude automation" maybe_run_claude
run_step "Validate code changes" validate_changes
run_step "Run verification suite" run_tests
COMMIT_SHA="$(run_step "Commit and push changes" push_changes)"
if [[ -z "${COMMIT_SHA}" ]]; then
  log "Failed to determine remediation commit SHA."
  fail_summary "Unable to determine remediation commit SHA"
  exit 5
fi

success_summary "${COMMIT_SHA}" "${LAST_TEST_RESULTS}"

log "Session completed successfully"
