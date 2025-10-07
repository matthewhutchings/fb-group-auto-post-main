# server.py
import os
import requests
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, constr

from engine.runner import \
    RulesRunner  # <-- runner that returns status/steps/logs/video
# local imports
from platforms.loader import load_rules
import configs

# ------------ Config ------------
API_KEY = os.environ.get("POSTER_API_KEY")           # simple header auth
ALLOW_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "*")

PUBLIC_DIR = Path("recordings_public")               # where videos are exposed
PUBLIC_DIR.mkdir(exist_ok=True)

# Cookie generation session tracking
cookie_sessions: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Multi Poster API", version="1.2.0")

# Serve recorded videos at /files/...
app.mount("/files", StaticFiles(directory=str(PUBLIC_DIR)), name="files")

# Optional CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOW_ORIGINS.split(",")] if ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------ Auth ------------
def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# ------------ Models ------------
Str50 = constr(strip_whitespace=True, min_length=1, max_length=50)

class Target(BaseModel):
    name: str = Field(..., description="Friendly name for logging / filenames")
    username: str = Field(..., description="Slug/handle (e.g., group username, subreddit)")

class PlanItem(BaseModel):
    platform: Str50
    task: Str50
    target: Target
    content: str = Field("", description="Text content to fill/paste")

class RunRequest(BaseModel):
    plan: List[PlanItem] = Field(..., description="List of tasks to execute")
    headless: bool = False
    recordings_dir: Optional[str] = Field(default="recordings", description="Where raw .webm are recorded")
    generate_cookies: bool = Field(default=False, description="Whether to generate new cookies instead of using existing ones")

class RunResponse(BaseModel):
    started_at: str
    finished_at: str
    tasks: int
    details: List[Dict[str, Any]]  # each has: platform, task, target, status, message, steps[], logs[], video_url, video_local

class CookieGenerationRequest(BaseModel):
    platform: Str50 = Field(..., description="Platform to generate cookies for (e.g., 'facebook')")
    manual_confirmation: bool = Field(default=False, description="If true, waits for manual confirmation instead of auto-detection")
    
class CookieGenerationResponse(BaseModel):
    session_id: str
    platform: str
    status: str  # "started", "completed", "failed"
    message: str
    started_at: str
    
class CookieStatusResponse(BaseModel):
    session_id: str
    platform: str
    status: str  # "started", "completed", "failed", "not_found"
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

# ------------ Utilities ------------
def _get_cdp_ws_url(port: int = 9222) -> str:
    """Get Chrome DevTools Protocol WebSocket URL"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=3)
        response.raise_for_status()
        info = response.json()
        return info["webSocketDebuggerUrl"]
    except Exception as e:
        raise Exception(f"Failed to get CDP WebSocket URL: {e}")


def _is_chrome_running_with_debug(port: int = 9222) -> bool:
    """Check if Chrome is running with remote debugging enabled"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
        return response.status_code == 200
    except:
        return False


