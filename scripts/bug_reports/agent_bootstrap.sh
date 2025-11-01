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
  git remote set-url origin "${GIT_REMOTE_URL:-$(git remote get-url origin)}"
}

checkout_branch() {
  cd "${WORKSPACE_DIR}"
  git fetch origin "${TARGET_BRANCH}"
  git checkout -B "bugfix/${REPORT_ID}" "origin/${TARGET_BRANCH}"
}

maybe_run_claude() {
  if [[ -f "${PROMPT_PATH}" ]]; then
    claude --non-interactive \
      --workingDirectory "${WORKSPACE_DIR}" \
      --maxTokens 4096 \
      --prompt "$(cat "${PROMPT_PATH}")"
  else
    log "No prompt supplied at ${PROMPT_PATH}; skipping Claude automation."
  fi
}

LAST_TEST_RESULTS="{}"

run_tests() {
  local tests_json="{}"
  cd "${WORKSPACE_DIR}/web"
  npm install --prefer-offline --omit=optional --ignore-scripts
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

push_changes() {
  cd "${WORKSPACE_DIR}"
  git add -A
  if git diff --cached --quiet; then
    log "No staged changes detected after Claude automation."
    fail_summary "Claude automation did not produce any changes"
    exit 4
  fi
  git status
  git commit -m "fix: automated remediation (bug ${REPORT_ID})"
  git push origin "HEAD:${TARGET_BRANCH}"
  git rev-parse HEAD
}

# -----------------------------------------------------------------------------
# Session orchestration
# -----------------------------------------------------------------------------

run_step "Link cached node_modules" link_node_modules
run_step "Configure git identity" configure_git
run_step "Prepare remediation branch" checkout_branch
run_step "Display workspace status" git -C "${WORKSPACE_DIR}" status
run_step "Execute Claude automation" maybe_run_claude
run_step "Run verification suite" run_tests
COMMIT_SHA="$(run_step "Commit and push changes" push_changes)"

success_summary "${COMMIT_SHA}" "${LAST_TEST_RESULTS}"

log "Session completed successfully"
