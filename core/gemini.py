"""All one-shot Gemini calls go through here: model ladder, timeout, cooldowns."""
import time
from . import config

_cool = {}  # model -> time when it may be tried again


def _cooldown(err):
    s = str(err)
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        return 300          # quota refills
    if any(k in s for k in ("503", "504", "UNAVAILABLE", "DEADLINE")):
        return 1800         # outages outlast a retry
    if "404" in s or "NOT_FOUND" in s or "403" in s:
        return 21600        # this key doesn't have it
    return 60


def generate(prompt, search=False, timeout=15, system=None):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=config.api_key(),
                          http_options=types.HttpOptions(timeout=int(timeout * 1000)))
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        tools=[types.Tool(google_search=types.GoogleSearch())] if search else None)
    last = None
    for model in config.get("text_models"):
        if _cool.get(model, 0) > time.time():
            continue
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            if r.text:
                return r.text.strip()
        except Exception as e:
            last = e
            _cool[model] = time.time() + _cooldown(e)
    raise RuntimeError(f"All models failed. Last error: {last}")
