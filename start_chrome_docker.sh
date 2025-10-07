#!/bin/bash
# Start Chrome with remote debugging in Docker/Kasm environment

echo "🐳 Starting Chrome with Remote Debugging (Docker/Kasm)"
echo "====================================================="

# Check if we're in a Docker environment
if [ -f /.dockerenv ]; then
    echo "✅ Running in Docker environment"
    CHROME_PATH="/usr/bin/google-chrome"
elif [ -d "/Applications/Google Chrome.app" ]; then
    echo "✅ Running on macOS"
    CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    echo "🔍 Detecting Chrome installation..."
    CHROME_PATH=$(which google-chrome || which chrome || which chromium-browser || echo "")
    if [ -z "$CHROME_PATH" ]; then
        echo "❌ Chrome not found"
        exit 1
    fi
    echo "✅ Found Chrome at: $CHROME_PATH"
fi

# Kill existing Chrome processes (if any)
echo "1. Stopping existing Chrome processes..."
pkill -f "chrome" 2>/dev/null || true
pkill -f "Chrome" 2>/dev/null || true
sleep 2

# Check if port 9222 is available
if command -v lsof >/dev/null 2>&1; then
    if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 9222 is still in use. Waiting..."
        sleep 3
    fi
fi

# Docker/Kasm specific arguments
DOCKER_ARGS=""
if [ -f /.dockerenv ]; then
    DOCKER_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"
    echo "🐳 Using Docker-specific Chrome arguments"
fi

# Start Chrome with remote debugging
echo "2. Starting Chrome with remote debugging..."
echo "   Chrome path: $CHROME_PATH"
echo "   Port: 9222"

"$CHROME_PATH" \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --no-first-run \
  --start-maximized \
  --disable-blink-features=AutomationControlled \
  --disable-web-security \
  --disable-features=VizDisplayCompositor \
  $DOCKER_ARGS \
  --user-data-dir=/tmp/chrome-automation &

CHROME_PID=$!

# Wait for Chrome to start
echo "3. Waiting for Chrome to start..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
        echo "✅ Chrome started successfully!"
        echo ""
        echo "📊 Chrome Info:"
        if command -v python3 >/dev/null 2>&1; then
            curl -s http://127.0.0.1:9222/json/version | python3 -m json.tool 2>/dev/null || echo "Chrome debugging available"
        else
            curl -s http://127.0.0.1:9222/json/version
        fi
        echo ""
        echo "🚀 Chrome is ready for automation!"
        echo "   - Remote debugging: http://127.0.0.1:9222"
        echo "   - Chrome PID: $CHROME_PID"
        if [ -f /.dockerenv ]; then
            echo "   - Running in Docker container"
            echo "   - VNC access available for manual interaction"
        fi
        echo ""
        echo "📖 Next steps:"
        echo "   PORT=3000 python3 server.py"
        echo ""
        echo "📝 To keep Chrome running, this script will continue..."
        
        # Keep the script running to maintain Chrome process
        wait $CHROME_PID
        exit 0
    fi
    echo "   Waiting... ($i/15)"
    sleep 1
done

echo "❌ Chrome failed to start with remote debugging"
echo ""
echo "🔧 Troubleshooting:"
echo "   1. Check Chrome installation: $CHROME_PATH"
echo "   2. Verify port 9222 is available"
echo "   3. Check Docker permissions (if in container)"
echo ""
echo "💡 Manual start command:"
echo "\"$CHROME_PATH\" --remote-debugging-port=9222 --remote-allow-origins=* $DOCKER_ARGS"