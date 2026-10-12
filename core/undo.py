"""One shared undo stack. Actions register a closure that reverses themselves."""
import threading

_stack, _lock = [], threading.Lock()


def register(description, fn):
    with _lock:
        _stack.append((description, fn))
        del _stack[:-50]


def undo():
    with _lock:
        if not _stack:
            return "Nothing to undo."
        desc, fn = _stack.pop()
    try:
        fn()
        return f"Undone: {desc}"
    except Exception as e:
        return f"Could not undo '{desc}': {e}"
