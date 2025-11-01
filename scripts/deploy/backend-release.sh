#!/usr/bin/env bash
# Backend deployment helper invoked from CI over SSH.
# Syncs main branch, refreshes dependencies, restarts the systemd service,
# and waits for the health check to pass before exiting.

set -euo pipefail

APP_DIR="/home/jdubz/Development/imagineer"
SERVICE_NAME="imagineer-api"
VENV_DIR="${APP_DIR}/venv"
HEALTH_URL="http://localhost:10050/api/health"
MAX_ATTEMPTS=5
SLEEP_SECONDS=3

log() {
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[${timestamp}] $*"
}

abort() {
  log "ERROR: $*"
  exit 1
}

log "Starting backend release pipeline..."

if [[ ! -d "${APP_DIR}" ]]; then
  abort "Application directory ${APP_DIR} not found."
fi

if ! sudo -n true 2>/dev/null; then
  abort "Passwordless sudo required for systemctl/journalctl. Configure NOPASSWD for ${USER}."
fi

cd "${APP_DIR}"

log "Fetching latest changes from origin..."
git fetch --prune origin
git reset --hard origin/main

log "Repository synced to commit $(git rev-parse --short HEAD)."

if [[ ! -d "${VENV_DIR}" ]]; then
  abort "Virtual environment missing at ${VENV_DIR}. Run scripts/deploy/setup-backend.sh first."
fi

log "Activating virtual environment..."
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

log "Upgrading pip and project dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

log "Restarting systemd service ${SERVICE_NAME}..."
sudo -n systemctl restart "${SERVICE_NAME}"

log "Waiting for API health check at ${HEALTH_URL}..."
for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  if curl -fsS "${HEALTH_URL}" >/dev/null; then
    log "Health check passed on attempt ${attempt}."
    success=true
    break
  fi
  log "Health check attempt ${attempt} failed; retrying in ${SLEEP_SECONDS}s..."
  sleep "${SLEEP_SECONDS}"
done

if [[ "${success:-false}" != true ]]; then
  sudo -n systemctl status "${SERVICE_NAME}" --no-pager || true
  sudo -n journalctl -u "${SERVICE_NAME}" -n 100 --no-pager || true
  abort "Service failed health checks after ${MAX_ATTEMPTS} attempts."
fi

log "Backend release completed successfully."
