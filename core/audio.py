"""Audio device helpers. Devices are stored by name (indices shift when you plug things in)."""


def resolve(name, kind):
    """Return a device index for a name substring, or None for the system default."""
    if not name:
        return None
    import sounddevice as sd
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    for i, d in enumerate(sd.query_devices()):
        if d[key] > 0 and name.lower() in d["name"].lower():
            return i
    return None


def list_devices():
    import sounddevice as sd
    for i, d in enumerate(sd.query_devices()):
        kinds = ("in " if d["max_input_channels"] else "") + ("out" if d["max_output_channels"] else "")
        print(f"{i:3d}  [{kinds:6s}] {d['name']}")
