#!/usr/bin/env python3
"""
devtools_selftest.py
--------------------
Quick health check for the SOTS DevTools toolbox.

It walks the DevTools/python directory, and for each .py file:
  - In --mode compile (default): compiles the source to bytecode to catch
    syntax errors.
  - In --mode import: tries to import the module via importlib and reports
    any exceptions (including missing dependencies, bad top-level code, etc).

Results are:
  - Printed to stdout.
  - Written to DevTools/logs/devtools_selftest_YYYYMMDD_HHMMSS.log

Exit codes:
  0 -> no errors (only OK/WARN)
  1 -> at least one ERROR encountered
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
TOOLS_ROOT = THIS_FILE.parent                      # .../DevTools/python
PROJECT_ROOT = TOOLS_ROOT.parent.parent            # .../ShadowsAndShurikens
DEFAULT_PYTHON_DIR = TOOLS_ROOT
DEFAULT_LOG_DIR = PROJECT_ROOT / "DevTools" / "logs"


def debug_print(msg: str) -> None:
    print(f"[devtools_selftest] {msg}")


def ensure_log_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_log(log_dir: Path, lines: List[str]) -> Path:
    ensure_log_dir(log_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"devtools_selftest_{ts}.log"
    with log_path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    return log_path


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------

def discover_python_files(root: Path, recursive: bool) -> List[Path]:
    if recursive:
        return sorted(p for p in root.rglob("*.py") if p.is_file())
    return sorted(p for p in root.glob("*.py") if p.is_file())


def check_compile(path: Path) -> Tuple[str, str]:
    """
    Try to compile a module. Returns (status, detail):

    status: "OK" or "ERROR"
    detail: message
    """
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        return "ERROR", f"Failed to read file: {exc}"

    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        msg = f"SyntaxError at line {exc.lineno}: {exc.msg}"
        return "ERROR", msg
    except Exception as exc:
        msg = "".join(
            traceback.format_exception_only(type(exc), exc)
        ).strip()
        return "ERROR", f"Unexpected error while compiling: {msg}"

    return "OK", "compiled successfully"


def module_name_for(path: Path, python_root: Path) -> str:
    """
    Produce a stable module-like name for importlib usage.
    """
    rel = path.relative_to(python_root)
    # e.g., "subdir/foo.py" -> "subdir.foo"
    parts = list(rel.with_suffix("").parts)
    return "devtools_" + "_".join(parts)


def check_import(path: Path, python_root: Path) -> Tuple[str, str]:
    """
    Try to import a module from the given path. Returns (status, detail).

    status: "OK", "WARN", or "ERROR"
    """
    name = module_name_for(path, python_root)

    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return "ERROR", "Could not create import spec/loader."
        mod = importlib.util.module_from_spec(spec)

        # Make sure the tools root is on sys.path so intra-DevTools imports work.
        if str(python_root) not in sys.path:
            sys.path.insert(0, str(python_root))

        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return "OK", "imported successfully"

    except SystemExit as exc:
        code = exc.code
        # If a module calls sys.exit(0) on import (bad style), we treat as WARN.
        return "WARN", f"SystemExit({code}) raised during import (module may auto-exit on import)."

    except Exception as exc:
        msg = "".join(
            traceback.format_exception_only(type(exc), exc)
        ).strip()
        return "ERROR", f"Exception during import: {msg}"


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_selftest(
    python_dir: Path,
    recursive: bool,
    mode: str,
    log_dir: Path,
) -> Tuple[List[str], int]:
    """
    Run the selftest and return (log_lines, num_errors).
    """
    log_lines: List[str] = []

    log_lines.append("DEVTOOLS SELFTEST REPORT")
    log_lines.append("-" * 72)
    log_lines.append(f"Project root: {PROJECT_ROOT}")
    log_lines.append(f"Python dir:  {python_dir}")
    log_lines.append(f"Mode:        {mode}")
    log_lines.append(f"Recursive:   {recursive}")
    log_lines.append("")

    if not python_dir.is_dir():
        msg = f"ERROR: python dir does not exist: {python_dir}"
        log_lines.append(msg)
        return log_lines, 1

    files = discover_python_files(python_dir, recursive)
    if not files:
        log_lines.append("No .py files found to test.")
        return log_lines, 0

    log_lines.append(f"Discovered {len(files)} .py file(s).")
    log_lines.append("")

    num_errors = 0
    num_warns = 0
    num_ok = 0

    for path in files:
        # Skip __init__ if present; it's often empty or package-only.
        if path.name == "__init__.py":
            continue

        rel = path.relative_to(PROJECT_ROOT)
        if mode == "compile":
            status, detail = check_compile(path)
        else:
            status, detail = check_import(path, python_dir)

        if status == "OK":
            num_ok += 1
        elif status == "WARN":
            num_warns += 1
        else:
            num_errors += 1

        log_lines.append(f"[{status}] {rel}")
        log_lines.append(f"    -> {detail}")

    log_lines.append("")
    log_lines.append("SUMMARY")
    log_lines.append("-" * 72)
    log_lines.append(f"OK:    {num_ok}")
    log_lines.append(f"WARN:  {num_warns}")
    log_lines.append(f"ERROR: {num_errors}")
    log_lines.append(f"TOTAL: {num_ok + num_warns + num_errors}")
    return log_lines, num_errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a health check over DevTools/python modules."
    )
    parser.add_argument(
        "--python-dir",
        type=str,
        default=str(DEFAULT_PYTHON_DIR),
        help="Root folder to scan for .py files (default: DevTools/python).",
    )
    parser.add_argument(
        "--mode",
        choices=["compile", "import"],
        default="compile",
        help="compile: just compile source; import: actually import each module.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="If set, scan subdirectories recursively.",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=str(DEFAULT_LOG_DIR),
        help="Directory for selftest logs (default: <ProjectRoot>/DevTools/logs).",
    )

    args = parser.parse_args(argv)

    python_dir = Path(args.python_dir).resolve()
    log_dir = Path(args.log_dir).resolve()

    debug_print(f"Python dir: {python_dir}")
    debug_print(f"Mode:       {args.mode}")
    debug_print(f"Recursive:  {args.recursive}")
    debug_print(f"Log dir:    {log_dir}")

    lines, num_errors = run_selftest(
        python_dir=python_dir,
        recursive=args.recursive,
        mode=args.mode,
        log_dir=log_dir,
    )

    # Print to console
    for line in lines:
        print(line)

    # Write to log
    log_path = write_log(log_dir, lines)
    debug_print(f"Selftest log written to: {log_path}")

    return 0 if num_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
