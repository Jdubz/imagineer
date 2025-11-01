#!/usr/bin/env bash
set -euo pipefail

# Resolve project root (scripts/../)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/venv"
ACTIVATE="${VENV_DIR}/bin/activate"

if [[ ! -f "${ACTIVATE}" ]]; then
  echo "Virtualenv not found at ${VENV_DIR}. Create it with 'python -m venv venv'." >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${ACTIVATE}"

if [[ $# -gt 0 ]]; then
  exec "$@"
else
  exec "${SHELL:-/bin/bash}"
fi
