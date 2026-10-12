import datetime, threading

TOOL = {
    "name": "reminder",
    "description": "Set a spoken reminder in N minutes or at a clock time (HH:MM, 24h). Reminders live while the app is running.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["set", "list", "cancel_all"]},
        "text": {"type": "string", "description": "What to remind about"},
        "minutes": {"type": "number"},
        "at": {"type": "string", "description": "HH:MM, 24-hour"}}},
}
_active = []


def handler(params, ctx):
    a = params.get("action", "set")
    if a == "list":
        return "\n".join(f"{t['due']:%H:%M}  {t['text']}" for t in _active) or "No reminders."
    if a == "cancel_all":
        for t in _active: t["timer"].cancel()
        _active.clear(); return "All reminders cancelled."
    text = params.get("text") or "your reminder"
    now = datetime.datetime.now()
    if params.get("minutes") is not None:
        due = now + datetime.timedelta(minutes=float(params["minutes"]))
    elif params.get("at"):
        h, m = [int(x) for x in params["at"].split(":")[:2]]
        due = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if due <= now: due += datetime.timedelta(days=1)
    else:
        return "Tell me when: minutes or a clock time."
    entry = {"text": text, "due": due}

    def fire():
        _active.remove(entry)
        ctx.log(f"Reminder: {text}")
        ctx.say(f"Reminder due now: {text}")
    entry["timer"] = threading.Timer((due - now).total_seconds(), fire)
    entry["timer"].daemon = True
    entry["timer"].start()
    _active.append(entry)
    return f"Reminder set for {due:%H:%M}: {text}"
