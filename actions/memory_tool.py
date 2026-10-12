from core import memory

TOOL = {
    "name": "memory",
    "description": ("Long-term memory about the user. remember: save a lasting fact (key like 'sister_name', category "
                    "'identity' for name/city/etc). recall: search saved facts. forget: delete a fact by key."),
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["remember", "recall", "forget"]},
        "key": {"type": "string"}, "value": {"type": "string"},
        "category": {"type": "string", "description": "identity, preference, person, project, general"},
        "query": {"type": "string"}}, "required": ["action"]},
}


def handler(params, ctx):
    a = params["action"]
    if a == "remember":
        if not params.get("key") or not params.get("value"): return "Need a key and a value."
        k = memory.remember(params["key"], params["value"], params.get("category", "general"))
        return f"Saved as '{k}'."
    if a == "recall":
        hits = memory.search(params.get("query") or params.get("key") or "")
        return "\n".join(f"{k}: {v['value']} ({v['updated']})" for k, v in hits) or "Nothing found."
    if a == "forget":
        return "Forgotten." if memory.forget(params.get("key", "")) else "No such key."
    return "Unknown action."
