from __future__ import annotations
from pathlib import Path


def get_tools_root() -> Path:
    return Path(__file__).resolve().parent


def get_project_root() -> Path:
    # Assumes tools live under <ProjectRoot>/DevTools/python
    tools_root = get_tools_root()
    return tools_root.parent.parent


def get_plugins_dir() -> Path:
    return get_project_root() / "Plugins"
