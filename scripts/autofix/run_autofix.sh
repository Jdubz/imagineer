#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[autofix] %s\n' "$*" >&2
}

abort() {
  log "ERROR: $*"
  exit 1
}

require() {
  command -v "$1" >/dev/null 2>&1 || abort "Missing required command: $1"
}

require git
require jq

# Configuration (can be overridden via environment variables)
AUTOFIX_REPO_URL="${AUTOFIX_REPO_URL:-https://github.com/Jdubz/imagineer.git}"
AUTOFIX_BRANCH="${AUTOFIX_BRANCH:-develop}"
AUTOFIX_WORKSPACE="${AUTOFIX_WORKSPACE:-/workspace/autofix}"
AUTOFIX_CONTEXT_PATH="${AUTOFIX_CONTEXT_PATH:-/tmp/autofix/context.md}"
AUTOFIX_PLAN_PATH="${AUTOFIX_PLAN_PATH:-/tmp/autofix/plan.json}"
AUTOFIX_SUMMARY_PATH="${AUTOFIX_SUMMARY_PATH:-/tmp/autofix/summary.json}"
AUTOFIX_CONFIG_MANIFEST="${AUTOFIX_CONFIG_MANIFEST:-scripts/autofix/config_manifest.txt}"
AUTOFIX_TEST_MATRIX="${AUTOFIX_TEST_MATRIX:-scripts/autofix/test_matrix.json}"
AUTOFIX_SOURCE_ROOT="${AUTOFIX_SOURCE_ROOT:-/workspace/source}"
AUTOFIX_COMPONENT_LABELS="${AUTOFIX_COMPONENT_LABELS:-}"
AUTOFIX_COMMITTER_NAME="${AUTOFIX_COMMITTER_NAME:-Imagineer AutoFix Bot}"
AUTOFIX_COMMITTER_EMAIL="${AUTOFIX_COMMITTER_EMAIL:-infra+autofix@joshwentworth.com}"
AUTOFIX_COMMIT_MESSAGE_PREFIX="${AUTOFIX_COMMIT_MESSAGE_PREFIX:-fix}"
AUTOFIX_DRY_RUN="${AUTOFIX_DRY_RUN:-false}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_PLAN_ARGS="${CLAUDE_PLAN_ARGS:---max-steps 12}"
CLAUDE_APPLY_ARGS="${CLAUDE_APPLY_ARGS:---yes}"

mkdir -p "${AUTOFIX_WORKSPACE}"
WORKDIR="$(mktemp -d "${AUTOFIX_WORKSPACE}/repo.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

