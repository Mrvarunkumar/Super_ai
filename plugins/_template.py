"""Copy this file (remove the leading underscore) to add a skill. Restart the app and it is auto-discovered.
Files starting with '_' are ignored."""

TOOL = {
    "name": "my_skill",
    "description": "One clear sentence telling the model WHEN to use this.",
    "parameters": {"type": "object", "properties": {
        "thing": {"type": "string", "description": "What it needs"}}, "required": ["thing"]},
}


def handler(params, ctx):
    # ctx.log(msg) -> activity log, ctx.say(text) -> assistant speaks, ctx.confirm(label, fn) -> UI confirm button
    return f"You asked for {params['thing']}."
