import subprocess
from core.config import OS

TOOL = {
    "name": "power",
    "description": ("Shutdown, restart or lock the computer. Shutdown/restart are irreversible, so the user must press "
                    "a CONFIRM button on screen; this tool only puts the button up."),
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["shutdown", "restart", "lock"]}}, "required": ["action"]},
}
CMD = {
    "shutdown": {"Windows": ["shutdown", "/s", "/t", "5"], "Darwin": ["osascript", "-e", 'tell app "System Events" to shut down'], "Linux": ["systemctl", "poweroff"]},
    "restart": {"Windows": ["shutdown", "/r", "/t", "5"], "Darwin": ["osascript", "-e", 'tell app "System Events" to restart'], "Linux": ["systemctl", "reboot"]},
    "lock": {"Windows": ["rundll32.exe", "user32.dll,LockWorkStation"], "Darwin": ["pmset", "displaysleepnow"], "Linux": ["loginctl", "lock-session"]},
}


def handler(params, ctx):
    a = params["action"]
    cmd = CMD[a][OS]
    run = lambda: (subprocess.run(cmd, check=True), "done")[1]
    if a == "lock":
        return run()
    return ctx.confirm(a.upper(), run)   # token is issued by the UI, not by the model
