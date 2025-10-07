#!/bin/bash
# Start server on different ports

echo "🚀 FB Auto-Post Server Launcher"
echo "================================"

# Check if requirements are installed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installing requirements..."
    pip3 install -r requirements.txt
fi

echo ""
echo "Choose a port configuration:"
echo "1) Default (localhost:8000)"
echo "2) Development (localhost:3000)"  
echo "3) Local network (0.0.0.0:3000)"
echo "4) Custom port"
echo ""

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "🌐 Starting on http://localhost:8000"
        python3 server.py
        ;;
    2)
        echo "🌐 Starting on http://localhost:3000"
        PORT=3000 HOST=127.0.0.1 python3 server.py
        ;;
    3)
        echo "🌐 Starting on http://0.0.0.0:3000 (accessible from network)"
        PORT=3000 HOST=0.0.0.0 python3 server.py
        ;;
    4)
        read -p "Enter port number: " port
        read -p "Enter host (default: 0.0.0.0): " host
        host=${host:-0.0.0.0}
        echo "🌐 Starting on http://$host:$port"
        PORT=$port HOST=$host python3 server.py
        ;;
    *)
        echo "❌ Invalid choice. Starting on default port 8000"
        python3 server.py
        ;;
esac