def _start_chrome_with_debug(chrome_path: str, port: int = 9222, args: List[str] = None) -> subprocess.Popen:
    """Start Chrome with remote debugging enabled"""
    if args is None:
        args = []
    
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--disable-blink-features=AutomationControlled"
    ] + args
    
    return subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _connect_or_launch_browser(p, headless=False):
    """Connect to existing Chrome via CDP or launch new browser"""
    
    if configs.BROWSER_CONFIG.get('use_cdp_connection', False):
        # Try to connect to existing Chrome with remote debugging
        cdp_port = configs.BROWSER_CONFIG.get('cdp_port', 9222)
        
        if _is_chrome_running_with_debug(cdp_port):
            try:
                print(f"[Cookie Gen] Connecting to existing Chrome on port {cdp_port}")
                ws_url = _get_cdp_ws_url(cdp_port)
                browser = p.chromium.connect_over_cdp(ws_url)
                print(f"[Cookie Gen] ✅ Connected to existing Chrome via CDP")
                return browser
            except Exception as e:
                print(f"[Cookie Gen] ⚠️ Failed to connect to existing Chrome: {e}")
        else:
            print(f"[Cookie Gen] No Chrome found with remote debugging on port {cdp_port}")
            
            # Try to start Chrome with remote debugging
            if configs.BROWSER_CONFIG.get('use_local_chrome', False):
                try:
                    print(f"[Cookie Gen] Starting Chrome with remote debugging on port {cdp_port}")
                    chrome_path = configs.BROWSER_CONFIG['chrome_path']
                    chrome_args = configs.BROWSER_CONFIG.get('chrome_args', [])
                    
                    # Filter out conflicting args and add our required ones
                    filtered_args = [arg for arg in chrome_args 
                                   if not arg.startswith('--remote-debugging')]
                    
                    _start_chrome_with_debug(chrome_path, cdp_port, filtered_args)
                    
                    # Wait for Chrome to start
                    for i in range(10):  # Wait up to 10 seconds
                        time.sleep(1)
                        if _is_chrome_running_with_debug(cdp_port):
                            print(f"[Cookie Gen] Chrome started successfully")
                            break
                    else:
                        raise Exception("Chrome failed to start with remote debugging")
                    
                    # Connect to the newly started Chrome
                    ws_url = _get_cdp_ws_url(cdp_port)
                    browser = p.chromium.connect_over_cdp(ws_url)
                    print(f"[Cookie Gen] ✅ Connected to newly started Chrome via CDP")
                    return browser
                    
                except Exception as e:
                    print(f"[Cookie Gen] ⚠️ Failed to start Chrome with remote debugging: {e}")
    
    # Fallback to launching browser directly
    try:
        if configs.BROWSER_CONFIG.get('use_local_chrome', False):
            print(f"[Cookie Gen] Launching Chrome directly")
            browser = p.chromium.launch(
                headless=headless,
                channel="chrome",
                executable_path=configs.BROWSER_CONFIG['chrome_path'],
                args=configs.BROWSER_CONFIG['chrome_args']
            )
        else:
            # Try Chrome channel without explicit path
            browser = p.chromium.launch(
                headless=headless,
                channel="chrome", 
                args=["--start-maximized"]
            )
    except Exception as e:
        print(f"[Cookie Gen] ⚠️ Failed to launch Chrome: {e}")
        print("[Cookie Gen] Falling back to Chromium...")
        browser = p.chromium.launch(
            headless=headless,
            args=["--start-maximized"]
        )
    
    return browser
    rules = load_rules()  # dynamic load each call
    if not rules:
        raise HTTPException(status_code=422, detail="No platform rules found in ./rules/*.yaml")
    return rules

