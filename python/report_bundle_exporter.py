
"""
report_bundle_exporter.py
-------------------------
Bundles related logs/reports into a single text file for easy review or for
sending back to ChatGPT via Send2SOTS.

Behavior:
  - Searches one or more source directories for files whose names contain a
    given --category substring (case-insensitive).
  - For each matching file, copies up to --max-lines lines into the bundle,
    with a header separating files.
  - Writes the bundle into --output-dir (default: DevTools/exports).

Usage example:
    python report_bundle_exporter.py --category tagmanager --sources DevTools/logs DevTools/reports
"""

import argparse
import os
import sys
from datetime import datetime


def debug_print(msg: str) -> None:
    print(f"[report_bundle_exporter] {msg}")


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def find_matching_files(sources, category: str):
    matches = []
    cat_lower = category.lower()
    for src in sources:
        if not os.path.isdir(src):
            continue
        for root, _, files in os.walk(src):
            for name in files:
                if cat_lower in name.lower():
                    matches.append(os.path.join(root, name))
    return sorted(matches)


def bundle_files(paths, max_lines: int):
    lines = []
    for path in paths:
        lines.append("=" * 72)
        lines.append(f"FILE: {path}")
        lines.append("=" * 72)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncated at {max_lines} lines)")
                        break
                    lines.append(line.rstrip("\n"))
        except Exception as exc:
            lines.append(f"[ERROR] failed to read {path}: {exc}")
        lines.append("")
    return lines


def write_bundle(output_dir: str, category: str, lines):
    ensure_dir(output_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_bundle_{category}.txt"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export a bundled report from DevTools logs/reports.")
    parser.add_argument(
        "--category",
        required=True,
        help="Substring to match in file names (case-insensitive).",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=[os.path.join("DevTools", "logs"), os.path.join("DevTools", "reports")],
        help="Source directories to scan (default: DevTools/logs DevTools/reports).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=400,
        help="Maximum lines to read from each file (default: 400).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join("DevTools", "exports"),
        help="Directory to write the bundle into (default: DevTools/exports).",
    )

    args = parser.parse_args(argv)

    debug_print("Starting report_bundle_exporter")
    debug_print(f"Category:   {args.category}")
    debug_print(f"Sources:    {args.sources}")
    debug_print(f"Max lines:  {args.max_lines if hasattr(args, 'max-lines') else args.max_lines}")
    debug_print(f"Output dir: {args.output_dir}")

    matches = find_matching_files(args.sources, args.category)
    if not matches:
        debug_print("No matching files found.")
        return 0

    debug_print(f"Found {len(matches)} matching files.")
    for m in matches:
        debug_print(f"  - {m}")

    lines = bundle_files(matches, args.max_lines)
    bundle_path = write_bundle(args.output_dir, args.category, lines)
    debug_print(f"Bundle written to: {bundle_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
