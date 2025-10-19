#!/bin/bash

# Start backend service
echo "Starting backend service..."
cd /app
source .venv/bin/activate
python run_server.py
