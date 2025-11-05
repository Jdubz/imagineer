#!/bin/bash
# Development server startup script
# This runs a LOCAL development server separate from production

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Imagineer Development Server ===${NC}"

# Check if we're in the right directory
if [ ! -f "server/api.py" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

# Check if production server is running on port 5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}Error: Port 5000 is already in use${NC}"
    echo "Is another development server running?"
    exit 1
fi

# Verify we're not accidentally stopping production
if [ "$1" = "stop" ]; then
    echo -e "${RED}This script doesn't stop servers.${NC}"
    echo "To stop development server, press Ctrl+C or kill the process."
    echo -e "${YELLOW}NEVER stop the production server (port 10050) manually!${NC}"
    exit 1
fi

# Load development environment
export FLASK_ENV=development
export FLASK_APP=server.api:app
export FLASK_DEBUG=1
export PORT=5000
export HOST=127.0.0.1
export IMAGINEER_CONFIG_PATH=$(pwd)/config.development.yaml
export DATABASE_URL=sqlite:///$(pwd)/instance/imagineer-dev.db
export ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Load .env.development.local if it exists (for local overrides)
if [ -f .env.development.local ]; then
    echo -e "${GREEN}Loading .env.development.local${NC}"
    set -a
    source .env.development.local
    set +a
fi

# Create development directories
echo "Creating development directories..."
mkdir -p /tmp/imagineer-dev/outputs
mkdir -p /tmp/imagineer-dev/scraped
mkdir -p /tmp/imagineer-dev/checkpoints
mkdir -p /tmp/imagineer-dev/bug_reports
mkdir -p instance
mkdir -p logs

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

echo -e "${GREEN}Starting development server on http://${HOST}:${PORT}${NC}"
echo -e "${YELLOW}Production server runs on port 10050 and should NOT be touched!${NC}"
echo ""
echo "Development database: instance/imagineer-dev.db"
echo "Development outputs: /tmp/imagineer-dev/"
echo "Configuration: config.development.yaml"
echo ""
echo "Press Ctrl+C to stop the development server"
echo ""

# Run development server with auto-reload
python server/api.py
