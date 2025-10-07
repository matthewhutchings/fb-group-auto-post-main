# server.py
import os
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

PUBLIC_DIR = Path("/workspace/recordings_public")               # where videos are exposed
PUBLIC_DIR.mkdir(exist_ok=True)

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

# ------------ Utilities ------------
def _load_rules_or_422():
    rules = load_rules()  # dynamic load each call
    if not rules:
        raise HTTPException(status_code=422, detail="No platform rules found in ./rules/*.yaml")
    return rules

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