AUTH_REPO_URL="${AUTOFIX_REPO_URL}"
if [[ "${AUTOFIX_REPO_URL}" == https://* && -n "${GH_TOKEN_AUTOFIX:-}" ]]; then
  AUTH_REPO_URL="${AUTOFIX_REPO_URL/https:\/\//https:\/\/x-access-token:${GH_TOKEN_AUTOFIX}@}"
fi

log "Cloning ${AUTOFIX_REPO_URL} into ${WORKDIR}"
git clone --depth=2 --branch "${AUTOFIX_BRANCH}" "${AUTH_REPO_URL}" "${WORKDIR}"
cd "${WORKDIR}"
git fetch origin "${AUTOFIX_BRANCH}" --depth=1
git checkout "${AUTOFIX_BRANCH}"
git pull --ff-only origin "${AUTOFIX_BRANCH}"

# Sync configuration files specified in manifest
if [[ -f "${AUTOFIX_SOURCE_ROOT}/${AUTOFIX_CONFIG_MANIFEST}" ]]; then
  manifest="${AUTOFIX_SOURCE_ROOT}/${AUTOFIX_CONFIG_MANIFEST}"
elif [[ -f "${AUTOFIX_CONFIG_MANIFEST}" ]]; then
  manifest="${AUTOFIX_CONFIG_MANIFEST}"
else
  manifest=""
  log "Config manifest not found; skipping config sync."
fi

if [[ -n "${manifest}" ]]; then
  log "Syncing config files from manifest ${manifest}"
  while IFS= read -r entry; do
    [[ -z "${entry}" || "${entry}" =~ ^# ]] && continue
    src_path="${AUTOFIX_SOURCE_ROOT}/${entry}"
    dest_path="${WORKDIR}/${entry}"
    if [[ -d "${src_path}" ]]; then
      mkdir -p "${dest_path}"
      cp -a "${src_path}/." "${dest_path}/"
    elif [[ -f "${src_path}" ]]; then
      mkdir -p "$(dirname "${dest_path}")"
      cp -f "${src_path}" "${dest_path}"
    else
      log "Warning: manifest entry ${entry} not found at ${src_path}"
    fi
  done < "${manifest}"
fi

# Prepare Claude context
[[ -f "${AUTOFIX_CONTEXT_PATH}" ]] || abort "Context file not found: ${AUTOFIX_CONTEXT_PATH}"

log "Generating plan with Claude"
"${CLAUDE_BIN}" codex plan \
  --prompt "${AUTOFIX_CONTEXT_PATH}" \
  --output "${AUTOFIX_PLAN_PATH}" \
  ${CLAUDE_PLAN_ARGS}

[[ -f "${AUTOFIX_PLAN_PATH}" ]] || abort "Claude plan output not found at ${AUTOFIX_PLAN_PATH}"

risk_level="$(jq -r '.risk // \"unknown\"' "${AUTOFIX_PLAN_PATH}")"
log "Claude plan risk level: ${risk_level}"
if [[ "${risk_level}" == "high" || "${risk_level}" == "critical" ]]; then
  abort "Aborting auto-fix due to high risk level (${risk_level})."
fi

if [[ "${AUTOFIX_DRY_RUN}" == "true" ]]; then
  log "Dry run mode enabled; skipping claude codex apply."
else
  log "Applying plan with Claude"
  "${CLAUDE_BIN}" codex apply \
    "${AUTOFIX_PLAN_PATH}" \
    ${CLAUDE_APPLY_ARGS}
fi

log "Reviewing git status"
git status --short

if git diff --quiet; then
  abort "No changes produced by Claude; nothing to commit."
fi

# Determine test command based on component labels
select_test_command() {
  local labels token cmd
  labels="${AUTOFIX_COMPONENT_LABELS}"
  if [[ -z "${labels}" ]]; then
    jq -r '.default' "${AUTOFIX_TEST_MATRIX}"
    return
  fi
  for token in ${labels}; do
    cmd="$(jq -r --arg label "${token}" '.[$label] // empty' "${AUTOFIX_TEST_MATRIX}")"
    if [[ -n "${cmd}" && "${cmd}" != "null" ]]; then
      printf '%s\n' "${cmd}"
      return
    fi
  done
  jq -r '.default' "${AUTOFIX_TEST_MATRIX}"
}

if [[ -f "${AUTOFIX_TEST_MATRIX}" ]]; then
  TEST_COMMAND="$(select_test_command)"
else
  log "Test matrix missing (${AUTOFIX_TEST_MATRIX}); defaulting to 'make test'."
  TEST_COMMAND="make test"
fi

if [[ "${AUTOFIX_DRY_RUN}" == "true" ]]; then
  log "Dry run mode: skipping tests (${TEST_COMMAND})."
  TEST_RESULT="skipped"
else
  log "Running tests: ${TEST_COMMAND}"
  set +e
  eval "${TEST_COMMAND}"
  status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    abort "Test command failed (${TEST_COMMAND}) with status ${status}"
  fi
  TEST_RESULT="passed"
fi

log "Configuring git committer"
git config user.name "${AUTOFIX_COMMITTER_NAME}"
git config user.email "${AUTOFIX_COMMITTER_EMAIL}"

SUMMARY_TEXT="$(jq -r '.summary // empty' "${AUTOFIX_PLAN_PATH}")"
if [[ -z "${SUMMARY_TEXT}" || "${SUMMARY_TEXT}" == "null" ]]; then
  SUMMARY_TEXT="Automated fix applied by Claude"
fi

COMMIT_MSG="${AUTOFIX_COMMIT_MESSAGE_PREFIX}: ${SUMMARY_TEXT} (auto-fix)"

log "Creating commit: ${COMMIT_MSG}"
git add -A
git commit -m "${COMMIT_MSG}"

if [[ "${AUTOFIX_DRY_RUN}" == "true" ]]; then
  log "Dry run: skipping push to remote."
  COMMIT_SHA="$(git rev-parse HEAD)"
else
  log "Pushing commit to origin ${AUTOFIX_BRANCH}"
  git push origin "HEAD:${AUTOFIX_BRANCH}"
  COMMIT_SHA="$(git rev-parse HEAD)"
fi

log "Writing summary JSON to ${AUTOFIX_SUMMARY_PATH}"
mkdir -p "$(dirname "${AUTOFIX_SUMMARY_PATH}")"
export AUTOFIX_COMMIT_SHA="${COMMIT_SHA}"
export AUTOFIX_BRANCH_NAME="${AUTOFIX_BRANCH}"
export AUTOFIX_SUMMARY_TEXT="${SUMMARY_TEXT}"
export AUTOFIX_TEST_COMMAND_VALUE="${TEST_COMMAND}"
export AUTOFIX_TEST_RESULT_VALUE="${TEST_RESULT}"
export AUTOFIX_RISK_VALUE="${risk_level}"
export AUTOFIX_SUMMARY_FILE="${AUTOFIX_SUMMARY_PATH}"
python - <<'PY'
import json
import os

summary = {
    'commit': os.environ['AUTOFIX_COMMIT_SHA'],
    'branch': os.environ['AUTOFIX_BRANCH_NAME'],
    'summary': os.environ['AUTOFIX_SUMMARY_TEXT'],
    'test_command': os.environ['AUTOFIX_TEST_COMMAND_VALUE'],
    'test_result': os.environ['AUTOFIX_TEST_RESULT_VALUE'],
    'risk': os.environ['AUTOFIX_RISK_VALUE'],
}
with open(os.environ['AUTOFIX_SUMMARY_FILE'], 'w', encoding='utf-8') as handle:
    json.dump(summary, handle, indent=2)
    handle.write('\n')
PY

log "Auto-fix complete."
