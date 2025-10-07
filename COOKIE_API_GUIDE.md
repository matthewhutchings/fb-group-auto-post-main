# Non-Blocking Cookie Generation API

## Overview

The API now supports non-blocking cookie generation, where the browser opens in the background and the API returns immediately. This allows for a better user experience when setting up authentication.

## New Endpoints

### 1. Generate Cookies (Non-blocking)
```http
POST /generate-cookies
Content-Type: application/json

{
  "platform": "facebook"
}
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "platform": "facebook", 
  "status": "started",
  "message": "Cookie generation started. Browser will open for manual login. Use /cookie-status/{session_id} to check progress.",
  "started_at": "2025-10-07T12:00:00Z"
}
```

### 2. Check Cookie Generation Status
```http
GET /cookie-status/{session_id}
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "platform": "facebook",
  "status": "completed",
  "message": "Cookies generated successfully for facebook",
  "started_at": "2025-10-07T12:00:00Z",
  "completed_at": "2025-10-07T12:05:00Z"
}
```

**Status Values:**
- `started` - Cookie generation initiated
- `in_progress` - Browser opened, waiting for login
- `completed` - Cookies saved successfully
- `failed` - Error occurred during generation
- `not_found` - Session ID not found

### 3. Run Tasks (Unchanged)
```http
POST /run
Content-Type: application/json

{
  "plan": [
    {
      "platform": "facebook",
      "task": "post_group", 
      "target": {"name": "Test Group", "username": "test-group"},
      "content": "Your post content"
    }
  ],
  "headless": true
}
```

## Workflow

### First Time Setup (Generate Cookies)

1. **Start Cookie Generation**
   ```bash
   curl -X POST http://localhost:8000/generate-cookies \
     -H "Content-Type: application/json" \
     -d '{"platform": "facebook"}'
   ```

2. **API Returns Immediately**
   ```json
   {
     "session_id": "abc123...",
     "status": "started",
     "message": "Browser will open for manual login"
   }
   ```

3. **Browser Opens Automatically**
   - Chrome/browser window opens
   - Navigates to Facebook login page
   - User logs in manually

4. **Monitor Progress**
   ```bash
   curl http://localhost:8000/cookie-status/abc123...
   ```

5. **Poll Until Complete**
   ```json
   {
     "status": "completed",
     "message": "Cookies generated successfully"
   }
   ```

### Regular Usage (With Saved Cookies)

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "plan": [
      {
        "platform": "facebook",
        "task": "post_group",
        "target": {"name": "My Group", "username": "my-group"},
        "content": "Hello world!"
      }
    ],
    "headless": true
  }'
```

## Implementation Details

### Background Processing
- Cookie generation runs in a separate thread
- API responds immediately with session tracking
- Browser process is managed independently

### Login Detection
The system automatically detects successful login by monitoring:
- URL changes (away from login page)
- Presence of logged-in UI elements
- Facebook-specific indicators

### Cookie Storage
- Cookies saved to `sessions/{platform}.json`
- Automatically loaded for subsequent runs
- No manual file management needed

### Error Handling
- 10-minute timeout for login
- Graceful failure with error messages
- Session tracking for debugging

## Benefits

1. **Non-blocking**: API returns immediately
2. **Automatic**: Browser opens without manual intervention
3. **Trackable**: Session IDs for monitoring progress
4. **Robust**: Smart login detection
5. **Compatible**: Existing `/run` endpoint unchanged

## Example Client Code

```python
import requests
import time

def setup_cookies(platform="facebook"):
    # Start cookie generation
    response = requests.post("http://localhost:8000/generate-cookies", 
                           json={"platform": platform})
    session_id = response.json()["session_id"]
    
    print(f"Browser opening for {platform} login...")
    print(f"Session ID: {session_id}")
    
    # Poll for completion
    while True:
        status_response = requests.get(f"http://localhost:8000/cookie-status/{session_id}")
        status = status_response.json()["status"]
        
        if status == "completed":
            print("✅ Cookies saved! Ready to run tasks.")
            break
        elif status == "failed":
            print("❌ Cookie generation failed")
            break
        
        time.sleep(2)  # Check every 2 seconds

def run_task():
    response = requests.post("http://localhost:8000/run", json={
        "plan": [{
            "platform": "facebook",
            "task": "post_group",
            "target": {"name": "Test", "username": "test"},
            "content": "Hello from API!"
        }]
    })
    return response.json()
```