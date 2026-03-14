#!/bin/bash

# Start script for AI Agent Platform
# Starts both backend and frontend in separate terminals

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

#workaround https://github.com/anthropics/claude-code/issues/15112
export TMPDIR=/tmp/claude-tmp
mkdir -p "$TMPDIR"
echo "🚀 Starting AI Agent Platform..."

# Check if backend dependencies are installed
if [ ! -d "backend/.venv" ]; then
    echo "⚠️  Backend virtual environment not found. Setting up backend..."
    cd backend
    uv sync
    cd ..
else
    # Ensure dependencies are up to date
    cd backend
    uv sync --quiet
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  Frontend dependencies not found. Installing..."
    cd frontend
    npm install
    cd ..
fi

# Check if .env file exists in backend
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Backend .env file not found."
    if [ -f "backend/.env.example" ]; then
        echo "📋 Creating .env from .env.example..."
        cp backend/.env.example backend/.env
        echo "⚠️  Please edit backend/.env and add your ANTHROPIC_API_KEY"
    else
        echo "❌ Please create backend/.env with your ANTHROPIC_API_KEY"
        exit 1
    fi
fi

# Initialize AWS resources (DynamoDB tables, S3 bucket)
source "$SCRIPT_DIR/init-aws.sh"
init_aws_resources

# Create directories
mkdir -p .pids logs

# Create isolated agent workspaces directory (for skill isolation)
# Default location, can be overridden via AGENT_WORKSPACES_DIR in backend/.env
AGENT_WORKSPACES_DIR="${AGENT_WORKSPACES_DIR:-$SCRIPT_DIR/workspaces}"
mkdir -p "$AGENT_WORKSPACES_DIR"
echo "📁 Agent workspaces: $AGENT_WORKSPACES_DIR"

# Start backend
echo ""
echo "🔧 Starting backend (FastAPI)..."
cd backend
# source .venv/bin/activate
nohup uv run main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../.pids/backend.pid
cd ..

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check logs/backend.log"
        exit 1
    fi
    sleep 1
done

# Start frontend (bind to 0.0.0.0 for public access)
echo "🎨 Starting frontend (Vite)..."
cd frontend
nohup npm run dev -- --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Frontend failed to start. Check logs/frontend.log"
        exit 1
    fi
    sleep 1
done

echo ""
echo "✨ AI Agent Platform is running!"
echo ""
echo "📍 Frontend: http://localhost:5173 (or http://<your-ip>:5173 for public access)"
echo "📍 Backend:  http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 To stop: ./stop.sh"
echo ""
