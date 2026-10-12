import urllib.parse, webbrowser

TOOL = {
    "name": "browser_control",
    "description": "Open a URL, or search Google / YouTube in the default browser.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["open_url", "google", "youtube"]},
        "target": {"type": "string", "description": "URL or search terms"}},
        "required": ["action", "target"]},
}


def handler(params, ctx):
    a, t = params["action"], params["target"].strip()
    if a == "open_url":
        url = t if "://" in t else "https://" + t
    elif a == "youtube":
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(t)
    else:
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(t)
    webbrowser.open(url)
    return f"Opened {url}"
