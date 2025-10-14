#!/bin/bash
# Start Flask API server only
cd "$(dirname "$0")/.."
source venv/bin/activate
python server/api.py
