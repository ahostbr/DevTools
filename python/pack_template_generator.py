
"""
pack_template_generator.py
--------------------------
Generates skeleton [SOTS_DEVTOOLS] pack files for common workflows so you
don't have to hand-write headers every time.

This script is **non-interactive by default** and is meant to be safe for
both human use and VSCode Buddy use.

Usage examples:
    python pack_template_generator.py --template tag_audit
    python pack_template_generator.py --template omnitrace_sweep --output-dir chatgpt_inbox/templates

Templates:
  - tag_audit
  - omnitrace_sweep
  - kem_execution_audit

Files are written into --output-dir (default: chatgpt_inbox) with a
timestamped name and a short description in the body.
"""

import argparse
import os
import sys
from datetime import datetime


def debug_print(msg: str) -> None:
    print(f"[pack_template_generator] {msg}")


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_file(path: str, lines) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")


def make_template(template: str) -> list[str]:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if template == "tag_audit":
        return [
            "[SOTS_DEVTOOLS]",
            "tool: quick_search",
            "scope: Plugins",
            "subscope: SOTS_*",
            "search: \"RequestGameplayTag(\"",
            "exts: .cpp|.h",
            "category: tagmanager_audit",
            "mode: manual",
            f"created: {ts}",
            "[/SOTS_DEVTOOLS]",
            "",
            "Body:",
            "  TagManager V2 audit template.",
            "  TODO: refine search filters, adjust scope and report paths as needed.",
        ]
    elif template == "omnitrace_sweep":
        return [
            "[SOTS_DEVTOOLS]",
            "tool: quick_search",
            "scope: Plugins",
            "subscope: SOTS_*",
            "search: \"OmniTrace\"",
            "exts: .cpp|.h",
            "category: omnitrace_sweep",
            "mode: manual",
            f"created: {ts}",
            "[/SOTS_DEVTOOLS]",
            "",
            "Body:",
            "  OmniTrace integration sweep template.",
            "  TODO: refine search term(s) and report location.",
        ]
    elif template == "kem_execution_audit":
        return [
            "[SOTS_DEVTOOLS]",
            "tool: quick_search",
            "scope: Plugins/SOTS_KillExecutionManager",
            "search: \"Execution\"",
            "exts: .cpp|.h",
            "category: kem_audit",
            "mode: manual",
            f"created: {ts}",
            "[/SOTS_DEVTOOLS]",
            "",
            "Body:",
            "  KEM Execution audit template.",
            "  TODO: refine search term(s) to match your current KEM naming.",
        ]
    else:
        raise ValueError(f"Unknown template: {template}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate skeleton [SOTS_DEVTOOLS] pack templates.")
    parser.add_argument(
        "--template",
        required=True,
        choices=["tag_audit", "omnitrace_sweep", "kem_execution_audit"],
        help="Template name to generate.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="chatgpt_inbox",
        help="Directory to write the new pack into (default: chatgpt_inbox).",
    )

    args = parser.parse_args(argv)

    debug_print("Starting pack_template_generator")
    debug_print(f"Template:   {args.template}")
    debug_print(f"Output dir: {args.output_dir}")

    ensure_dir(args.output_dir)

    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts_name}_{args.template}.txt"
    path = os.path.join(args.output_dir, filename)

    try:
        lines = make_template(args.template)
    except ValueError as exc:
        debug_print(f"FATAL: {exc}")
        return 1

    write_file(path, lines)
    debug_print(f"Template written to: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
