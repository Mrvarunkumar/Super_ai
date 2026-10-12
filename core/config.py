"""Settings in one JSON file. GEMINI_API_KEY env var overrides the stored key."""
import json, os, platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "settings.json"
OS = platform.system()  # "Windows" | "Darwin" | "Linux"

DEFAULTS = {
    "api_key": "",
    "assistant_name": "Jarvis",
    "user_name": "",
    "voice": "Puck",
    # Live models are tried in order when one is missing/over quota.
    "live_models": ["gemini-3.1-flash-live-preview",
                    "gemini-2.5-flash-native-audio-preview-12-2025"],
    # One-shot (text) models for web search etc. Ladder with cooldowns.
    "text_models": ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"],
    "half_duplex": True,      # mute mic while the assistant talks (use False with headphones)
    "push_to_talk": False,    # hold Ctrl+Space to talk
    "input_device": "",       # substring of device name, "" = system default
    "output_device": "",
    "accent": "#00d4ff",
}
_cache = None


def load():
    global _cache
    if _cache is None:
        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text("utf-8"))
            except Exception:
                data = {}
        _cache = {**DEFAULTS, **data}
    return _cache


def save():
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(load(), indent=2), "utf-8")


def get(key):
    return load()[key]


def put(key, value):
    load()[key] = value
    save()


def api_key():
    return os.environ.get("GEMINI_API_KEY") or load()["api_key"]
