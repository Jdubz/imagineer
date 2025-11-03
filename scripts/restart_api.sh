#!/bin/bash
#
# Restart the Imagineer API service
#

echo "Restarting Imagineer API..."
sudo systemctl restart imagineer-api

echo "Waiting for service to start..."
sleep 2

echo "Service status:"
sudo systemctl status imagineer-api --no-pager -l | head -20

echo ""
echo "Recent logs:"
sudo journalctl -u imagineer-api -n 20 --no-pager
