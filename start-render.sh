#!/bin/bash
# Arranca action server en background y Rasa en foreground

echo "Starting action server on port 5055..."
python -m rasa_sdk --actions actions --port 5055 &

echo "Waiting for action server to be ready..."
sleep 5

PORT=${PORT:-5005}
echo "Starting Rasa server on port $PORT..."
exec rasa run \
    --enable-api \
    --cors "*" \
    --port $PORT \
    --endpoints endpoints.yml