def _background_cookie_generation(session_id: str, platform: str, manual_confirmation: bool = False):
    """Background function to handle cookie generation"""
    try:
        cookie_sessions[session_id]["status"] = "in_progress"
        cookie_sessions[session_id]["message"] = f"Browser opening for {platform} login..."
        
        # Import here to avoid circular imports
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = _connect_or_launch_browser(p, headless=False)
            
            # Get existing context or create new one
            if hasattr(browser, 'contexts') and browser.contexts:
                context = browser.contexts[0]
                page = context.new_page()
            else:
                context = browser.new_context(no_viewport=True)
                page = context.new_page()
            
            try:
                # Generate cookies using the runner's method
                rules = load_rules()
                runner = RulesRunner(
                    rules_by_platform=rules,
                    headless=False,
                    base_video_dir=Path("recordings"),
                    public_dir=PUBLIC_DIR,
                    public_base_url="/files",
                    use_chrome_channel=True,
                    copy_to_desktop=False,
                    generate_cookies=False,  # We'll call the method directly
                )
                
                # Directly call the cookie generation method
                runner._log = lambda msg: print(f"[Cookie Gen] {msg}")
                
                if manual_confirmation:
                    # Manual confirmation mode - just open browser and wait for API call
                    cookie_sessions[session_id]["message"] = f"Browser opened for {platform}. Please login and then call /cookie-save/{session_id} when ready."
                    
                    # Navigate to login page and wait
                    if platform in configs.SOCIAL_MAPS:
                        login_url = configs.SOCIAL_MAPS[platform]['login_url']
                        print(f"[Cookie Gen] Opening {login_url}")
                        page.goto(login_url)
                        page.wait_for_load_state("networkidle")
                        print(f"[Cookie Gen] Browser ready for manual login. Waiting for save command...")
                        
                        # Keep browser open and wait for manual save trigger
                        while cookie_sessions[session_id]["status"] == "in_progress":
                            try:
                                page.wait_for_timeout(1000)  # Check every second
                            except:
                                break
                        
                        # If manual save was triggered, save cookies now
                        if cookie_sessions[session_id]["status"] == "manual_save":
                            print(f"[Cookie Gen] Manual save triggered, saving cookies...")
                            try:
                                # Save cookies manually
                                sessions_dir = Path.cwd() / "sessions"
                                sessions_dir.mkdir(exist_ok=True)
                                filename = configs.SOCIAL_MAPS[platform].get('filename', f'{platform}.json')
                                cookie_file = sessions_dir / filename
                                
                                cookies = page.context.cookies()
                                if not cookies:
                                    raise Exception("No cookies found. Please ensure you are logged in.")
                                
                                with open(cookie_file, 'w', encoding='utf-8') as f:
                                    json.dump(cookies, f, indent=2)
                                
                                print(f"[Cookie Gen] ✅ Manually saved {len(cookies)} cookies to {cookie_file}")
                                cookie_sessions[session_id]["message"] = f"✅ Manually saved {len(cookies)} cookies for {platform}"
                                
                            except Exception as e:
                                print(f"[Cookie Gen] ❌ Manual save failed: {e}")
                                cookie_sessions[session_id]["status"] = "failed"
                                cookie_sessions[session_id]["message"] = f"Manual save failed: {str(e)}"
                                cookie_sessions[session_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
                                return
                    
                else:
                    # Auto-detection mode
                    runner._generate_cookie(page, platform)
                
                cookie_sessions[session_id]["status"] = "completed"
                cookie_sessions[session_id]["message"] = f"Cookies generated successfully for {platform}"
                cookie_sessions[session_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
                
            except Exception as e:
                cookie_sessions[session_id]["status"] = "failed"
                cookie_sessions[session_id]["message"] = f"Cookie generation failed: {str(e)}"
                cookie_sessions[session_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
            finally:
                # Keep browser open a bit longer to ensure cookies are saved
                try:
                    page.wait_for_timeout(2000)  # Wait 2 seconds
                except:
                    pass
                
                # For CDP connections, only close the context, not the browser
                if configs.BROWSER_CONFIG.get('use_cdp_connection', False):
                    try:
                        context.close()
                        print("[Cookie Gen] Context closed (browser remains open)")
                    except:
                        pass
                else:
                    # For direct launches, close the entire browser
                    try:
                        context.close()
                        browser.close()
                        print("[Cookie Gen] Browser closed")
                    except:
                        pass
        
    except Exception as e:
        cookie_sessions[session_id]["status"] = "failed"
        cookie_sessions[session_id]["message"] = f"Cookie generation failed: {str(e)}"
        cookie_sessions[session_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"

# ------------ Routes ------------
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}

@app.get("/platforms", dependencies=[Depends(require_api_key)])
def list_platforms():
    rules = _load_rules_or_422()
    return {"platforms": sorted(rules.keys())}

@app.get("/platforms/{platform}/tasks", dependencies=[Depends(require_api_key)])
def list_tasks(platform: str):
    rules = _load_rules_or_422()
    p = rules.get(platform)
    if not p:
        raise HTTPException(status_code=404, detail=f"Unknown platform '{platform}'")
    tasks = sorted((p.get("tasks") or {}).keys())
    return {"platform": platform, "tasks": tasks, "raw": p.get("tasks")}

@app.post("/run", response_model=RunResponse, dependencies=[Depends(require_api_key)])
def run_tasks(req: RunRequest):
    rules = _load_rules_or_422()

    # Validate platform/task existence before running
    invalid = []
    for item in req.plan:
        pdef = rules.get(item.platform, {})
        if item.task not in (pdef.get("tasks") or {}):
            invalid.append({"platform": item.platform, "task": item.task, "known_tasks": sorted((pdef.get("tasks") or {}).keys())})
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_tasks": invalid})

    runner = RulesRunner(
        rules_by_platform=rules,
        headless=req.headless,
        base_video_dir=Path(req.recordings_dir),
        public_dir=PUBLIC_DIR,
        public_base_url="/files",
        use_chrome_channel=True,
        copy_to_desktop=False,  # API mode: keep videos under /files
        generate_cookies=req.generate_cookies,
    )

    started = datetime.utcnow()
    # Transform request models into the simple dicts the runner expects
    plan_dicts = [
        {
            "platform": i.platform,
            "task": i.task,
            "target": {"name": i.target.name, "username": i.target.username},
            "content": i.content,
        }
        for i in req.plan
    ]

    try:
        details = runner.run_plan(plan_dicts)  # returns statuses, steps, logs, video paths/urls
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Runner error: {e}")

    finished = datetime.utcnow()
    return RunResponse(
        started_at=started.isoformat() + "Z",
        finished_at=finished.isoformat() + "Z",
        tasks=len(details),
        details=details,
    )

@app.post("/generate-cookies", response_model=CookieGenerationResponse, dependencies=[Depends(require_api_key)])
def generate_cookies(req: CookieGenerationRequest):
    """Start cookie generation process in background"""
    rules = _load_rules_or_422()
    
    if req.platform not in rules:
        raise HTTPException(status_code=404, detail=f"Unknown platform '{req.platform}'")
    
    session_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat() + "Z"
    
    # Initialize session tracking
    cookie_sessions[session_id] = {
        "platform": req.platform,
        "status": "started",
        "message": "Cookie generation started. Browser will open for manual login.",
        "started_at": started_at,
        "completed_at": None
    }
    
    # Start background thread
    thread = threading.Thread(
        target=_background_cookie_generation,
        args=(session_id, req.platform, req.manual_confirmation),
        daemon=True
    )
    thread.start()
    
    message = "Cookie generation started. Browser will open for manual login."
    if req.manual_confirmation:
        message += " Call /cookie-save/{session_id} after logging in to save cookies."
    else:
        message += " Login will be detected automatically."
    
    return CookieGenerationResponse(
        session_id=session_id,
        platform=req.platform,
        status="started",
        message=message,
        started_at=started_at
    )

@app.post("/cookie-save/{session_id}", dependencies=[Depends(require_api_key)])
def save_cookies_manually(session_id: str):
    """Manually trigger cookie saving for a session"""
    if session_id not in cookie_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = cookie_sessions[session_id]
    if session["status"] != "in_progress":
        raise HTTPException(status_code=400, detail=f"Session is not in progress. Current status: {session['status']}")
    
    # Trigger the save by changing status
    cookie_sessions[session_id]["status"] = "manual_save"
    
    return {"message": "Cookie save triggered. Check status for completion."}

@app.get("/cookie-status/{session_id}", response_model=CookieStatusResponse, dependencies=[Depends(require_api_key)])
def get_cookie_status(session_id: str):
    """Check the status of a cookie generation session"""
    if session_id not in cookie_sessions:
        return CookieStatusResponse(
            session_id=session_id,
            platform="unknown",
            status="not_found",
            message="Session not found"
        )
    
    session = cookie_sessions[session_id]
    return CookieStatusResponse(
        session_id=session_id,
        platform=session["platform"],
        status=session["status"],
        message=session["message"],
        started_at=session["started_at"],
        completed_at=session.get("completed_at")
    )

# ------------ Server Startup ------------
if __name__ == "__main__":
    import uvicorn
    
    # Default configuration
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"🚀 Starting Multi Poster API server...")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🌐 URL: http://{host}:{port}")
    print(f"📚 Docs: http://{host}:{port}/docs")
    print(f"🔧 Health: http://{host}:{port}/health")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes
        access_log=True
    )
