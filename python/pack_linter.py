
"""
pack_linter.py
--------------
Lints multiple [SOTS_DEVTOOLS] pack files at once, providing a quick overview of
which packs are structurally OK and which have missing or suspicious fields.

This is meant as a **multi-pack front-end** to validate_sots_pack.validate_pack,
plus some additional per-tool schema checks.

Behavior:
  - Scans --inbox-dir for text-like files (non-recursive by default).
  - For each file that contains a [SOTS_DEVTOOLS] header:
      * Runs validate_sots_pack.validate_pack() (if available).
      * Applies simple tool-specific checks:
          - quick_search: require 'search' and 'exts'.
          - mass_regex_edit: require 'search', 'replace', 'exts'.
      * Classifies status as OK / WARN / FAIL.

  - Prints a table-style summary to stdout.
  - Writes a detailed log into DevTools/logs/pack_linter_<timestamp>.log.

Usage example:
    python pack_linter.py --inbox-dir chatgpt_inbox --project-root E:\\SAS\\ShadowsAndShurikens
"""

import argparse
import os
import sys
from datetime import datetime

try:
    # Optional: use validate_sots_pack if present in the same folder.
    import validate_sots_pack
except ImportError:  # pragma: no cover - optional dependency
    validate_sots_pack = None


HEADER_START = "[SOTS_DEVTOOLS]"
HEADER_END = "[/SOTS_DEVTOOLS]"


def debug_print(msg: str) -> None:
    print(f"[pack_linter] {msg}")


def ensure_log_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_log(log_dir: str, lines) -> str:
    ensure_log_dir(log_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"pack_linter_{ts}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    return log_path


def parse_header_block(text: str):
    start_idx = text.find(HEADER_START)
    if start_idx == -1:
        return None
    end_idx = text.find(HEADER_END, start_idx)
    if end_idx == -1:
        return None

    block = text[start_idx:end_idx].splitlines()
    lines = block[1:]
    data = {}
    for line in lines:
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


def tool_schema_warnings(tool: str, header: dict) -> list[str]:
    warnings: list[str] = []
    t = (tool or "").strip()
    if t == "quick_search":
        if not header.get("search"):
            warnings.append("quick_search: missing 'search' field")
        if not header.get("exts"):
            warnings.append("quick_search: missing 'exts' field")
    elif t == "mass_regex_edit":
        if not header.get("search"):
            warnings.append("mass_regex_edit: missing 'search' field")
        if not header.get("replace"):
            warnings.append("mass_regex_edit: missing 'replace' field")
        if not header.get("exts"):
            warnings.append("mass_regex_edit: missing 'exts' field")
    return warnings


def iter_candidate_files(inbox_dir: str):
    for entry in sorted(os.listdir(inbox_dir)):
        full_path = os.path.join(inbox_dir, entry)
        if not os.path.isfile(full_path):
            continue
        if not entry.lower().endswith((".txt", ".md", ".log", ".cfg", ".json")):
            continue
        yield full_path


def lint_packs(inbox_dir: str, project_root: str | None):
    """
    Returns (rows, summary_counts)

    rows: list of dicts with keys: file, tool, status, details
    """
    rows = []
    summary = {"ok": 0, "warn": 0, "fail": 0, "skipped": 0}

    for file_path in iter_candidate_files(inbox_dir):
        rel = os.path.relpath(file_path, os.getcwd())
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as exc:
            msg = f"FAIL: cannot read file: {exc}"
            debug_print(f"{rel}: {msg}")
            rows.append({"file": rel, "tool": "?", "status": "FAIL", "details": msg})
            summary["fail"] += 1
            continue

        header = parse_header_block(text)
        if header is None:
            msg = "SKIP: no [SOTS_DEVTOOLS] header"
            debug_print(f"{rel}: {msg}")
            rows.append({"file": rel, "tool": "-", "status": "SKIP", "details": msg})
            summary["skipped"] += 1
            continue

        tool = header.get("tool", "").strip()
        overall_status = "OK"
        detail_msgs: list[str] = []

        # If validate_sots_pack is available, run it for this file.
        if validate_sots_pack is not None:
            rep_lines, fatal_errors, warnings = validate_sots_pack.validate_pack(
                file_path, project_root
            )
            if fatal_errors > 0:
                overall_status = "FAIL"
                detail_msgs.append(f"{fatal_errors} fatal error(s) from validate_sots_pack")
            if warnings > 0 and overall_status != "FAIL":
                overall_status = "WARN"
                detail_msgs.append(f"{warnings} warning(s) from validate_sots_pack")

        # Tool-specific schema hints
        schema_warnings = tool_schema_warnings(tool, header)
        if schema_warnings:
            if overall_status == "OK":
                overall_status = "WARN"
            detail_msgs.extend(schema_warnings)

        if not tool:
            if overall_status == "OK":
                overall_status = "FAIL"
            detail_msgs.append("missing 'tool' field")

        if not detail_msgs:
            detail_msgs.append("no issues detected")

        if overall_status == "OK":
            summary["ok"] += 1
        elif overall_status == "WARN":
            summary["warn"] += 1
        elif overall_status == "FAIL":
            summary["fail"] += 1

        rows.append(
            {
                "file": rel,
                "tool": tool or "?",
                "status": overall_status,
                "details": "; ".join(detail_msgs),
            }
        )

    return rows, summary


def format_table(rows, summary):
    lines: list[str] = []
    lines.append("PACK LINTER SUMMARY")
    lines.append("-" * 72)
    lines.append(
        f"OK={summary['ok']}  WARN={summary['warn']}  FAIL={summary['fail']}  SKIP={summary['skipped']}"
    )
    lines.append("")
    lines.append(f"{'STATUS':8}  {'TOOL':18}  FILE")
    lines.append("-" * 72)
    for row in rows:
        lines.append(
            f"{row['status']:8}  {row['tool'][:18]:18}  {row['file']}"
        )
        lines.append(f"    -> {row['details']}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint multiple [SOTS_DEVTOOLS] packs in an inbox directory.")
    parser.add_argument(
        "--inbox-dir",
        type=str,
        default="chatgpt_inbox",
        help="Inbox directory to scan (default: chatgpt_inbox).",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Optional project root for deeper validation (passed to validate_sots_pack).",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.path.join("DevTools", "logs"),
        help="Directory to write linter logs into (default: DevTools/logs).",
    )

    args = parser.parse_args(argv)

    debug_print("Starting pack_linter")
    debug_print(f"Inbox directory: {args.inbox_dir}")
    debug_print(f"Project root:    {args.project_root or '(none)'}")
    debug_print(f"Log directory:   {args.log_dir}")

    if not os.path.isdir(args.inbox_dir):
        debug_print(f"FATAL: inbox directory does not exist: {args.inbox_dir}")
        return 1

    rows, summary = lint_packs(args.inbox_dir, args.project_root)
    lines = format_table(rows, summary)

    for line in lines:
        print(line)

    log_path = write_log(args.log_dir, lines)
    debug_print(f"Log written to: {log_path}")

    # Non-zero exit if we have any FAILs
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
