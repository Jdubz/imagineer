#!/usr/bin/env bash
# Backend deployment helper invoked from CI on the production host.
# Builds/pulls the latest API image, restarts the docker-compose stack,
# and waits for the health check to pass.

set -euo pipefail

APP_DIR="${APP_DIR:-/home/jdubz/Development/imagineer}"
STACK_DIR="/srv/imagineer"
COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"
BUILD_TAG="${BUILD_TAG:-${GITHUB_SHA:-latest}}"
IMAGE_TAG="ghcr.io/jdubz/imagineer/api:${BUILD_TAG}"
SKIP_BUILD=${SKIP_BUILD:-true}
HEALTH_URL="http://localhost:10050/api/health"
MAX_ATTEMPTS=10
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

log "Starting backend release pipeline (containers)..."

[[ -d "${APP_DIR}" ]] || abort "Application directory ${APP_DIR} not found."
[[ -f "${COMPOSE_FILE}" ]] || abort "Compose file ${COMPOSE_FILE} not found."

cd "${APP_DIR}"

if [[ "${SKIP_BUILD}" != "true" ]]; then
  log "Building API image ${IMAGE_TAG}..."
  docker build -t "${IMAGE_TAG}" .
else
  log "Skipping local build (SKIP_BUILD=true); pulling ${IMAGE_TAG} from registry..."
  docker pull "${IMAGE_TAG}"
fi

cd "${STACK_DIR}"

log "Pulling compose images (cloudflared/watchtower) and recreating api..."
docker compose pull cloudflared watchtower || log "Pull skipped (not critical)."
docker compose up -d api cloudflared watchtower

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
  docker compose logs --tail=120 api || true
  abort "Service failed health checks after ${MAX_ATTEMPTS} attempts."
fi

log "Backend release completed successfully (compose)."
