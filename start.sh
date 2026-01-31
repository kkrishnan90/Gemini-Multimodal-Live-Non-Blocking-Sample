#!/bin/bash

# Sophie Assistant - Start Script
# Runs both backend (FastAPI) and frontend (Vite) concurrently

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_PID=""
FRONTEND_PID=""

# Kill any existing processes on our ports
kill_existing() {
    echo -e "${YELLOW}Checking for existing processes on ports 8000 and 5173...${NC}"

    # Kill any process on port 8000 (backend)
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Kill any process on port 5173 (frontend)
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true

    # Small delay to allow ports to be released
    sleep 1
}

# Trap to kill background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"

    # Kill backend and all its children
    if [ ! -z "$BACKEND_PID" ] && [ "$BACKEND_PID" != "" ]; then
        echo -e "${YELLOW}Stopping backend (PID: $BACKEND_PID)...${NC}"
        pkill -P $BACKEND_PID 2>/dev/null || true
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # Kill frontend and all its children
    if [ ! -z "$FRONTEND_PID" ] && [ "$FRONTEND_PID" != "" ]; then
        echo -e "${YELLOW}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        pkill -P $FRONTEND_PID 2>/dev/null || true
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Force kill any remaining processes on our ports
    sleep 1
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}Shutdown complete.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting Sophie Assistant...${NC}"

# Kill any existing processes first
kill_existing

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

# Give backend a moment to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo -e "\n${GREEN}Both services are running!${NC}"
echo -e "  Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo -e "  Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
echo -e "\nPress Ctrl+C to stop both services.\n"

# Wait for either process to exit
wait
