#!/bin/bash
echo "========================================"
echo "   SkillSync AI - Setup and Run"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Install from https://python.org"
    exit 1
fi

echo "[1/3] Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

echo ""
echo "[2/3] Dependencies installed!"
echo ""
echo "[3/3] Starting SkillSync AI..."
echo ""
echo "========================================"
echo "  App running at: http://localhost:5000"
echo "  Open browser and visit that URL"
echo "  Press CTRL+C to stop"
echo "========================================"
echo ""
python3 app.py
