TOOL = {
    "name": "computer_control",
    "description": "Control keyboard and mouse: type text, press keys, hotkeys (e.g. ctrl+c), click, scroll.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["type", "press", "hotkey", "click", "scroll", "move"]},
        "text": {"type": "string", "description": "Text to type, key name, or '+'-joined hotkey like 'ctrl+shift+t'"},
        "x": {"type": "number"}, "y": {"type": "number"},
        "amount": {"type": "number", "description": "Scroll clicks (positive = up)"}},
        "required": ["action"]},
}


def handler(params, ctx):
    import pyautogui
    pyautogui.PAUSE = 0.05
    a, t = params.get("action"), params.get("text", "")
    x, y = params.get("x"), params.get("y")
    try:
        if a == "type": pyautogui.write(t, interval=0.02)
        elif a == "press": pyautogui.press(t.lower())
        elif a == "hotkey": pyautogui.hotkey(*[k.strip().lower() for k in t.split("+")])
        elif a == "click":
            pyautogui.click(x, y) if x is not None and y is not None else pyautogui.click()
        elif a == "move": pyautogui.moveTo(x, y, duration=0.2)
        elif a == "scroll": pyautogui.scroll(int(params.get("amount", -5)))
        else: return f"Unknown action {a}"
        return f"Done: {a} {t}".strip()
    except Exception as e:
        return f"Failed: {e}"
