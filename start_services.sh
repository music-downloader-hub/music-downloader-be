#!/bin/bash

# Start wrapper service in background
echo "Starting wrapper service..."
cd /app/wrapper
./wrapper -H 0.0.0.0 -D 10020 -M 20020 &
WRAPPER_PID=$!

# Wait for wrapper to start
sleep 5

# Check if wrapper is running
if ! kill -0 $WRAPPER_PID 2>/dev/null; then
    echo "Failed to start wrapper service"
    exit 1
fi

echo "Wrapper service started with PID: $WRAPPER_PID"

# Start backend service
echo "Starting backend service..."
cd /app
python run_server.py &
BACKEND_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill $WRAPPER_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    wait
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait $BACKEND_PID
