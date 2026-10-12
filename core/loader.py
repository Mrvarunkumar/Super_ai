"""Skill discovery. Every .py in actions/ and plugins/ that defines TOOL + handler
is loaded at launch. A broken skill is reported and skipped, never fatal."""
import importlib.util
from .config import ROOT


def discover():
    skills, errors = {}, []
    for folder in ("actions", "plugins"):
        for f in sorted((ROOT / folder).glob("*.py")):
            if f.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"skill_{f.stem}", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                tool, handler = mod.TOOL, mod.handler
                assert isinstance(tool, dict) and tool.get("name") and tool.get("description")
                assert callable(handler)
                skills[tool["name"]] = (tool, handler)
            except ModuleNotFoundError as e:
                errors.append(f"{folder}/{f.name}: needs '{e.name}' (pip install {e.name})")
            except Exception as e:
                errors.append(f"{folder}/{f.name}: {e}")
    return skills, errors
