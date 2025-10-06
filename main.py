from datetime import datetime
from pathlib import Path

from engine.runner import RulesRunner
from platforms.loader import load_rules


def get_sources_list(platform: str):
    # replace with your config or DB
    if platform == "facebook":
        return [{"name":"Test FB Group","username":"your.fb.group.username"}]
    if platform == "reddit":
        return [{"name":"testsub","username":"testsubreddit"}]
    if platform == "instagram":
        return [{"name":"testinsta","username":"testinstausername"}]
    return []

if __name__ == "__main__":
    rules_by_platform = load_rules()
    runner = RulesRunner(rules_by_platform, headless=False, base_video_dir=Path("recordings"))

    now = datetime.now()
    POST_CONTENT = f"""
Сайн байцгаана уу...
Automated post: {now.strftime('%H:%M:%S')}
https://youtu.be/BdjZFPTONYc
"""

    plan = []
    for g in get_sources_list("facebook"):
        plan.append({"platform":"facebook","task":"post_group","target":g,"content":POST_CONTENT})
    for r in get_sources_list("reddit"):
        plan.append({"platform":"reddit","task":"post_subreddit","target":r,"content":POST_CONTENT})
    for ig in get_sources_list("instagram"):
        plan.append({"platform":"instagram","task":"post_profile","target":ig,"content":POST_CONTENT})

    runner.run_plan(plan)
