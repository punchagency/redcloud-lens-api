#!/bin/bash

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || { echo "Failed to activate virtual environment. Exiting."; exit 1; }

# Pull the latest changes from the develop branch
echo "Pulling latest changes from develop branch..."
git pull origin develop || { echo "Git pull failed. Exiting."; exit 1; }

# Restart the systemd service
echo "Restarting redlensapi.service..."
sudo systemctl restart redlensapi.service || { echo "Failed to restart redlensapi.service. Exiting."; exit 1; }

# Confirm success
echo "App updated and service restarted successfully!"
