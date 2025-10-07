#!/usr/bin/env python3
"""
Test script for Chrome DevTools Protocol (CDP) connection
"""
import requests
import subprocess
import time
from pathlib import Path

def test_cdp_connection():
    """Test connecting to Chrome via CDP"""
    print("🌐 Chrome DevTools Protocol (CDP) Connection Test")
    print("=" * 60)
    
    # Check if Chrome is running with remote debugging
    cdp_port = 9222
    
    def is_chrome_debug_running():
        try:
            response = requests.get(f"http://127.0.0.1:{cdp_port}/json/version", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    print(f"1. Checking if Chrome is running with remote debugging on port {cdp_port}...")
    
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
        
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        if not Path(chrome_path).exists():
            print(f"❌ Chrome not found at: {chrome_path}")
            print("   Please install Google Chrome or update the path")
            return
        
        # Start Chrome with remote debugging
        chrome_args = [
            chrome_path,
            f"--remote-debugging-port={cdp_port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled"
        ]
        
        try:
            print(f"   Launching: {chrome_path}")
            print(f"   With args: --remote-debugging-port={cdp_port}")
            
            process = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for Chrome to start
            print("   Waiting for Chrome to start with remote debugging...")
            for i in range(10):
                time.sleep(1)
                if is_chrome_debug_running():
                    print(f"✅ Chrome started successfully after {i+1} seconds!")
                    break
                print(f"   Waiting... ({i+1}/10)")
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
        
        print(f"   CDP Connection Enabled: {cdp_enabled}")
        print(f"   CDP Port: {cdp_port_config}")
        
        if cdp_enabled:
            print("✅ Your app is configured to use CDP connections!")
        else:
            print("⚠️ CDP connections are disabled in configs.py")
            print("   Set 'use_cdp_connection': True to enable")
            
    except Exception as e:
        print(f"⚠️ Could not load config: {e}")

def show_manual_setup():
    """Show manual setup instructions"""
    print(f"\n" + "=" * 60)
    print("📖 MANUAL CHROME SETUP (Optional)")
    print("=" * 60)
    print()
    print("To manually start Chrome with remote debugging:")
    print()
    print("1. Close all Chrome instances")
    print("2. Start Chrome with debugging:")
    print('   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\')
    print('   --remote-debugging-port=9222 \\')
    print('   --remote-allow-origins=* \\')
    print('   --no-first-run \\')
    print('   --start-maximized')
    print()
    print("3. Verify it's working:")
    print("   curl http://127.0.0.1:9222/json/version")
    print()
    print("4. Your automation will connect to this Chrome instance")

if __name__ == "__main__":
    test_cdp_connection()
    show_manual_setup()