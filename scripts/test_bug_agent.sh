#!/bin/bash
#
# Test script for bug report remediation agent
#

set -e

API_URL="http://localhost:10050"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Bug Report Agent Test ==="
echo "Timestamp: $TIMESTAMP"
echo

# Create a simple test bug report
echo "1. Creating test bug report..."
REPORT_ID=$(curl -s -X POST "${API_URL}/api/bug-reports" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=.eJwlzjEOwjAMBdC7ZGawncRJcxlkO05pQSAhMSHuTsfn6b3rGc-4xWet5_HEW6znEZOATJLJJpkRzGYnEqOFJo5JRswIDV5SV-pKVbmrVjULtaWq3JWqSl2latRVqhp1laoxa3HwOLWV45gxdnFpzBgzxizN2e7cbD_nfpz3S1zvH0gvLxw.ZymGpA.MRmZ5uqIrjPZCT8wVzBUJa7fzkU" \
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
    -H "Cookie: session=.eJwlzjEOwjAMBdC7ZGawncRJcxlkO05pQSAhMSHuTsfn6b3rGc-4xWet5_HEW6znEZOATJLJJpkRzGYnEqOFJo5JRswIDV5SV-pKVbmrVjULtaWq3JWqSl2latRVqhp1laoxa3HwOLWV45gxdnFpzBgzxizN2e7cbD_nfpz3S1zvH0gvLxw.ZymGpA.MRmZ5uqIrjPZCT8wVzBUJa7fzkU" \
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
  -H "Cookie: session=.eJwlzjEOwjAMBdC7ZGawncRJcxlkO05pQSAhMSHuTsfn6b3rGc-4xWet5_HEW6znEZOATJLJJpkRzGYnEqOFJo5JRswIDV5SV-pKVbmrVjULtaWq3JWqSl2latRVqhp1laoxa3HwOLWV45gxdnFpzBgzxizN2e7cbD_nfpz3S1zvH0gvLxw.ZymGpA.MRmZ5uqIrjPZCT8wVzBUJa7fzkU" \
  | jq '.report.resolution.agent'

echo
echo "4. Session summary (if available):"
LOG_DIR="/home/jdubz/Development/imagineer/logs/bug_reports/${REPORT_ID}"
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
