#!/bin/bash

# Sophie Assistant - Start Script
# Runs both backend (FastAPI) and frontend (Vite) concurrently

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Trap to kill background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting Sophie Assistant...${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found. Run 'uv sync' first.${NC}"
    exit 1
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
fi

# Start backend
echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
source .venv/bin/activate
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
cd frontend && npm run dev &
FRONTEND_PID=$!

echo -e "\n${GREEN}Both services are running!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:5173"
echo -e "\nPress Ctrl+C to stop both services.\n"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
