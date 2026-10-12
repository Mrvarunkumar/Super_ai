"""Push-to-talk: hold Ctrl+Space. Uses pynput; degrades quietly if unavailable."""


class PushToTalk:
    def __init__(self):
        self.active = False
        self._ctrl = self._space = False
        self._listener = None

    def start(self):
        try:
            from pynput import keyboard
        except Exception:
            return False
        K = keyboard.Key

        def update():
            self.active = self._ctrl and self._space

        def press(k):
            if k in (K.ctrl, K.ctrl_l, K.ctrl_r): self._ctrl = True
            elif k == K.space: self._space = True
            update()

        def release(k):
            if k in (K.ctrl, K.ctrl_l, K.ctrl_r): self._ctrl = False
            elif k == K.space: self._space = False
            update()

        try:
            self._listener = keyboard.Listener(on_press=press, on_release=release)
            self._listener.daemon = True
            self._listener.start()
            return True
        except Exception:
            return False
