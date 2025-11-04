#!/bin/bash
#
# Test script for bug report remediation agent
#
# Usage:
#   export SESSION_COOKIE="your_session_cookie_here"
#   ./scripts/test_bug_agent.sh
#
# Or provide SESSION_COOKIE inline:
#   SESSION_COOKIE="your_session_cookie" ./scripts/test_bug_agent.sh
#

set -e

API_URL="http://localhost:10050"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Check for required session cookie
if [ -z "$SESSION_COOKIE" ]; then
  echo "ERROR: SESSION_COOKIE environment variable is required"
  echo ""
  echo "To obtain your session cookie:"
  echo "  1. Log in to ${API_URL} in your browser"
  echo "  2. Open browser DevTools (F12) -> Application/Storage -> Cookies"
  echo "  3. Copy the 'session' cookie value"
  echo "  4. Export it: export SESSION_COOKIE='<your_cookie_value>'"
  echo ""
  exit 1
fi

# Derive project root from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Bug Report Agent Test ==="
echo "Timestamp: $TIMESTAMP"
echo "Project Root: $PROJECT_ROOT"
echo

# Create a simple test bug report
echo "1. Creating test bug report..."
REPORT_ID=$(curl -s -X POST "${API_URL}/api/bug-reports" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=${SESSION_COOKIE}" \
  -d '{
    "description": "Test bug: Add a simple comment to server/api.py explaining the Flask app initialization",
    "environment": {
      "userAgent": "Test Script",
      "url": "http://localhost/test",
      "timestamp": "'$(date -Iseconds)'"
    },
    "clientMeta": {
      "locationHref": "/test"
    }
  }' | jq -r '.report_id')

echo "Created bug report: $REPORT_ID"
echo

# Monitor the bug report status
echo "2. Monitoring bug report status..."
for i in {1..60}; do
  STATUS=$(curl -s "${API_URL}/api/bug-reports/${REPORT_ID}" \
    -H "Cookie: session=${SESSION_COOKIE}" \
    | jq -r '.report.status')

  echo "  [$i/60] Status: $STATUS"

  if [ "$STATUS" == "resolved" ]; then
    echo
    echo "✅ Bug report resolved!"
    break
  fi

  sleep 5
done

# Show final results
echo
echo "3. Final bug report details:"
curl -s "${API_URL}/api/bug-reports/${REPORT_ID}" \
  -H "Cookie: session=${SESSION_COOKIE}" \
  | jq '.report.resolution.agent'

echo
echo "4. Session summary (if available):"
LOG_DIR="${PROJECT_ROOT}/logs/bug_reports/${REPORT_ID}"
if [ -f "${LOG_DIR}/artifacts/session_summary.json" ]; then
  cat "${LOG_DIR}/artifacts/session_summary.json" | jq .
else
  echo "Session summary not yet available"
fi

echo
echo "5. Session log tail:"
if [ -f "${LOG_DIR}/session.log" ]; then
  tail -50 "${LOG_DIR}/session.log"
else
  echo "Session log not yet available"
fi
