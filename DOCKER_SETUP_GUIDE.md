# Docker/Kasm Chrome Automation Setup

## 🐳 **Docker Environment Overview**

Your automation is running in a `kasmweb/chrome` Docker container, which provides:
- ✅ **Pre-installed Chrome browser**
- ✅ **VNC access for visual interaction**
- ✅ **Isolated environment**
- ✅ **Consistent runtime across deployments**

## 🔧 **Configuration for Docker**

Your `configs.py` is now configured for the Docker environment:

```python
BROWSER_CONFIG = {
    'use_cdp_connection': True,          # ✅ Connect to existing Chrome
    'cdp_port': 9222,                    # Standard debugging port
    'chrome_path': '/usr/bin/google-chrome',  # Chrome path in container
    'chrome_args': [
        '--no-sandbox',                  # Required for Docker
        '--disable-dev-shm-usage',       # Required for Docker  
        '--disable-gpu',                 # Optional for Docker
        '--remote-debugging-port=9222',   # Enable CDP
        '--remote-allow-origins=*',       # Allow connections
        # ... other optimization flags
    ]
}
```

## 🚀 **Setup Steps**

### **Step 1: Start Chrome with Remote Debugging**

In your Docker container, run:
```bash
# Make script executable
chmod +x start_chrome_docker.sh

# Start Chrome with debugging
./start_chrome_docker.sh
```

Or manually:
```bash
/usr/bin/google-chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --start-maximized \
  --user-data-dir=/tmp/chrome-automation &
```

### **Step 2: Verify Chrome is Ready**
```bash
curl http://127.0.0.1:9222/json/version
```

### **Step 3: Start Your Automation Server**
```bash
PORT=3000 python3 server.py
```

## 🖥️ **VNC Access**

The Kasm container provides VNC access:
- **View Chrome**: See the browser window through VNC
- **Manual Interaction**: You can manually use Chrome when automation is idle
- **Debugging**: Watch automation in real-time
- **Cookie Setup**: Manually login through VNC, then save cookies via API

## 🔄 **Workflow**

### **For Cookie Generation:**
1. **VNC**: Open VNC to see the Chrome browser
2. **API Call**: Generate cookies via API endpoint
3. **Manual Login**: Log into Facebook/platform through VNC
4. **Save**: Trigger cookie save through API
5. **Automation**: Run tasks using saved cookies

### **For Task Execution:**
1. **Load Cookies**: Automation loads saved cookies
2. **Connect**: Connects to the running Chrome via CDP
3. **Execute**: Performs automation tasks
4. **Monitor**: Watch through VNC if needed

## 🧪 **Testing Your Setup**

Run the Docker-specific test:
```bash
python3 test_docker_cdp.py
```

This will:
- ✅ Detect Docker environment
- ✅ Find Chrome installation
- ✅ Start Chrome with debugging if needed
- ✅ Test CDP connection
- ✅ Verify configuration

## 🔍 **API Usage Examples**

### **Generate Cookies (Manual Control)**
```bash
curl -X POST http://localhost:3000/generate-cookies \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "facebook",
    "manual_confirmation": true
  }'
```

**Process:**
1. Chrome opens to Facebook login (visible in VNC)
2. You login manually through VNC
3. Call save endpoint when ready:
```bash
curl -X POST http://localhost:3000/cookie-save/{session_id}
```

### **Run Automation Tasks**
```bash
curl -X POST http://localhost:3000/run \
  -H "Content-Type: application/json" \
  -d '{
    "plan": [
      {
        "platform": "facebook",
        "task": "post_group",
        "target": {"name": "Test Group", "username": "test-group"},
        "content": "Hello from Docker automation!"
      }
    ]
  }'
```

## 🛡️ **Docker-Specific Benefits**

| Feature | Benefit |
|---------|---------|
| **Isolated Environment** | No conflicts with host system |
| **Consistent Runtime** | Same environment every time |
| **VNC Access** | Visual debugging and manual control |
| **Pre-configured Chrome** | Ready-to-use browser setup |
| **Container Persistence** | Sessions survive container restarts |

## 🔧 **Troubleshooting**

### **Chrome won't start**
```bash
# Check if Chrome is available
ls -la /usr/bin/google-chrome

# Check processes
ps aux | grep chrome

# Kill existing processes
pkill -f chrome
```

### **CDP connection fails**
```bash
# Check if debugging endpoint is available
curl http://127.0.0.1:9222/json/version

# Check port availability
netstat -tlnp | grep 9222
```

### **VNC not showing Chrome**
- Ensure Chrome is started with `--start-maximized`
- Check if Chrome is running: `ps aux | grep chrome`
- Refresh VNC connection

## 🎯 **Advantages of Docker + CDP Setup**

1. **🔄 Persistent Browser**: Chrome stays open between automation runs
2. **👀 Visual Access**: See and control browser through VNC
3. **⚡ Fast Execution**: No browser startup delay
4. **🛡️ Isolated**: Contained environment for safety
5. **📱 Dual Control**: Both manual (VNC) and automated (API) access

Your Docker-based automation environment is now configured for optimal Chrome connectivity! 🌟