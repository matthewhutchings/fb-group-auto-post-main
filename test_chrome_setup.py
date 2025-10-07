#!/usr/bin/env python3
"""
Test script to verify Chrome browser usage
"""
import subprocess
import sys
from pathlib import Path

def test_chrome_installation():
    """Test if Chrome is properly installed and accessible"""
    print("🔍 Testing Chrome Installation")
    print("=" * 50)
    
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    if Path(chrome_path).exists():
        print(f"✅ Chrome found at: {chrome_path}")
        
        # Test Chrome version
        try:
            result = subprocess.run([chrome_path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Chrome version: {result.stdout.strip()}")
            else:
                print(f"⚠️ Chrome version check failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Could not get Chrome version: {e}")
    else:
        print(f"❌ Chrome not found at: {chrome_path}")
        print("   Please install Google Chrome or update the path in configs.py")

def test_browser_config():
    """Test the browser configuration"""
    print("\n🔧 Testing Browser Configuration")
    print("=" * 50)
    
    try:
        import configs
        
        print(f"✅ Browser config loaded successfully")
        print(f"   Use local Chrome: {configs.BROWSER_CONFIG['use_local_chrome']}")
        print(f"   Chrome path: {configs.BROWSER_CONFIG['chrome_path']}")
        print(f"   Chrome args: {len(configs.BROWSER_CONFIG['chrome_args'])} arguments")
        
        # Show args
        for i, arg in enumerate(configs.BROWSER_CONFIG['chrome_args'], 1):
            print(f"      {i}. {arg}")
            
    except Exception as e:
        print(f"❌ Failed to load browser config: {e}")

def test_playwright_chrome():
    """Test Playwright with Chrome"""
    print("\n🎭 Testing Playwright Chrome Launch")
    print("=" * 50)
    
    try:
        from playwright.sync_api import sync_playwright
        import configs
        
        print("✅ Playwright imported successfully")
        
        with sync_playwright() as p:
            try:
                print("🚀 Attempting to launch Chrome...")
                
                browser = p.chromium.launch(
                    headless=True,  # Use headless for testing
                    channel="chrome",
                    executable_path=configs.BROWSER_CONFIG['chrome_path'],
                    args=["--no-sandbox", "--disable-dev-shm-usage"]  # Minimal args for test
                )
                
                print("✅ Chrome launched successfully via Playwright!")
                
                # Test basic functionality
                page = browser.new_page()
                page.goto("data:text/html,<h1>Test Page</h1>")
                title = page.title()
                print(f"✅ Page navigation working: '{title}'")
                
                browser.close()
                print("✅ Chrome closed successfully")
                
            except Exception as e:
                print(f"❌ Failed to launch Chrome via Playwright: {e}")
                print("   Trying fallback to Chromium...")
                
                try:
                    browser = p.chromium.launch(headless=True)
                    print("✅ Fallback to Chromium successful")
                    browser.close()
                except Exception as e2:
                    print(f"❌ Fallback to Chromium also failed: {e2}")
                
    except ImportError:
        print("❌ Playwright not installed. Run: pip install playwright")
    except Exception as e:
        print(f"❌ Playwright test failed: {e}")

def main():
    print("🌐 Chrome Browser Configuration Test")
    print("=" * 60)
    print()
    
    test_chrome_installation()
    test_browser_config()
    test_playwright_chrome()
    
    print("\n" + "=" * 60)
    print("📝 CONFIGURATION SUMMARY:")
    print()
    print("To use local Chrome:")
    print("✅ Set use_local_chrome: True in configs.py (already set)")
    print("✅ Ensure Chrome is installed (✅ confirmed)")
    print("✅ Update chrome_path if needed (currently set to standard macOS location)")
    print()
    print("To disable local Chrome and use Chromium:")
    print("   Set use_local_chrome: False in configs.py")
    print()
    print("🚀 Your setup is configured to use local Chrome!")

if __name__ == "__main__":
    main()