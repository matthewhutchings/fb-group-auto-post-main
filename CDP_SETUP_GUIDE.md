# Chrome DevTools Protocol (CDP) Setup Guide

## 🎯 **What is CDP Connection?**

Instead of launching a new Chrome browser each time, your automation connects to an **already running Chrome instance** with remote debugging enabled. This provides:

- ✅ **Persistent Browser**: Chrome stays open between automation runs
- ✅ **Better Performance**: No browser startup delay
- ✅ **Session Persistence**: Login sessions can persist across runs
- ✅ **External Control**: You can manually use the browser while automation is idle

## 🔧 **Setup Instructions**

### **Step 1: Close All Chrome Instances**
```bash
# Kill all Chrome processes
pkill -f "Google Chrome"
```

### **Step 2: Start Chrome with Remote Debugging**
```bash
# Start Chrome with remote debugging enabled
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --no-first-run \
  --start-maximized \
  --disable-blink-features=AutomationControlled
```

### **Step 3: Verify Chrome is Ready**
```bash
# Test the debugging endpoint
curl http://127.0.0.1:9222/json/version
```

You should see JSON output with Chrome version info.

### **Step 4: Configure Your App**
Your app is already configured to use CDP! The settings in `configs.py`:
```python
BROWSER_CONFIG = {
    'use_cdp_connection': True,    # ✅ Enabled
    'cdp_port': 9222,             # Default debugging port
    # ... other settings
}
```

## 🚀 **Usage**

Once Chrome is running with remote debugging:

1. **Start your API server**:
   ```bash
   PORT=3000 python3 server.py
   ```

2. **Generate cookies** (connects to existing Chrome):
   ```bash
   curl -X POST http://localhost:3000/generate-cookies \
     -H "Content-Type: application/json" \
     -d '{"platform": "facebook", "manual_confirmation": true}'
   ```

3. **Run tasks** (uses existing Chrome):
   ```bash
   curl -X POST http://localhost:3000/run \
     -H "Content-Type: application/json" \
     -d '{"plan": [...]}'
   ```

## 🔍 **Troubleshooting**

### **Problem: Chrome won't start with debugging**
**Solution**: Kill existing Chrome processes first
```bash
pkill -f "Google Chrome"
sleep 2
# Then start with debugging
```

### **Problem: Connection refused on port 9222**
**Solution**: Chrome isn't running with debugging
```bash
# Check if the endpoint is accessible
curl http://127.0.0.1:9222/json/version
```

### **Problem: Want to disable CDP**
**Solution**: Set `use_cdp_connection: False` in `configs.py`

### **Problem: Different port needed**
**Solution**: Update `cdp_port` in `configs.py` and start Chrome with that port

## 🔄 **Switching Between Methods**

### **Use CDP Connection** (Current Setup):
```python
# In configs.py
BROWSER_CONFIG = {
    'use_cdp_connection': True,    # Connect to existing Chrome
    'cdp_port': 9222,
    # ...
}
```

### **Use Direct Launch**:
```python
# In configs.py
BROWSER_CONFIG = {
    'use_cdp_connection': False,   # Launch new browser each time
    # ...
}
```

## 🎯 **Benefits Summary**

| Method | Browser Startup | Session Persistence | Performance | Control |
|--------|----------------|-------------------|-------------|---------|
| **CDP Connection** | ⚡ Instant | ✅ Yes | 🚀 Fast | 👤 Manual + Auto |
| **Direct Launch** | 🐌 Slow | ❌ No | 📈 Slower | 🤖 Auto Only |

## 🧪 **Testing Your Setup**

Run the test script to verify everything is working:
```bash
python3 test_cdp_connection.py
```

This will:
1. Check if Chrome is running with debugging
2. Start Chrome if needed
3. Test Playwright CDP connection
4. Verify configuration

Your automation is now ready to use persistent Chrome connections! 🌟