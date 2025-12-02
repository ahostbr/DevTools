
"""
log_error_digest.py
-------------------
Scans Unreal Engine log files (Saved/Logs/*.log by default) and produces a
ranked digest of recurring error-like messages.

It looks for lines containing:
  - "Error:"
  - "Fatal:"
  - "ensure(" or "ensureMsgf"
  - "check(" or "checkf("
  - "Assertion failed"

For each match, it extracts the substring from the first keyword onward and
groups identical messages, counting occurrences and tracking where they first
appeared (file + line number).

Output:
  - Prints a "TOP N" summary to stdout.
  - Writes a detailed report to a text file in DevTools/logs by default.

Usage example:
    python log_error_digest.py
    python log_error_digest.py --logs-dir Saved/Logs --limit 5 --top 15

This script is intended as a debugging helper for the SOTS DevTools pipeline.
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime


KEYWORDS = [
    "Error:",
    "Fatal:",
    "ensure(",
    "ensureMsgf",
    "check(",
    "checkf(",
    "Assertion failed",
]


def debug_print(msg: str) -> None:
    print(f"[log_error_digest] {msg}")


def ensure_log_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_log(log_dir: str, lines) -> str:
    ensure_log_dir(log_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"log_error_digest_{ts}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    return log_path


def find_logs(logs_dir: str, limit: int):
    if not os.path.isdir(logs_dir):
        raise RuntimeError(f"Logs directory does not exist: {logs_dir}")

    entries = []
    for entry in os.listdir(logs_dir):
        if not entry.lower().endswith(".log"):
            continue
        full_path = os.path.join(logs_dir, entry)
        if not os.path.isfile(full_path):
            continue
        mtime = os.path.getmtime(full_path)
        entries.append((mtime, full_path))

    entries.sort(reverse=True)  # newest first
    return [path for _, path in entries[:limit]]


def extract_key_segment(line: str) -> str | None:
    """
    Returns the substring of 'line' beginning at the first error keyword,
    or None if no keyword is found.
    """
    lowest_idx = None
    for kw in KEYWORDS:
        idx = line.find(kw)
        if idx != -1:
            if lowest_idx is None or idx < lowest_idx:
                lowest_idx = idx
    if lowest_idx is None:
        return None
    return line[lowest_idx:].strip()


def digest_logs(log_files, max_message_length: int = 200):
    """
    Returns a dict mapping message -> dict(count=int, first=(file, line_no)).
    """
    summary = {}

    for log_path in log_files:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                msg = extract_key_segment(line)
                if msg is None:
                    continue

                key = msg
                if len(key) > max_message_length:
                    key = key[: max_message_length - 3] + "..."

                if key not in summary:
                    summary[key] = {
                        "count": 1,
                        "first": (log_path, lineno),
                    }
                else:
                    summary[key]["count"] += 1

    return summary


def format_digest(summary: dict, top: int):
    """
    Returns a list of text lines describing the top N messages.
    """
    lines = []
    lines.append("LOG ERROR DIGEST")
    lines.append("-" * 72)

    if not summary:
        lines.append("No error-like messages found in the scanned logs.")
        return lines

    sorted_items = sorted(summary.items(), key=lambda kv: kv[1]["count"], reverse=True)
    lines.append(f"Top {min(top, len(sorted_items))} messages:")
    lines.append("")

    for rank, (msg, data) in enumerate(sorted_items[:top], start=1):
        count = data["count"]
        first_file, first_lineno = data["first"]
        lines.append(f"{rank}. Count: {count}")
        lines.append(f"   First seen: {first_file} (line {first_lineno})")
        lines.append(f"   Message: {msg}")
        lines.append("")

    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Digest UE log errors into a ranked summary.")
    parser.add_argument(
        "--logs-dir",
        type=str,
        default=os.path.join("Saved", "Logs"),
        help="Directory containing Unreal log files (default: Saved/Logs).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of most recent log files to scan (default: 10).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top messages to display (default: 10).",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.path.join("DevTools", "logs"),
        help="Directory to write the digest report into (default: DevTools/logs).",
    )

    args = parser.parse_args(argv)

    debug_print("Starting log_error_digest")
    debug_print(f"Logs directory: {args.logs_dir}")
    debug_print(f"Log files limit: {args.limit}")
    debug_print(f"Top messages:   {args.top}")
    debug_print(f"Report log dir: {args.log_dir}")

    try:
        log_files = find_logs(args.logs_dir, args.limit)
    except Exception as exc:
        debug_print(f"FATAL: {exc}")
        return 1

    if not log_files:
        debug_print("No .log files found to scan.")
        return 0

    debug_print(f"Scanning {len(log_files)} log file(s):")
    for path in log_files:
        debug_print(f"  - {path}")

    summary = digest_logs(log_files)
    lines = format_digest(summary, args.top)

    for line in lines:
        print(line)

    report_path = write_log(args.log_dir, lines)
    debug_print(f"Digest report written to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
