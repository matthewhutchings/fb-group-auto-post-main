# engine/runner.py
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .actions import ACTION_MAP, AbortTask  # ensure AbortTask exists
import configs


def nowstamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def get_cdp_ws_url(port: int = 9222) -> str:
    """Get Chrome DevTools Protocol WebSocket URL"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=3)
        response.raise_for_status()
        info = response.json()
        return info["webSocketDebuggerUrl"]
    except Exception as e:
        raise Exception(f"Failed to get CDP WebSocket URL: {e}")


def is_chrome_running_with_debug(port: int = 9222) -> bool:
    """Check if Chrome is running with remote debugging enabled"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
        return response.status_code == 200
    except:
        return False


def start_chrome_with_debug(chrome_path: str, port: int = 9222, args: List[str] = None) -> subprocess.Popen:
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


class RulesRunner:
    """
    Executes platform rules (YAML parsed to dict).
    - Cookie load
    - Per-task context with video recording
    - Publishes video to a public dir for API to link
    - Returns per-task: status, message, steps, logs, video paths/URLs
    """

    def __init__(
        self,
        rules_by_platform: Dict,
        headless: bool = False,
        base_video_dir: Optional[Path] = None,
        public_dir: Optional[Path] = None,
        public_base_url: str = "/files",   # where StaticFiles is mounted
        use_chrome_channel: bool = True,
        copy_to_desktop: bool = False,     # API mode usually doesn't move to Desktop
        generate_cookies: bool = False,    # whether to generate new cookies
    ):
        self.rules_by_platform = rules_by_platform
        self.headless = headless
        self.base_video_dir = base_video_dir or Path("recordings")
        self.base_video_dir.mkdir(parents=True, exist_ok=True)

        self.public_dir = public_dir or Path("recordings_public")

        self.public_dir.mkdir(parents=True, exist_ok=True)

        self.public_base_url = public_base_url.rstrip("/")
        self.use_chrome_channel = use_chrome_channel
        self.copy_to_desktop = copy_to_desktop
        self.generate_cookies = generate_cookies
        self.desktop = Path.home() / "Desktop"

    def _connect_or_launch_browser(self, p) -> Browser:
        """Connect to existing Chrome via CDP or launch new browser"""
        
        if configs.BROWSER_CONFIG.get('use_cdp_connection', False):
            # Try to connect to existing Chrome with remote debugging
            cdp_port = configs.BROWSER_CONFIG.get('cdp_port', 9222)
            
            if is_chrome_running_with_debug(cdp_port):
                try:
                    self._log(f"[browser] Connecting to existing Chrome on port {cdp_port}")
                    ws_url = get_cdp_ws_url(cdp_port)
                    browser = p.chromium.connect_over_cdp(ws_url)
                    self._log(f"[browser] ✅ Connected to existing Chrome via CDP")
                    return browser
                except Exception as e:
                    self._log(f"[browser] ⚠️ Failed to connect to existing Chrome: {e}")
            else:
                self._log(f"[browser] No Chrome found with remote debugging on port {cdp_port}")
                
                # Try to start Chrome with remote debugging
                if configs.BROWSER_CONFIG.get('use_local_chrome', False):
                    try:
                        self._log(f"[browser] Starting Chrome with remote debugging on port {cdp_port}")
                        chrome_path = configs.BROWSER_CONFIG['chrome_path']
                        chrome_args = configs.BROWSER_CONFIG.get('chrome_args', [])
                        
                        # Filter out conflicting args and add our required ones
                        filtered_args = [arg for arg in chrome_args 
                                       if not arg.startswith('--remote-debugging')]
                        
                        start_chrome_with_debug(chrome_path, cdp_port, filtered_args)
                        
                        # Wait for Chrome to start
                        for i in range(10):  # Wait up to 10 seconds
                            time.sleep(1)
                            if is_chrome_running_with_debug(cdp_port):
                                self._log(f"[browser] Chrome started successfully")
                                break
                        else:
                            raise Exception("Chrome failed to start with remote debugging")
                        
                        # Connect to the newly started Chrome
                        ws_url = get_cdp_ws_url(cdp_port)
                        browser = p.chromium.connect_over_cdp(ws_url)
                        self._log(f"[browser] ✅ Connected to newly started Chrome via CDP")
                        return browser
                        
                    except Exception as e:
                        self._log(f"[browser] ⚠️ Failed to start Chrome with remote debugging: {e}")
        
        # Fallback to launching browser directly
        return self._launch_browser_directly(p)
    
    def _launch_browser_directly(self, p) -> Browser:
        """Launch browser directly (original method)"""
        try:
            if self.use_chrome_channel and configs.BROWSER_CONFIG.get('use_local_chrome', False):
                self._log(f"[browser] Launching Chrome directly")
                browser = p.chromium.launch(
                    headless=self.headless, 
                    channel="chrome",
                    executable_path=configs.BROWSER_CONFIG['chrome_path'],
                    args=configs.BROWSER_CONFIG['chrome_args']
                )
            elif self.use_chrome_channel:
                # Try Chrome channel without explicit path
                browser = p.chromium.launch(
                    headless=self.headless, 
                    channel="chrome",
                    args=["--start-maximized"]
                )
            else:
                raise Exception("Chrome channel disabled")
        except Exception as e:
            self._log(f"[browser] ⚠️ Failed to launch Chrome: {e}")
            self._log("[browser] Falling back to Chromium...")
            browser = p.chromium.launch(headless=self.headless, args=["--start-maximized"])
        
        return browser

    def _task_dir(self, platform: str, task: str) -> Path:
        d = self.base_video_dir / f"{platform}_{task}_{nowstamp()}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _new_context(self, browser: Browser, platform: str, task: str) -> BrowserContext:
        task_dir = self._task_dir(platform, task)
        
        # For CDP connections, try to use existing context or create new one
        if configs.BROWSER_CONFIG.get('use_cdp_connection', False):
            # If browser has existing contexts, create a new page in the first context
            if hasattr(browser, 'contexts') and browser.contexts:
                return browser.contexts[0]
        
        # Create new context with video recording
        return browser.new_context(
            no_viewport=True,
            record_video_dir=str(task_dir),
            record_video_size={"width": 1280, "height": 720},
        )

    def _load_cookies_if_any(self, context: BrowserContext, platform: str):
        cookie_file = Path.cwd() / "sessions" / f"{platform}.json"
        if cookie_file.exists():
            try:
                cookies = json.loads(cookie_file.read_text())
                context.add_cookies(cookies)
            except Exception as e:
                self._log(f"[cookies] Failed to add {platform} cookies: {e}")

    def _generate_cookie(self, page: Page, platform: str):
        """Generate and save cookies for a platform after manual login"""
        if platform not in configs.SOCIAL_MAPS:
            self._log(f"[cookies] No login URL configured for platform '{platform}'")
            return
        
        login_url = configs.SOCIAL_MAPS[platform]['login_url']
        filename = configs.SOCIAL_MAPS[platform].get('filename', f'{platform}.json')
        
        self._log(f"[cookies] Opening {platform} login page...")
        self._log(f"[cookies] URL: {login_url}")
        page.goto(login_url)
        
        # Wait for page to fully load
        page.wait_for_load_state("networkidle")
        
        self._log(f"[cookies] ✅ Browser opened for {platform} login")
        self._log(f"[cookies] Please log in manually in the browser window...")
        self._log(f"[cookies] Waiting for login completion (up to 10 minutes)...")
        
        # Wait for navigation away from login page or presence of logged-in indicators
        try:
            # More strict login detection - wait for actual login, not just page load
            page.wait_for_function(
                """() => {
                    // Only return true if we have clear evidence of being logged in
                    
                    // First check: Are we still on the login page?
                    const isOnLoginPage = window.location.href.includes('/login') || 
                                         window.location.href.includes('/signin');
                    
                    if (isOnLoginPage) {
                        // If still on login page, check if login form is gone AND we have logged-in elements
                        const loginForm = document.querySelector('[data-testid="royal_login_form"]') ||
                                        document.querySelector('form[action*="login"]') ||
                                        document.querySelector('#loginform');
                        
                        // Only proceed if login form is completely gone
                        if (loginForm) {
                            console.log('Still on login page with form visible');
                            return false;
                        }
                    }
                    
                    // Check for definitive logged-in indicators
                    const loggedInElements = [
                        '[aria-label="Account"]',
                        '[data-testid="blue_bar"]',
                        '[data-testid="fb-nav-bar"]',
                        '[data-testid="nav-bar-user-menu"]',
                        '[role="banner"] [role="navigation"]',
                        '[data-testid="left_nav_menu_list"]',
                        'div[data-pagelet="LeftRail"]'
                    ];
                    
                    let foundLoggedInElement = false;
                    for (const selector of loggedInElements) {
                        if (document.querySelector(selector)) {
                            console.log('Found logged-in element:', selector);
                            foundLoggedInElement = true;
                            break;
                        }
                    }
                    
                    // Check if we're on a logged-in page (home, feed, profile)
                    const loggedInUrls = ['/feed', '/home', '/?', '/profile'];
                    const isOnLoggedInPage = loggedInUrls.some(url => 
                        window.location.href.includes(url) || 
                        window.location.pathname === '/'
                    );
                    
                    // Only return true if we have BOTH a logged-in element AND are not on login page
                    if (foundLoggedInElement && !isOnLoginPage) {
                        console.log('✅ Successfully logged in - found UI elements and not on login page');
                        return true;
                    }
                    
                    // Alternative: if we're clearly on a logged-in page with content
                    if (isOnLoggedInPage && foundLoggedInElement) {
                        console.log('✅ Successfully logged in - on logged-in page with UI elements');
                        return true;
                    }
                    
                    console.log('Still waiting for login completion...');
                    return false;
                }""",
                timeout=600000  # 10 minutes timeout
            )
            self._log(f"[cookies] ✅ Login detected for {platform}")
            
            # Wait a bit more to ensure all cookies are set
            page.wait_for_timeout(3000)  # 3 seconds
            
        except Exception as e:
            self._log(f"[cookies] ❌ Login timeout or error: {e}")
            raise Exception(f"Login timeout for {platform}. Please try again.")
        
        # Save cookies
        sessions_dir = Path.cwd() / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        cookie_file = sessions_dir / filename
        
        try:
            cookies = page.context.cookies()
            if not cookies:
                self._log(f"[cookies] ⚠️  No cookies found. Login may not have completed properly.")
                raise Exception("No cookies found after login")
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            self._log(f"[cookies] ✅ Saved {len(cookies)} cookies to {cookie_file}")
            self._log(f"[cookies] Cookie generation completed successfully!")
            
        except Exception as e:
            self._log(f"[cookies] ❌ Failed to save cookies: {e}")
            raise

    def _publish_videos(self, platform: str, task: str, target_name: str) -> Dict[str, Any]:
        """
        Copy first .webm from task dir to public_dir and (optionally) Desktop.
        Return {'video_local': str|None, 'video_url': str|None}
        """
        result = {"video_local": None, "video_url": None}
        # find most recent task dir matching pattern
        candidates = sorted(self.base_video_dir.glob(f"{platform}_{task}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return result
        for subdir in candidates:
            videos = sorted(subdir.glob("*.webm"))
            if not videos:
                continue
            video = videos[0]
            # Publish to public dir
            public_name = f"{platform}_{task}_{target_name}_{nowstamp()}.webm"
            public_path = self.public_dir / public_name
            try:
                shutil.copy2(str(video), str(public_path))
                result["video_local"] = str(public_path)
                result["video_url"] = f"{self.public_base_url}/{public_name}"
            except Exception as e:
                self._log(f"[video] Failed to copy to public dir: {e}")

            # Optionally copy to Desktop
            if self.copy_to_desktop:
                try:
                    desktop_path = self.desktop / public_name
                    shutil.copy2(str(video), str(desktop_path))
                except Exception as e:
                    self._log(f"[video] Failed to copy to Desktop: {e}")
            break
        return result

    def _log(self, msg: str):
        # gets replaced per-task with a closure that appends to that task's logs
        print(msg)

    # ----------------- public API -----------------

    def run_plan(self, plan: List[Dict]) -> List[Dict[str, Any]]:
        """
        Execute tasks; return per-task details:
        {
          platform, task, target,
          status: "completed"|"aborted"|"error",
          message: str,
          steps: [ {index, type, params} ],
          logs: [str],
          video_local: str|None,
          video_url: str|None
        }
        """
        results: List[Dict[str, Any]] = []

        with sync_playwright() as p:
            browser = self._connect_or_launch_browser(p)

            for item in plan:
                platform = item["platform"]
                task = item["task"]
                target = item.get("target", {}) or {}
                content = item.get("content", "")

                target_name = target.get("name", "target")
                task_logs: List[str] = []
                steps_executed: List[Dict[str, Any]] = []

                # per-task logger that also prints
                def tlog(msg: str):
                    task_logs.append(msg)
                    print(msg)

                # swap logger for this task
                self._log = tlog

                tlog(f"[runner] {platform}.{task} -> {target_name}")

                rules = self.rules_by_platform.get(platform, {})
                task_def = (rules.get("tasks") or {}).get(task)
                if not task_def:
                    msg = f"No task '{task}' for platform '{platform}'"
                    tlog(f"[runner] {msg}")
                    results.append({
                        "platform": platform,
                        "task": task,
                        "target": target,
                        "status": "error",
                        "message": msg,
                        "steps": steps_executed,
                        "logs": task_logs,
                        "video_local": None,
                        "video_url": None,
                    })
                    continue

                context = self._new_context(browser, platform, task)
                page = context.new_page()

                status = "completed"
                message = "ok"

                try:
                    # If generate_cookies is True, generate cookies instead of loading them
                    if self.generate_cookies:
                        self._generate_cookie(page, platform)
                        # After generating cookies, we can optionally proceed with the task
                        # or just return after cookie generation
                        tlog(f"[runner] Cookie generation completed for {platform}")
                    else:
                        self._load_cookies_if_any(context, platform)
                        self._execute_steps(
                            page,
                            task_def["steps"],
                            steps_executed=steps_executed,
                            log=tlog,
                            target=target,
                            content=content,
                            platform=platform,
                        )
                except AbortTask as e:
                    status = "aborted"
                    message = str(e) or "aborted by condition"
                    tlog(f"[runner] Aborted task: {message}")
                except Exception as e:
                    status = "error"
                    message = f"{type(e).__name__}: {e}"
                    tlog(f"[runner] Task error: {message}")
                finally:
                    # close to flush video; then publish
                    if configs.BROWSER_CONFIG.get('use_cdp_connection', False):
                        # For CDP connections, only close the context, not the browser
                        try:
                            if context != browser.contexts[0]:  # Only close if it's not the main context
                                context.close()
                        except:
                            pass
                    else:
                        # For direct launches, close the context normally
                        context.close()
                    
                    vid = self._publish_videos(platform, task, target_name)

                    results.append({
                        "platform": platform,
                        "task": task,
                        "target": target,
                        "status": status,
                        "message": message,
                        "steps": steps_executed,
                        "logs": task_logs,
                        "video_local": vid.get("video_local"),
                        "video_url": vid.get("video_url"),
                    })

            # Only close browser if not using CDP connection
            if not configs.BROWSER_CONFIG.get('use_cdp_connection', False):
                browser.close()

        return results

    # ----------------- internals -----------------

    def _render_template(self, s: str, target: Dict, content: str, platform: str) -> str:
        return (
            (s or "")
            .replace("{{target.username}}", target.get("username", ""))
            .replace("{{target.name}}", target.get("name", ""))
            .replace("{{content}}", content)
            .replace("{{platform}}", platform)
        )

    def _execute_steps(
        self,
        page: Page,
        steps: List[Dict],
        *,
        steps_executed: List[Dict[str, Any]],
        log,
        **ctx,
    ):
        for i, step in enumerate(steps, 1):
            stype = step["type"]
            fn = ACTION_MAP.get(stype)
            if not fn:
                log(f"[runner] Unknown step type '{stype}', skipping.")
                continue

            # Render templated params
            params = {
                k: self._render_template(v, **ctx) if isinstance(v, str) else v
                for k, v in step.items()
                if k != "type"
            }

            steps_executed.append({"index": i, "type": stype, "params": params})
            log(f"[runner] step {i}: {stype} {params}")
            fn(page, **params)
