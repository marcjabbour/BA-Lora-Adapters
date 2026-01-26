#!/bin/bash

# Start Backend Server Script

echo "========================================="
echo "  Starting LoRA Training Pipeline Backend"
echo "========================================="
echo ""

# Change to backend directory
cd backend || { echo "Error: backend directory not found"; exit 1; }

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || { echo "Error: Failed to activate venv"; exit 1; }

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "Please edit backend/.env and add your OPENAI_API_KEY"
    exit 1
fi

# Start the backend
echo "Starting FastAPI server..."
echo "Backend will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m app.main
