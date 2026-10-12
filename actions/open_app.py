import os, shutil, subprocess
from core.config import OS

TOOL = {
    "name": "open_app",
    "description": "Open / launch an application on the computer by name (e.g. Chrome, Spotify, Calculator, VS Code).",
    "parameters": {"type": "object", "properties": {
        "app_name": {"type": "string", "description": "Application name"}}, "required": ["app_name"]},
}

WIN = {"calculator": "calc", "notepad": "notepad", "explorer": "explorer", "files": "explorer",
       "vscode": "code", "vs code": "code", "terminal": "wt", "paint": "mspaint", "settings": "ms-settings:",
       "chrome": "chrome", "edge": "msedge", "firefox": "firefox", "word": "winword", "excel": "excel"}
LIN = {"calculator": "gnome-calculator", "files": "nautilus", "vscode": "code", "vs code": "code",
       "terminal": "x-terminal-emulator", "chrome": "google-chrome", "settings": "gnome-control-center"}


def handler(params, ctx):
    name = params["app_name"].strip()
    low = name.lower()
    if OS == "Windows":
        target = WIN.get(low, name)
        subprocess.Popen(["cmd", "/c", "start", "", target], creationflags=0x08000000)
        return f"Asked Windows to open {name}."
    if OS == "Darwin":
        r = subprocess.run(["open", "-a", name], capture_output=True, text=True)
        return f"Opened {name}." if r.returncode == 0 else f"Could not open {name}: {r.stderr.strip()}"
    exe = shutil.which(LIN.get(low, low)) or shutil.which(low.replace(" ", "-"))
    if not exe:
        return f"Could not find an application called {name}."
    subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Opened {name}."
