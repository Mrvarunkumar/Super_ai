"""Long-term memory. Nothing is silently deleted; the prompt carries a small core,
the rest is looked up on demand with the `memory` tool."""
import json, re, threading, time
from .config import ROOT

FILE = ROOT / "memory" / "long_term.json"
_lock = threading.Lock()


def _norm(key):
    return re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_") or "note"


def _load():
    try:
        return json.loads(FILE.read_text("utf-8"))
    except Exception:
        return {}


def _save(d):
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), "utf-8")


def remember(key, value, category="general"):
    key = _norm(key)
    with _lock:
        d = _load()
        d[key] = {"value": str(value), "category": category or "general",
                  "updated": time.strftime("%Y-%m-%d %H:%M")}
        _save(d)
    return key


def forget(key):
    key = _norm(key)
    with _lock:
        d = _load()
        gone = d.pop(key, None) is not None
        _save(d)
    return gone


def all_facts():
    return _load()


def search(query, limit=8):
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 1]
    scored = []
    for k, v in _load().items():
        hay = f"{k} {v['value']} {v['category']}".lower()
        score = sum(hay.count(w) for w in words)
        if score:
            scored.append((score, k, v))
    scored.sort(key=lambda x: -x[0])
    return [(k, v) for _, k, v in scored[:limit]]


def prompt_block(budget=1200):
    d = _load()
    if not d:
        return ""
    identity = {k: v for k, v in d.items() if v["category"] == "identity"}
    rest = sorted(((k, v) for k, v in d.items() if v["category"] != "identity"),
                  key=lambda kv: kv[1]["updated"], reverse=True)
    lines, used, shown = [], 0, set(identity)
    for k, v in identity.items():
        line = f"- {k}: {v['value']}"
        lines.append(line); used += len(line)
    for k, v in rest:
        line = f"- {k}: {v['value']}"
        if used + len(line) > budget:
            break
        lines.append(line); used += len(line); shown.add(k)
    # Index of keys that did not fit, interleaved by category so no category hides the rest.
    by = {}
    for k, v in rest:
        if k not in shown:
            by.setdefault(v["category"], []).append(k)
    index = []
    while any(by.values()):
        for c in by:
            if by[c]:
                index.append(by[c].pop(0))
    out = "Known facts about the user:\n" + "\n".join(lines)
    if index:
        out += ("\n\nMore stored facts (read them with the memory tool, action=recall): "
                + ", ".join(index[:60]))
    return out
