#!/bin/bash

# Check and Clean Ports Script

echo "========================================="
echo "  Port Status Checker"
echo "========================================="
echo ""

# Check port 8000 (backend)
echo "Checking port 8000 (backend)..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "❌ Port 8000 is IN USE"
    echo ""
    lsof -i:8000
    echo ""
    read -p "Kill the process on port 8000? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        echo "✅ Process killed"
    fi
else
    echo "✅ Port 8000 is FREE"
fi

echo ""

# Check port 5173 (frontend)
echo "Checking port 5173 (frontend)..."
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo "❌ Port 5173 is IN USE"
    echo ""
    lsof -i:5173
    echo ""
    read -p "Kill the process on port 5173? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:5173 | xargs kill -9 2>/dev/null
        echo "✅ Process killed"
    fi
else
    echo "✅ Port 5173 is FREE"
fi

echo ""
echo "========================================="
echo "  Port check complete!"
echo "========================================="
