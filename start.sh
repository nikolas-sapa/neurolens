#!/usr/bin/env bash
set -e
echo "Starting NeuroPulse..."
(cd backend && bash start.sh) &
BPID=$!
(cd frontend && { [ -d node_modules ] || npm install; } && npm run dev) &
FPID=$!
trap "kill $BPID $FPID 2>/dev/null" EXIT
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:3000"
wait
