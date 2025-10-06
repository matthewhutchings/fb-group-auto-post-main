# engine/actions.py
from playwright.sync_api import Page


class AbortTask(Exception):
    """Raised to stop the current task gracefully (not an error)."""
    pass

def do_goto(page: Page, url: str, **kwargs):
    page.goto(url, timeout=kwargs.get("timeout", 30000))

def do_wait_selector(page: Page, selector: str, **kwargs):
    page.wait_for_selector(selector, timeout=kwargs.get("timeout", 10000))

def do_click(page: Page, selector: str, **kwargs):
    page.wait_for_selector(selector, timeout=kwargs.get("timeout", 10000)).click()

def do_fill(page: Page, selector: str, value: str, **kwargs):
    el = page.wait_for_selector(selector, timeout=kwargs.get("timeout", 10000))
    el.fill(value)

def do_sleep(page: Page, seconds: float, **kwargs):
    page.wait_for_timeout(int(seconds * 1000))

def do_type(page: Page, selector: str, text: str, **kwargs):
    el = page.wait_for_selector(selector, timeout=kwargs.get("timeout", 10000))
    el.type(text, delay=kwargs.get("delay", 20))

def do_eval(page: Page, script: str, **kwargs):
    page.evaluate(script)

# ---- New optional / conditional helpers ----

def do_wait_selector_optional(page: Page, selector: str, **kwargs):
    """Wait for selector if it appears, but don't fail if it doesn't."""
    timeout = kwargs.get("timeout", 3000)
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except Exception:
        pass

def do_click_if_present(page: Page, selector: str, **kwargs):
    """Click element if it exists; otherwise no-op."""
    el = page.query_selector(selector)
    if el:
        el.click()

def do_abort_if_present(page: Page, selector: str, **kwargs):
    """
    If selector exists, abort the task gracefully (used for 'already joined' etc.).
    """
    if page.query_selector(selector):
        raise AbortTask(f"Condition present: {selector!r}")

ACTION_MAP = {
    "goto": do_goto,
    "wait_selector": do_wait_selector,
    "click": do_click,
    "fill": do_fill,
    "type": do_type,
    "sleep": do_sleep,
    "eval": do_eval,
    # new:
    "wait_selector_optional": do_wait_selector_optional,
    "click_if_present": do_click_if_present,
    "abort_if_present": do_abort_if_present,
}
