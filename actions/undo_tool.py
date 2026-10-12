from core import undo

TOOL = {
    "name": "undo",
    "description": "Reverse the assistant's last file or settings change. Call when the user says undo / take that back.",
    "parameters": {"type": "object", "properties": {}},
}


def handler(params, ctx):
    return undo.undo()
