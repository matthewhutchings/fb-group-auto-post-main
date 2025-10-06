from pathlib import Path
from typing import Any, Dict

import yaml


def _deep_merge_tasks(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Merge src into dst for {platform: {tasks: {...}}}"""
    if not dst:
        return src
    # merge tasks
    dst_tasks = (dst.get("tasks") or {})
    src_tasks = (src.get("tasks") or {})
    # override on conflict; you can add warnings/logging if you like
    dst_tasks.update(src_tasks)
    dst["tasks"] = dst_tasks
    # carry over other top-level keys if needed (e.g., defaults)
    for k, v in src.items():
        if k == "tasks":
            continue
        dst.setdefault(k, v)
    return dst

def load_rules() -> Dict[str, Dict]:
    """
    Load all YAML files from rules/, merging tasks per platform.
    Supports multiple YAML documents per file (via '---').
    """
    # resolve rules/ relative to project root (platforms/..)
    base = Path(__file__).resolve().parent.parent
    rules_dir = base / "rules"

    out: Dict[str, Dict] = {}
    for path in sorted(rules_dir.glob("*.y*ml")):
        with path.open("r", encoding="utf-8") as f:
            # support multi-doc YAML
            docs = list(yaml.safe_load_all(f)) or []
            for doc in docs:
                if not isinstance(doc, dict):
                    continue
                platform_name = doc.get("platform")
                if not platform_name:
                    continue
                current = out.get(platform_name, {"platform": platform_name, "tasks": {}})
                out[platform_name] = _deep_merge_tasks(current, doc)
    return out
