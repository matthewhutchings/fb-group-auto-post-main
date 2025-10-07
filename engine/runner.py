# engine/runner.py
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .actions import ACTION_MAP, AbortTask  # ensure AbortTask exists
import configs


def nowstamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


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
        self.base_video_dir = Path("/workspace/recordings")
        self.base_video_dir.mkdir(parents=True, exist_ok=True)

        self.public_dir = Path("/workspace/recordings_public")

        self.public_dir.mkdir(parents=True, exist_ok=True)

        self.public_base_url = public_base_url.rstrip("/")
        self.use_chrome_channel = use_chrome_channel
        self.copy_to_desktop = copy_to_desktop
        self.generate_cookies = generate_cookies
        self.desktop = Path.home() / "Desktop"

    # ----------------- helpers -----------------

    def _task_dir(self, platform: str, task: str) -> Path:
        d = self.base_video_dir / f"{platform}_{task}_{nowstamp()}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _new_context(self, browser: Browser, platform: str, task: str) -> BrowserContext:
        task_dir = self._task_dir(platform, task)
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
        
        self._log(f"[cookies] Navigating to {login_url} for {platform} login")
        page.goto(login_url)
        
        self._log(f"[cookies] Browser opened for {platform} login. Waiting for user to complete login...")
        
        # Wait for navigation away from login page or presence of logged-in indicators
        try:
            # Wait for navigation away from login page or specific success indicators
            page.wait_for_function(
                """() => {
                    // Check if we're no longer on login page
                    if (!window.location.href.includes('/login')) {
                        return true;
                    }
                    // Check for Facebook-specific logged-in indicators
                    if (document.querySelector('[data-testid="royal_login_form"]') === null) {
                        return true;
                    }
                    // Check for presence of user menu or other logged-in elements
                    if (document.querySelector('[aria-label="Account"]') || 
                        document.querySelector('[data-testid="blue_bar"]') ||
                        document.querySelector('[role="navigation"]')) {
                        return true;
                    }
                    return false;
                }""",
                timeout=600000  # 10 minutes timeout
            )
            self._log(f"[cookies] Login detected for {platform}")
        except Exception as e:
            self._log(f"[cookies] Login timeout or error: {e}")
            raise
        
        # Save cookies
        sessions_dir = Path.cwd() / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        cookie_file = sessions_dir / filename
        
        try:
            cookies = page.context.cookies()
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            self._log(f"[cookies] Saved {len(cookies)} cookies to {cookie_file}")
        except Exception as e:
            self._log(f"[cookies] Failed to save cookies: {e}")
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
            # Chrome channel helps reduce detection; fall back to Chromium
            try:
                if self.use_chrome_channel:
                    browser = p.chromium.launch(headless=self.headless, channel="chrome", args=["--start-maximized"])
                else:
                    raise Exception("Chrome channel disabled")
            except Exception:
                browser = p.chromium.launch(headless=self.headless, args=["--start-maximized"])

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
