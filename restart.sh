#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ -x "backend/venv/bin/uvicorn" ]; then
  UVICORN_BIN="backend/venv/bin/uvicorn"
elif [ -x "../flight-forecast-engine/backend/venv/bin/uvicorn" ]; then
  UVICORN_BIN="../flight-forecast-engine/backend/venv/bin/uvicorn"
else
  echo "Error: uvicorn virtual environment not found. Please run ./setup.sh first."
  exit 1
fi

echo "Stopping existing Ground Route Engine processes..."
pkill -f "uvicorn backend.main:app.*8001" 2>/dev/null || true
pkill -f "http.server 3001" 2>/dev/null || true
sleep 1

echo "Starting Ground Route Engine API on http://localhost:8001 using ${UVICORN_BIN} ..."
PYTHONPATH=backend "${UVICORN_BIN}" backend.main:app --host 0.0.0.0 --port 8001 --reload &

echo "Starting Ground Route Engine UI on http://localhost:3001 ..."
python3 -m http.server 3001 --directory frontend &

echo "Ground Route Engine ready at http://localhost:3001"
