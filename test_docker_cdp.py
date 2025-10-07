#!/usr/bin/env python3
"""
Test script for Chrome DevTools Protocol (CDP) connection in Docker/Kasm environment
"""
import os
import requests
import subprocess
import time
from pathlib import Path

def detect_environment():
    """Detect the runtime environment"""
    if os.path.exists('/.dockerenv'):
        return 'docker'
    elif os.path.exists('/Applications/Google Chrome.app'):
        return 'macos'
    else:
        return 'linux'

def get_chrome_path(env):
    """Get Chrome executable path based on environment"""
    if env == 'docker':
        # Common paths in Docker containers
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chrome',
            '/usr/bin/chromium-browser',
            '/opt/google/chrome/chrome'
        ]
    elif env == 'macos':
        paths = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    else:
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chrome',
            '/usr/bin/chromium-browser'
        ]
    
    for path in paths:
        if Path(path).exists():
            return path
    return None

def test_docker_cdp_connection():
    """Test connecting to Chrome via CDP in Docker environment"""
    print("🐳 Chrome DevTools Protocol (CDP) - Docker/Kasm Test")
    print("=" * 60)
    
    # Detect environment
    env = detect_environment()
    print(f"Environment detected: {env}")
    
    # Get Chrome path
    chrome_path = get_chrome_path(env)
    if not chrome_path:
        print("❌ Chrome executable not found")
        print("   Make sure Chrome is installed in the container")
        return
    
    print(f"✅ Chrome found at: {chrome_path}")
    
    # Check if Chrome is running with remote debugging
    cdp_port = 9222
    
    def is_chrome_debug_running():
        try:
            response = requests.get(f"http://127.0.0.1:{cdp_port}/json/version", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    print(f"\n1. Checking if Chrome is running with remote debugging on port {cdp_port}...")
    
    if is_chrome_debug_running():
        print("✅ Chrome with remote debugging is already running!")
        
        # Get CDP info
        try:
            response = requests.get(f"http://127.0.0.1:{cdp_port}/json/version", timeout=3)
            info = response.json()
            print(f"   Chrome Version: {info.get('Browser', 'Unknown')}")
            print(f"   WebSocket URL: {info.get('webSocketDebuggerUrl', 'Not found')}")
        except Exception as e:
            print(f"   ⚠️ Could not get Chrome info: {e}")
            
    else:
        print("❌ Chrome with remote debugging is not running")
        print("\n🚀 Starting Chrome with remote debugging...")
        
        # Docker-specific Chrome arguments
        chrome_args = [
            chrome_path,
            f"--remote-debugging-port={cdp_port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--user-data-dir=/tmp/chrome-automation"
        ]
        
        # Add Docker-specific arguments if in container
        if env == 'docker':
            chrome_args.extend([
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ])
            print("   Using Docker-specific arguments")
        
        try:
            print(f"   Launching: {chrome_path}")
            print(f"   Arguments: {' '.join(chrome_args[1:])}")
            
            process = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for Chrome to start
            print("   Waiting for Chrome to start with remote debugging...")
            for i in range(15):
                time.sleep(1)
                if is_chrome_debug_running():
                    print(f"✅ Chrome started successfully after {i+1} seconds!")
                    break
                print(f"   Waiting... ({i+1}/15)")
            else:
                print("❌ Chrome failed to start with remote debugging")
                return
                
        except Exception as e:
            print(f"❌ Failed to start Chrome: {e}")
            return
    
    # Test Playwright CDP connection
    print(f"\n2. Testing Playwright CDP connection...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Get WebSocket URL
            response = requests.get(f"http://127.0.0.1:{cdp_port}/json/version", timeout=3)
            info = response.json()
            ws_url = info["webSocketDebuggerUrl"]
            
            print(f"   Connecting to: {ws_url}")
            
            # Connect to Chrome
            browser = p.chromium.connect_over_cdp(ws_url)
            print("✅ Successfully connected to Chrome via CDP!")
            
            # Get or create context
            if browser.contexts:
                context = browser.contexts[0]
                print(f"   Using existing context (has {len(browser.contexts)} contexts)")
            else:
                context = browser.new_context()
                print("   Created new context")
            
            # Test page creation and navigation
            page = context.new_page()
            print("   Created new page")
            
            page.goto("https://httpbin.org/user-agent")
            print("   Navigated to test page")
            
            # Check user agent to verify we're using Chrome
            user_agent = page.evaluate("navigator.userAgent")
            if "Chrome" in user_agent:
                print(f"✅ User agent confirms Chrome: {user_agent[:50]}...")
            else:
                print(f"⚠️ Unexpected user agent: {user_agent[:50]}...")
            
            page.close()
            print("✅ Page closed successfully")
            
            # Note: Don't close browser since it's external
            print("   Browser connection maintained (external Chrome stays open)")
            
    except ImportError:
        print("❌ Playwright not installed. Run: pip install playwright")
    except Exception as e:
        print(f"❌ CDP connection failed: {e}")
        
    print(f"\n3. Configuration summary...")
    
    try:
        import configs
        cdp_enabled = configs.BROWSER_CONFIG.get('use_cdp_connection', False)
        cdp_port_config = configs.BROWSER_CONFIG.get('cdp_port', 9222)
        chrome_path_config = configs.BROWSER_CONFIG.get('chrome_path', 'Not set')
        
        print(f"   Environment: {env}")
        print(f"   CDP Connection Enabled: {cdp_enabled}")
        print(f"   CDP Port: {cdp_port_config}")
        print(f"   Chrome Path (config): {chrome_path_config}")
        print(f"   Chrome Path (detected): {chrome_path}")
        
        if cdp_enabled:
            print("✅ Your app is configured to use CDP connections!")
            if chrome_path_config != chrome_path:
                print(f"⚠️ Chrome path mismatch - update configs.py to use: {chrome_path}")
        else:
            print("⚠️ CDP connections are disabled in configs.py")
            print("   Set 'use_cdp_connection': True to enable")
            
    except Exception as e:
        print(f"⚠️ Could not load config: {e}")

def show_docker_instructions():
    """Show Docker-specific instructions"""
    print(f"\n" + "=" * 60)
    print("🐳 DOCKER/KASM ENVIRONMENT SETUP")
    print("=" * 60)
    print()
    print("In the Kasm/Docker environment:")
    print()
    print("1. Chrome should already be available in the container")
    print("2. Start Chrome with debugging:")
    print("   ./start_chrome_docker.sh")
    print()
    print("3. Or manually:")
    print("   /usr/bin/google-chrome \\")
    print("   --remote-debugging-port=9222 \\")
    print("   --remote-allow-origins=* \\")
    print("   --no-sandbox \\")
    print("   --disable-dev-shm-usage \\")
    print("   --disable-gpu &")
    print()
    print("4. Verify debugging is working:")
    print("   curl http://127.0.0.1:9222/json/version")
    print()
    print("5. Start your automation server:")
    print("   PORT=3000 python3 server.py")
    print()
    print("🖥️ VNC Access:")
    print("   - Use VNC to see and interact with the Chrome browser")
    print("   - Automation will connect to the same Chrome instance")
    print("   - You can manually use Chrome while automation is idle")

if __name__ == "__main__":
    test_docker_cdp_connection()
    show_docker_instructions()