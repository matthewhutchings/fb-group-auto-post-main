#!/usr/bin/env python3
"""
Test script for the improved cookie generation with manual control
"""
import requests
import json
import time

BASE_URL = "http://localhost:3000"

def test_manual_cookie_generation():
    """Test manual cookie generation with user control"""
    print("=== Manual Cookie Generation (Recommended) ===")
    
    # Step 1: Start manual cookie generation
    url = f"{BASE_URL}/generate-cookies"
    headers = {"Content-Type": "application/json"}
    
    request_data = {
        "platform": "facebook",
        "manual_confirmation": True  # This keeps browser open until you manually save
    }
    
    print("1. Starting manual cookie generation...")
    print(f"POST {url}")
    print(json.dumps(request_data, indent=2))
    
    # Uncomment to make actual request:
    # response = requests.post(url, headers=headers, json=request_data)
    # result = response.json()
    # session_id = result["session_id"]
    # print(f"✅ Started! Session ID: {session_id}")
    # print(f"Message: {result['message']}")
    # print()
    # print("📋 Next steps:")
    # print("1. Browser will open to Facebook login")
    # print("2. Log in manually at your own pace")
    # print("3. When ready, call:")
    # print(f"   POST {BASE_URL}/cookie-save/{session_id}")
    # print("4. Check status:")
    # print(f"   GET {BASE_URL}/cookie-status/{session_id}")
    
    # Mock for demonstration
    mock_session_id = "manual-123"
    print(f"✅ Started! Session ID: {mock_session_id}")
    print("📋 After login, save cookies with:")
    print(f"POST {BASE_URL}/cookie-save/{mock_session_id}")

def test_auto_cookie_generation():
    """Test automatic cookie generation with improved detection"""
    print("\n=== Automatic Cookie Generation (Improved) ===")
    
    url = f"{BASE_URL}/generate-cookies"
    headers = {"Content-Type": "application/json"}
    
    request_data = {
        "platform": "facebook",
        "manual_confirmation": False  # Auto-detection (default)
    }
    
    print("1. Starting automatic cookie generation...")
    print(f"POST {url}")
    print(json.dumps(request_data, indent=2))
    print()
    print("This will:")
    print("✅ Open browser with stricter login detection")
    print("✅ Wait for clear evidence of successful login")
    print("✅ Require both UI elements AND navigation away from login")
    print("✅ Save cookies automatically when login is confirmed")

def demo_manual_save():
    """Demo the manual save process"""
    print("\n=== Manual Save Process ===")
    
    session_id = "your-session-id-here"
    
    print("After logging in manually:")
    print(f"1. Save cookies: POST {BASE_URL}/cookie-save/{session_id}")
    print(f"2. Check status: GET {BASE_URL}/cookie-status/{session_id}")
    print()
    print("Example curl commands:")
    print(f"curl -X POST {BASE_URL}/cookie-save/{session_id}")
    print(f"curl {BASE_URL}/cookie-status/{session_id}")

def main():
    print("🍪 Improved Cookie Generation API")
    print("=" * 50)
    
    print("\n🚀 TWO METHODS AVAILABLE:")
    print()
    print("METHOD 1: MANUAL CONTROL (Recommended)")
    print("- Browser opens and stays open")
    print("- You login at your own pace") 
    print("- You trigger cookie save when ready")
    print("- No risk of premature closing")
    print()
    print("METHOD 2: AUTO-DETECTION (Improved)")
    print("- Browser opens with better detection")
    print("- Waits for clear login evidence")
    print("- Saves cookies automatically")
    print("- More reliable than before")
    
    print("\n" + "=" * 50)
    
    test_manual_cookie_generation()
    test_auto_cookie_generation() 
    demo_manual_save()
    
    print("\n" + "=" * 50)
    print("🔧 API ENDPOINTS:")
    print(f"POST {BASE_URL}/generate-cookies")
    print("  - platform: 'facebook'")
    print("  - manual_confirmation: true/false")
    print()
    print(f"POST {BASE_URL}/cookie-save/{{session_id}}")
    print("  - Manually save cookies after login")
    print()
    print(f"GET {BASE_URL}/cookie-status/{{session_id}}")
    print("  - Check generation status")
    
    print("\n💡 RECOMMENDATION:")
    print("Use manual_confirmation=true for the most reliable experience!")

if __name__ == "__main__":
    main()