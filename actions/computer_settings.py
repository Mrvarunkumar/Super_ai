import difflib, re, subprocess
from core import undo
from core.config import OS

ACTIONS = ["set_volume", "volume_up", "volume_down", "mute", "unmute", "set_brightness"]
TOOL = {
    "name": "computer_settings",
    "description": "Change system settings: volume (set/up/down/mute/unmute) and screen brightness.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ACTIONS},
        "value": {"type": "number", "description": "0-100 for set_*, or step size for volume_up/down (default 10)"}},
        "required": ["action"]},
}


def _run(*cmd):
    return subprocess.check_output(cmd, text=True)


def _get_volume():
    if OS == "Darwin":
        return int(_run("osascript", "-e", "output volume of (get volume settings)").strip())
    if OS == "Linux":
        return int(re.search(r"(\d+)%", _run("pactl", "get-sink-volume", "@DEFAULT_SINK@")).group(1))
    return None  # Windows: no dependency-free way to read it


def _set_volume(n):
    n = max(0, min(100, int(n)))
    if OS == "Darwin":
        _run("osascript", "-e", f"set volume output volume {n}")
    elif OS == "Linux":
        _run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{n}%")
    else:
        import pyautogui
        pyautogui.PAUSE = 0
        for _ in range(50): pyautogui.press("volumedown")
        for _ in range(n // 2): pyautogui.press("volumeup")


def _volume_to(n):
    before = _get_volume()
    _set_volume(n)
    if before is not None:  # only register undo if we know the real previous value
        undo.register(f"volume back to {before}", lambda: _set_volume(before))
    return f"Volume set to {int(n)}."


def _mute(on):
    if OS == "Darwin": _run("osascript", "-e", f"set volume output muted {'true' if on else 'false'}")
    elif OS == "Linux": _run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if on else "0")
    else:
        import pyautogui; pyautogui.press("volumemute")   # toggle on Windows
    return "Muted." if on else "Unmuted."


def _brightness(n):
    try:
        import screen_brightness_control as sbc
    except ImportError:
        return "Brightness needs: pip install screen-brightness-control (not supported on macOS)."
    before = sbc.get_brightness()[0]
    sbc.set_brightness(int(n))
    undo.register(f"brightness back to {before}", lambda: sbc.set_brightness(before))
    return f"Brightness set to {int(n)}."


def handler(params, ctx):
    a = (params.get("action") or "").strip().lower().replace(" ", "_")
    if a not in ACTIONS:   # spelling tolerance, done locally
        m = difflib.get_close_matches(a, ACTIONS, n=1, cutoff=0.6)
        if not m:
            return f"Unknown action '{a}'. Valid: {', '.join(ACTIONS)}"
        a = m[0]
    v = params.get("value")
    try:
        if a == "set_volume": return _volume_to(v if v is not None else 50)
        if a in ("volume_up", "volume_down"):
            step = int(v or 10) * (1 if a == "volume_up" else -1)
            cur = _get_volume()
            if cur is not None: return _volume_to(cur + step)
            import pyautogui; pyautogui.PAUSE = 0
            for _ in range(abs(step) // 2): pyautogui.press("volumeup" if step > 0 else "volumedown")
            return "Volume adjusted."
        if a == "mute": return _mute(True)
        if a == "unmute": return _mute(False)
        if a == "set_brightness": return _brightness(v if v is not None else 50)
    except Exception as e:
        return f"Failed: {e}"
