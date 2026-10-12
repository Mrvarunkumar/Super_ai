"""Entry point:  python main.py        (python main.py --devices lists audio devices)"""
import sys

for s in (sys.stdout, sys.stderr):           # never die on a non-UTF-8 console
    try: s.reconfigure(errors="replace")
    except Exception: pass

from core import config


def main():
    if "--devices" in sys.argv:
        from core.audio import list_devices
        return list_devices()
    from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit
    app = QApplication(sys.argv)
    if not config.api_key():
        key, ok = QInputDialog.getText(None, "Gemini API key",
                                       "Paste your Gemini API key (free at aistudio.google.com):",
                                       QLineEdit.EchoMode.Password)
        if not ok or not key.strip():
            return
        config.put("api_key", key.strip())
    if not config.get("user_name"):
        name, ok = QInputDialog.getText(None, "Welcome", "What should I call you?")
        if ok and name.strip(): config.put("user_name", name.strip())
    from core.engine import Engine
    from ui import Bridge, MainWindow
    bridge = Bridge(); engine = Engine(bridge)
    win = MainWindow(bridge, engine); win.show()
    engine.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
