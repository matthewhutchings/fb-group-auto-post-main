#!/usr/bin/env python3
"""
Test script to demonstrate the new cookie generation functionality
"""
import requests
import json

# Example request to generate cookies
def test_cookie_generation():
    url = "http://localhost:8000/run"
    headers = {
        "Content-Type": "application/json",
        # "X-API-Key": "your-api-key-here"  # uncomment if API key is required
    }
    
    # Request to generate cookies (this will open a browser for manual login)
    generate_cookies_request = {
        "plan": [
            {
                "platform": "facebook",
                "task": "post_group",  # any valid task
                "target": {
                    "name": "Test Group",
                    "username": "test-group"
                },
                "content": "Test post"
            }
        ],
        "headless": False,  # Must be False for manual login
        "generate_cookies": True  # NEW: This triggers cookie generation
    }
    
    print("=== Cookie Generation Request ===")
    print(json.dumps(generate_cookies_request, indent=2))
    print("\nThis will:")
    print("1. Open a browser window")
    print("2. Navigate to Facebook login page")
    print("3. Wait for you to log in manually")
    print("4. Save cookies to sessions/facebook.json")
    print("5. Skip the actual task execution")
    
    # Uncomment below to actually make the request
    # response = requests.post(url, headers=headers, json=generate_cookies_request)
    # print(f"Response: {response.status_code}")
    # print(json.dumps(response.json(), indent=2))

def test_normal_run():
    url = "http://localhost:8000/run"
    headers = {
        "Content-Type": "application/json",
        # "X-API-Key": "your-api-key-here"  # uncomment if API key is required
    }
    
    # Normal request using saved cookies
    normal_request = {
        "plan": [
            {
                "platform": "facebook",
                "task": "post_group",
                "target": {
                    "name": "Test Group",
                    "username": "test-group"
                },
                "content": "Test post content"
            }
        ],
        "headless": True,  # Can be True since we have saved cookies
        "generate_cookies": False  # Default: use existing cookies
    }
    
    print("\n=== Normal Run Request (using saved cookies) ===")
    print(json.dumps(normal_request, indent=2))
    print("\nThis will:")
    print("1. Load cookies from sessions/facebook.json")
    print("2. Execute the actual posting task")
    print("3. Return task results with video recordings")
    
    # Uncomment below to actually make the request
    # response = requests.post(url, headers=headers, json=normal_request)
    # print(f"Response: {response.status_code}")
    # print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    print("Cookie Generation API Test")
    print("=" * 50)
    
    test_cookie_generation()
    test_normal_run()
    
    print("\n" + "=" * 50)
    print("To use this functionality:")
    print("1. Start the server: python3 server.py")
    print("2. First time: Send request with generate_cookies=True")
    print("3. Subsequent runs: Send requests with generate_cookies=False (default)")