from __future__ import annotations
from pathlib import Path
import shutil


def remove_dir(path: Path, dry_run: bool = True) -> None:
    if not path.exists():
        return
    if dry_run:
        print(f"[DRY-RUN] Would remove: {path}")
    else:
        print(f"[REMOVE] {path}")
        shutil.rmtree(path, ignore_errors=True)
