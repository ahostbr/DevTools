
"""
inbox_router.py
----------------
Routes raw [SOTS_DEVTOOLS] prompt files in a chatgpt_inbox into a structured
folder layout based on header metadata (tool, plugin, target, etc.).

Default behavior:
  - Scan the given --inbox-dir for files (non-recursive).
  - For each file containing a [SOTS_DEVTOOLS] header:
      * Parse key: value pairs between [SOTS_DEVTOOLS] and [/SOTS_DEVTOOLS].
      * Determine:
          tool   -> header["tool"]          (fallback: "unknown")
          plugin -> one of:
                     header["plugin"] or
                     header["target_plugin"] or
                     header["target"] or
                     "misc"
      * Move the file into: <inbox-dir>/<tool>/<plugin>/

  - Writes a log file (by default DevTools/logs/inbox_router_<timestamp>.log)
    and prints a human-friendly summary to stdout.

Usage example:
    python inbox_router.py --inbox-dir chatgpt_inbox

This script is designed for MANUAL use in the SOTS DevTools pipeline.
It never auto-runs; you must explicitly invoke it.
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime


HEADER_START = "[SOTS_DEVTOOLS]"
HEADER_END = "[/SOTS_DEVTOOLS]"


def debug_print(msg: str) -> None:
    print(f"[inbox_router] {msg}")


def ensure_log_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_log(log_dir: str, lines) -> str:
    ensure_log_dir(log_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"inbox_router_{ts}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    return log_path


def sanitize_segment(value: str) -> str:
    value = value.strip()
    if not value:
        return "misc"
    # Replace any non-alphanumeric/underscore/dash with underscore
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def parse_header_block(text: str):
    """
    Returns a dict of key->value parsed from the [SOTS_DEVTOOLS] block.
    Keys are lowercased; values are stripped.
    """
    start_idx = text.find(HEADER_START)
    if start_idx == -1:
        return None
    end_idx = text.find(HEADER_END, start_idx)
    if end_idx == -1:
        return None

    # Extract everything between the markers (excluding the start line)
    header_text = text[start_idx:end_idx].splitlines()
    # First line is [SOTS_DEVTOOLS]; skip it
    header_lines = header_text[1:]

    data = {}
    for line in header_lines:
        striped = line.strip()
        if not striped or striped.startswith("#"):
            continue
        if ":" not in striped:
            continue
        key, value = striped.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        data[key] = value
    return data


def route_file(file_path: str, inbox_dir: str, dry_run: bool = False):
    """
    Reads file_path, parses the header, and returns (old_path, new_path, reason).
    If no routing should occur, new_path will be None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        return file_path, None, f"ERROR: failed to read file: {exc}"

    header = parse_header_block(text)
    if header is None:
        return file_path, None, "SKIP: no [SOTS_DEVTOOLS] header found"

    tool = sanitize_segment(header.get("tool", "unknown"))
    plugin = sanitize_segment(
        header.get("plugin")
        or header.get("target_plugin")
        or header.get("target")
        or header.get("category")
        or "misc"
    )

    dest_dir = os.path.join(inbox_dir, tool, plugin)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(file_path))

    if dry_run:
        reason = f"DRY-RUN: would move -> {dest_path}"
        return file_path, dest_path, reason

    try:
        os.replace(file_path, dest_path)
        reason = f"MOVED -> {dest_path}"
        return file_path, dest_path, reason
    except Exception as exc:
        return file_path, None, f"ERROR: move failed: {exc}"


def scan_inbox(inbox_dir: str, dry_run: bool = False):
    if not os.path.isdir(inbox_dir):
        raise RuntimeError(f"Inbox directory does not exist: {inbox_dir}")

    results = []
    for entry in sorted(os.listdir(inbox_dir)):
        full_path = os.path.join(inbox_dir, entry)
        if not os.path.isfile(full_path):
            continue
        # Only consider text-like files by default
        if not entry.lower().endswith((".txt", ".md", ".log", ".cfg", ".json")):
            continue

        old_path, new_path, reason = route_file(full_path, inbox_dir, dry_run=dry_run)
        results.append((old_path, new_path, reason))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Route [SOTS_DEVTOOLS] inbox files into structured subfolders.")
    parser.add_argument(
        "--inbox-dir",
        type=str,
        default="chatgpt_inbox",
        help="Path to the inbox directory containing raw [SOTS_DEVTOOLS] prompt files.",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.path.join("DevTools", "logs"),
        help="Directory to write routing logs into (default: DevTools/logs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, do not actually move files; just print what would happen.",
    )

    args = parser.parse_args(argv)

    debug_print(f"Starting inbox_router")
    debug_print(f"Inbox directory: {args.inbox_dir}")
    debug_print(f"Log directory:   {args.log_dir}")
    debug_print(f"Dry run:         {args.dry_run}")

    try:
        results = scan_inbox(args.inbox_dir, dry_run=args.dry_run)
    except Exception as exc:
        debug_print(f"FATAL: {exc}")
        return 1

    log_lines = []
    moved = 0
    skipped = 0
    errors = 0

    for old_path, new_path, reason in results:
        rel_old = os.path.relpath(old_path, start=os.getcwd())
        if new_path:
            rel_new = os.path.relpath(new_path, start=os.getcwd())
            msg = f"{rel_old} -> {rel_new} | {reason}"
        else:
            msg = f"{rel_old} | {reason}"

        log_lines.append(msg)
        debug_print(msg)

        if reason.startswith("MOVED"):
            moved += 1
        elif reason.startswith("ERROR"):
            errors += 1
        else:
            skipped += 1

    summary = f"SUMMARY: moved={moved}, skipped={skipped}, errors={errors}, total={len(results)}"
    debug_print(summary)
    log_lines.append(summary)

    log_path = write_log(args.log_dir, log_lines)
    debug_print(f"Log written to: {log_path}")

    # Exit code: non-zero if any errors occurred
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
