#!/bin/bash

# Start Frontend Server Script

echo "========================================="
echo "  Starting LoRA Training Pipeline Frontend"
echo "========================================="
echo ""

# Change to frontend directory
cd frontend || { echo "Error: frontend directory not found"; exit 1; }

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found!"
    echo "Please run: npm install"
    exit 1
fi

# Start the frontend
echo "Starting Vite development server..."
echo "Frontend will be available at: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
