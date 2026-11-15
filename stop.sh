#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "Stopping existing Ground Route Engine processes..."
pkill -f "uvicorn backend.main:app.*8001" 2>/dev/null || true
pkill -f "http.server 3001" 2>/dev/null || true
sleep 1


