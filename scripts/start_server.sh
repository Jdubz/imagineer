#!/bin/bash
# Start Imagineer API Server
# Run with: bash start_server.sh

set -e

cd "$(dirname "$0")"

echo "================================================"
echo "IMAGINEER API SERVER"
echo "================================================"
echo ""

# Activate venv
source venv/bin/activate

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "Starting Flask API server..."
echo ""
echo "Access the web UI at:"
echo "  - Local: http://localhost:5000"
echo "  - Network: http://$LOCAL_IP:5000"
echo ""
echo "Generated images are accessible via SMB at:"
echo "  \\\\$LOCAL_IP\\Imagineer\\outputs"
echo ""
echo "================================================"
echo ""

# Start server
python server/api.py
