#!/usr/bin/env bash
cd "$(dirname "$0")"
pkill -f "uvicorn backend.main:app.*8001" 2>/dev/null || true
pkill -f "http.server 3001" 2>/dev/null || true
PYTHONPATH=backend ../flight-forecast-engine/backend/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8001 &
python3 -m http.server 3001 --directory frontend &
echo "Ground Route Engine running at http://localhost:3001"
