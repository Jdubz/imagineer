#!/bin/bash
# Setup backend API server with systemd service
# Usage: ./scripts/deploy/setup-backend.sh

set -e

echo "🚀 Setting up Imagineer Backend API..."

# Configuration
PROJECT_DIR="/home/jdubz/Development/imagineer"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="/var/log/imagineer"
SERVICE_NAME="imagineer-api"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "❌ Do not run this script as root. It will use sudo when needed."
  exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
  echo "❌ Virtual environment not found at $VENV_DIR"
  echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Create log directory
echo "📁 Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown $USER:$USER "$LOG_DIR"

# Check if .env file exists
if [ ! -f "${PROJECT_DIR}/.env" ]; then
  echo "⚠️  No .env file found. Creating from example..."
  if [ -f "${PROJECT_DIR}/.env.example" ]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    echo "✅ Created .env file. Please edit it with your configuration."
  else
    echo "❌ No .env.example found. Please create .env manually."
    exit 1
  fi
fi

# Create systemd service file
echo "📝 Creating systemd service file..."
cat > /tmp/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Imagineer API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin"
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --bind 127.0.0.1:10050 \\
    --workers 2 \\
    --timeout 300 \\
    --access-logfile ${LOG_DIR}/access.log \\
    --error-logfile ${LOG_DIR}/error.log \\
    --log-level info \\
    server.api:app

Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Install systemd service
echo "📦 Installing systemd service..."
sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
sudo systemctl enable ${SERVICE_NAME}

# Start service
echo "🚀 Starting service..."
sudo systemctl start ${SERVICE_NAME}

# Check status
sleep 2
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
  echo "✅ Service started successfully!"
  sudo systemctl status ${SERVICE_NAME} --no-pager
else
  echo "❌ Service failed to start. Check logs:"
  echo "   sudo journalctl -u ${SERVICE_NAME} -n 50"
  exit 1
fi

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "Useful commands:"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "Test endpoint: curl http://localhost:10050/api/health"
