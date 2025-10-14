#!/bin/bash
# Start both API and frontend dev servers
cd "$(dirname "$0")/.."

echo "Starting Imagineer Development Environment"
echo "=========================================="
echo ""
echo "Starting Flask API on port 5000..."
source venv/bin/activate
python server/api.py &
API_PID=$!

echo "Starting Vite dev server on port 5173..."
cd web
npm run dev &
VITE_PID=$!

echo ""
echo "Both servers started!"
echo "  - API: http://localhost:5000"
echo "  - Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Trap Ctrl+C and kill both processes
trap "kill $API_PID $VITE_PID 2>/dev/null" EXIT

wait
