#!/bin/bash

# Start backend service (wrapper is managed by backend)
echo "Starting backend service..."
cd /app
source .venv/bin/activate
python run_server.py
