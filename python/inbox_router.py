import argparse
import os
import re
import sys
from datetime import datetime

import devtools_header_utils as dhu


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


def sanitize_segment(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if not value:
        value = fallback
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def route_file(file_path: str, inbox_dir: str, dry_run: bool = False):
    header, err = dhu.load_header_from_file(file_path)
    if header is None:
        return file_path, None, f"SKIP: {err}"
    category = sanitize_segment(header.get("category"), "uncategorized")
    plugin = sanitize_segment(header.get("plugin"), "GLOBAL")
    dest_dir = os.path.join(inbox_dir, category, plugin)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
    if dry_run:
        return file_path, dest_path, f"DRY-RUN: would move -> {dest_path}"
    try:
        os.replace(file_path, dest_path)
        return file_path, dest_path, f"MOVED -> {dest_path}"
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
        if not dhu.is_text_file_name(entry):
            continue
        results.append(route_file(full_path, inbox_dir, dry_run=dry_run))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Route [SOTS_DEVTOOLS] inbox files.")
    parser.add_argument("--inbox-dir", type=str, default="chatgpt_inbox")
    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.path.join("DevTools", "logs"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    debug_print("Starting inbox_router")
    debug_print(f"Inbox directory: {args.inbox_dir}")
    debug_print(f"Log directory:   {args.log_dir}")
    debug_print(f"Dry run:         {args.dry_run}")

    try:
        results = scan_inbox(args.inbox_dir, dry_run=args.dry_run)
    except Exception as exc:
        debug_print(f"FATAL: {exc}")
        return 1

    log_lines = []
    moved = skipped = errors = 0
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
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
