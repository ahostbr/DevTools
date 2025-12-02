
"""
validate_sots_pack.py
----------------------
Validates a single [SOTS_DEVTOOLS] pack file for basic structural correctness.

Checks performed:
  - File exists and is readable.
  - Contains a [SOTS_DEVTOOLS] ... [/SOTS_DEVTOOLS] header block.
  - Header has at least a 'tool:' entry.
  - Optionally warns if the 'tool' is not in a known set of tools.
  - Optionally validates any path-like fields if a --project-root is given
    (keys checked: 'path', 'file', 'target', 'target_file').

It prints a human-readable VALIDATION REPORT and writes a log file.

Usage example:
    python validate_sots_pack.py --file chatgpt_inbox/my_pack.txt
    python validate_sots_pack.py --file chatgpt_inbox/my_pack.txt --project-root E:\\SAS\\ShadowsAndShurikens

Exit codes:
  0 -> validation passed (no fatal errors)
  1 -> validation failed (missing header, missing tool, file unreadable, etc.)
"""

import argparse
import os
import sys
from datetime import datetime


HEADER_START = "[SOTS_DEVTOOLS]"
HEADER_END = "[/SOTS_DEVTOOLS]"


# This is a *non-strict* suggested list. Unknown tools are a WARNING, not fatal.
KNOWN_TOOLS = {
    "quick_search",
    "regex_search",
    "run_python_script",
    "apply_json_pack",
    "version_cleanup",
    "mass_regex_edit",
    "pack_lint",
    "devtools_status_update",
    "export_report_bundle",
    "pipeline_hub",
}


def debug_print(msg: str) -> None:
    print(f"[validate_sots_pack] {msg}")


def ensure_log_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_log(log_dir: str, lines) -> str:
    ensure_log_dir(log_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"validate_sots_pack_{ts}.log")
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
    # Skip the first [SOTS_DEVTOOLS] line
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


def is_path_key(key: str) -> bool:
    """
    Basic heuristic to decide which keys should be treated as file-system paths.
    """
    return key in {"path", "file", "target", "target_file", "script_path", "config_path"}


def validate_pack(file_path: str, project_root: str | None):
    report_lines = []
    fatal_errors = 0
    warnings = 0

    report_lines.append(f"VALIDATION REPORT for: {file_path}")
    report_lines.append("-" * 72)

    if not os.path.isfile(file_path):
        msg = f"FATAL: file does not exist or is not a file: {file_path}"
        debug_print(msg)
        report_lines.append(msg)
        fatal_errors += 1
        return report_lines, fatal_errors, warnings

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        msg = f"FATAL: failed to read file: {exc}"
        debug_print(msg)
        report_lines.append(msg)
        fatal_errors += 1
        return report_lines, fatal_errors, warnings

    header = parse_header_block(text)
    if header is None:
        msg = "FATAL: no [SOTS_DEVTOOLS] header block found"
        debug_print(msg)
        report_lines.append(msg)
        fatal_errors += 1
        return report_lines, fatal_errors, warnings

    report_lines.append("Header fields:")
    for k, v in sorted(header.items()):
        report_lines.append(f"  {k}: {v}")
    report_lines.append("")

    tool = header.get("tool")
    if not tool:
        msg = "FATAL: header is missing required 'tool:' field"
        debug_print(msg)
        report_lines.append(msg)
        fatal_errors += 1
    else:
        tool_name = tool.strip()
        report_lines.append(f"OK: tool field present -> '{tool_name}'")
        if tool_name not in KNOWN_TOOLS:
            msg = (
                f"WARNING: tool '{tool_name}' is not in KNOWN_TOOLS; "
                "this may be fine, but double-check spelling/config."
            )
            debug_print(msg)
            report_lines.append(msg)
            warnings += 1

    # Optional path checks
    if project_root is not None:
        report_lines.append("Path checks (relative to project root):")
        for key, value in header.items():
            if not is_path_key(key):
                continue
            raw_value = value.strip()
            if not raw_value:
                continue

            candidate = raw_value
            if not os.path.isabs(candidate):
                candidate = os.path.join(project_root, candidate)
            candidate = os.path.normpath(candidate)

            if os.path.exists(candidate):
                msg = f"OK: {key} -> {candidate} exists"
            else:
                msg = f"WARNING: {key} -> {candidate} does not exist"
                warnings += 1
            debug_print(msg)
            report_lines.append("  " + msg)
    else:
        report_lines.append("Skipping path checks (no --project-root provided).")

    if fatal_errors == 0:
        report_lines.append("RESULT: PASS (no fatal errors).")
    else:
        report_lines.append(f"RESULT: FAIL ({fatal_errors} fatal error(s)).")

    if warnings > 0:
        report_lines.append(f"Warnings: {warnings} (non-fatal).")

    return report_lines, fatal_errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a [SOTS_DEVTOOLS] pack file.")
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the pack file to validate.",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Optional project root for validating path-like header fields.",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.path.join("DevTools", "logs"),
        help="Directory to write validation logs into (default: DevTools/logs).",
    )

    args = parser.parse_args(argv)

    debug_print(f"Starting validate_sots_pack")
    debug_print(f"Pack file:    {args.file}")
    debug_print(f"Project root: {args.project_root or '(none)'}")
    debug_print(f"Log directory:{args.log_dir}")

    report_lines, fatal_errors, warnings = validate_pack(args.file, args.project_root)

    for line in report_lines:
        print(line)

    log_path = write_log(args.log_dir, report_lines)
    debug_print(f"Log written to: {log_path}")

    return 0 if fatal_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
