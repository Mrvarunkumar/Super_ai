import difflib, os, shutil, time
from pathlib import Path
from core import undo

ACTIONS = ["list", "read", "create", "write", "make_folder", "copy", "move", "rename", "delete", "find"]
TOOL = {
    "name": "file_controller",
    "description": ("File system operations. Paths may be absolute, '~/x', or start with Desktop/Documents/Downloads. "
                    "Everything that changes files can be undone with the undo tool. Delete moves to a trash folder."),
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ACTIONS},
        "path": {"type": "string", "description": "Target file or folder"},
        "destination": {"type": "string", "description": "For copy/move: destination. For rename: the new name"},
        "content": {"type": "string", "description": "Text for create/write"},
        "query": {"type": "string", "description": "For find: part of a filename"}},
        "required": ["action", "path"]},
}
KNOWN = {"desktop", "documents", "downloads", "pictures", "music", "videos"}
TRASH = Path.home() / ".jarvis_trash"
MAX_UNDO_BYTES = 1_000_000


def _p(s):
    s = os.path.expanduser((s or "").strip().strip('"'))
    p = Path(s)
    if not p.is_absolute():
        parts = p.parts
        if parts and parts[0].lower() in KNOWN:
            p = Path.home() / parts[0].capitalize() / Path(*parts[1:]) if len(parts) > 1 else Path.home() / parts[0].capitalize()
        else:
            p = Path.home() / p
    return p.resolve()


def _list(p, a):
    items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:60]
    return "\n".join(("[dir] " if i.is_dir() else "      ") + i.name for i in items) or "(empty)"


def _read(p, a):
    if p.stat().st_size > 2_000_000: return "File is too large to read aloud (>2 MB)."
    return p.read_text("utf-8", errors="replace")[:6000]


def _write(p, a, create=False):
    text = a.get("content", "")
    existed = p.exists()
    if create and existed:
        return f"{p.name} already exists. Use write to overwrite."
    old = None
    if existed and p.stat().st_size <= MAX_UNDO_BYTES:
        old = p.read_bytes()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, "utf-8")
    if not existed:
        undo.register(f"remove created file {p.name}", lambda: p.unlink(missing_ok=True))
        return f"Created {p}."
    if old is not None:
        undo.register(f"restore previous contents of {p.name}", lambda: p.write_bytes(old))
        return f"Wrote {p}."
    return f"Wrote {p}. (File was over 1 MB, so this cannot be undone.)"


def _mkdir(p, a):
    existed = p.exists()
    p.mkdir(parents=True, exist_ok=True)
    if not existed:
        undo.register(f"remove folder {p.name} (only if empty)", lambda: p.rmdir())
    return f"Folder ready: {p}"


def _copy(p, a):
    d = _p(a["destination"])
    if d.is_dir(): d = d / p.name
    shutil.copytree(p, d) if p.is_dir() else shutil.copy2(p, d)
    undo.register(f"remove the copy {d.name}", lambda: shutil.rmtree(d) if d.is_dir() else d.unlink())
    return f"Copied to {d}."


def _move(p, a):
    d = _p(a["destination"])
    if d.is_dir(): d = d / p.name
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(d))
    undo.register(f"move {d.name} back", lambda: shutil.move(str(d), str(p)))
    return f"Moved to {d}."


def _rename(p, a):
    d = p.with_name(a["destination"])
    p.rename(d)
    undo.register(f"rename {d.name} back to {p.name}", lambda: d.rename(p))
    return f"Renamed to {d.name}."


def _delete(p, a):
    TRASH.mkdir(exist_ok=True)
    t = TRASH / f"{int(time.time())}_{p.name}"
    shutil.move(str(p), str(t))
    undo.register(f"restore {p.name}", lambda: shutil.move(str(t), str(p)))
    return f"Moved {p.name} to trash (undoable)."


def _find(p, a):
    q = (a.get("query") or p.name).lower()
    root = p if p.is_dir() else p.parent
    hits = []
    for dp, _, files in os.walk(root):
        for f in files:
            if q in f.lower(): hits.append(os.path.join(dp, f))
            if len(hits) >= 20: return "\n".join(hits)
    return "\n".join(hits) or "No matches."


FN = {"list": _list, "read": _read, "create": lambda p, a: _write(p, a, True), "write": _write,
      "make_folder": _mkdir, "copy": _copy, "move": _move, "rename": _rename, "delete": _delete, "find": _find}


def handler(params, ctx):
    a = (params.get("action") or "").strip().lower()
    if a not in FN:
        m = difflib.get_close_matches(a, ACTIONS, n=1, cutoff=0.6)
        if not m: return f"Unknown action '{a}'. Valid: {', '.join(ACTIONS)}"
        a = m[0]
    try:
        p = _p(params.get("path", ""))
        if a not in ("create", "write", "make_folder", "find") and not p.exists():
            return f"{p} does not exist."
        return FN[a](p, params)
    except Exception as e:
        return f"Error: {e}"
