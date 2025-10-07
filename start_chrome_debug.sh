#!/bin/bash
# Start Chrome with remote debugging for automation

echo "🌐 Starting Chrome with Remote Debugging"
echo "========================================"

# Kill existing Chrome processes
echo "1. Stopping existing Chrome processes..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# Check if port 9222 is available
if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 9222 is still in use. Waiting..."
    sleep 3
fi

# Start Chrome with remote debugging
echo "2. Starting Chrome with remote debugging..."
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --no-first-run \
  --start-maximized \
  --disable-blink-features=AutomationControlled \
  --user-data-dir="$HOME/.chrome-automation" &

# Wait for Chrome to start
echo "3. Waiting for Chrome to start..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
        echo "✅ Chrome started successfully!"
        echo ""
        echo "📊 Chrome Info:"
        curl -s http://127.0.0.1:9222/json/version | python3 -m json.tool 2>/dev/null || echo "Chrome version info available at http://127.0.0.1:9222/json/version"
        echo ""
        echo "🚀 Chrome is ready for automation!"
        echo "   - Remote debugging: http://127.0.0.1:9222"
        echo "   - You can now start your automation server"
        echo "   - Chrome will stay open until you close it manually"
        echo ""
        echo "📖 Next steps:"
        echo "   PORT=3000 python3 server.py"
        exit 0
    fi
    echo "   Waiting... ($i/10)"
    sleep 1
done

echo "❌ Chrome failed to start with remote debugging"
echo ""
echo "🔧 Troubleshooting:"
echo "   1. Make sure Chrome is installed"
echo "   2. Try closing all Chrome windows manually"
echo "   3. Check if another process is using port 9222"
echo ""
echo "💡 Manual start command:"
echo '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --remote-allow-origins=*'