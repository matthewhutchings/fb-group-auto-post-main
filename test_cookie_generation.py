#!/usr/bin/env python3
"""
Test script to demonstrate the new non-blocking cookie generation functionality
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_non_blocking_cookie_generation():
    """Test the new non-blocking cookie generation endpoint"""
    print("=== Non-Blocking Cookie Generation ===")
    
    # Step 1: Start cookie generation
    url = f"{BASE_URL}/generate-cookies"
    headers = {
        "Content-Type": "application/json",
        # "X-API-Key": "your-api-key-here"  # uncomment if API key is required
    }
    
    request_data = {
        "platform": "facebook"
    }
    
    print("1. Starting cookie generation...")
    print(f"POST {url}")
    print(json.dumps(request_data, indent=2))
    
    # Uncomment to make actual request
    # response = requests.post(url, headers=headers, json=request_data)
    # if response.status_code == 200:
    #     result = response.json()
    #     session_id = result["session_id"]
    #     print(f"✅ Cookie generation started!")
    #     print(f"Session ID: {session_id}")
    #     print(f"Status: {result['status']}")
    #     print(f"Message: {result['message']}")
    #     
    #     # Step 2: Poll for status
    #     print("\n2. Polling for completion...")
    #     return poll_cookie_status(session_id)
    # else:
    #     print(f"❌ Failed: {response.status_code}")
    #     print(response.text)
    
    # Mock response for demonstration
    mock_session_id = "123e4567-e89b-12d3-a456-426614174000"
    print(f"✅ Cookie generation started!")
    print(f"Session ID: {mock_session_id}")
    print("Browser will open automatically for login...")
    return mock_session_id

def poll_cookie_status(session_id):
    """Poll the status endpoint until completion"""
    url = f"{BASE_URL}/cookie-status/{session_id}"
    headers = {
        # "X-API-Key": "your-api-key-here"  # uncomment if API key is required
    }
    
    print(f"Polling: GET {url}")
    
    # Uncomment to make actual requests
    # while True:
    #     response = requests.get(url, headers=headers)
    #     if response.status_code == 200:
    #         result = response.json()
    #         status = result["status"]
    #         print(f"Status: {status} - {result['message']}")
    #         
    #         if status in ["completed", "failed"]:
    #             return result
    #         elif status == "not_found":
    #             print("❌ Session not found")
    #             return None
    #         
    #         time.sleep(2)  # Wait 2 seconds before next poll
    #     else:
    #         print(f"❌ Error checking status: {response.status_code}")
    #         break
    
    # Mock progression for demonstration
    print("Status: started - Cookie generation started. Browser will open for manual login.")
    print("Status: in_progress - Browser opened, waiting for user login...")
    print("Status: completed - Cookies generated successfully for facebook")
    
    return {
        "session_id": session_id,
        "platform": "facebook",
        "status": "completed",
        "message": "Cookies generated successfully for facebook"
    }

def test_normal_run_with_cookies():
    """Test normal task execution using saved cookies"""
    print("\n=== Normal Run with Saved Cookies ===")
    
    url = f"{BASE_URL}/run"
    headers = {
        "Content-Type": "application/json",
        # "X-API-Key": "your-api-key-here"  # uncomment if API key is required
    }
    
    request_data = {
        "plan": [
            {
                "platform": "facebook",
                "task": "post_group",
                "target": {
                    "name": "Test Group",
                    "username": "test-group"
                },
                "content": "Test post using saved cookies"
            }
        ],
        "headless": True,  # Can be True since we have saved cookies
        "generate_cookies": False  # Use existing cookies (default)
    }
    
    print("POST /run")
    print(json.dumps(request_data, indent=2))
    print("\nThis will:")
    print("✅ Load cookies from sessions/facebook.json")
    print("✅ Execute the posting task automatically")
    print("✅ Return results with video recording")

def main():
    print("🍪 Non-Blocking Cookie Generation API Test")
    print("=" * 60)
    
    print("\n🚀 WORKFLOW:")
    print("1. Call /generate-cookies to start browser")
    print("2. API returns immediately with session_id")
    print("3. Browser opens in background for manual login")
    print("4. Poll /cookie-status/{session_id} to check progress")
    print("5. Once completed, use /run normally")
    
    print("\n" + "=" * 60)
    
    # Test cookie generation
    session_id = test_non_blocking_cookie_generation()
    
    if session_id:
        print(f"\n📊 Use this to check status:")
        print(f"GET {BASE_URL}/cookie-status/{session_id}")
        
        # Simulate polling
        result = poll_cookie_status(session_id)
        
        if result and result["status"] == "completed":
            print(f"\n✅ Cookie generation completed!")
            test_normal_run_with_cookies()
    
    print("\n" + "=" * 60)
    print("🔧 API ENDPOINTS:")
    print(f"POST {BASE_URL}/generate-cookies")
    print("  - Start cookie generation (non-blocking)")
    print(f"GET  {BASE_URL}/cookie-status/{{session_id}}")
    print("  - Check cookie generation progress")
    print(f"POST {BASE_URL}/run")
    print("  - Execute tasks (uses saved cookies)")
    
    print("\n📝 USAGE:")
    print("1. Start server: python3 server.py")
    print("2. Generate cookies: POST /generate-cookies")
    print("3. Monitor progress: GET /cookie-status/{session_id}")
    print("4. Run tasks: POST /run")

if __name__ == "__main__":
    main()