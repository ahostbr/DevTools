import os
import sys

import inbox_router
import validate_sots_pack
import log_error_digest
import pack_linter
import pack_template_generator
import devtools_status_dashboard
import report_bundle_exporter
import devtools_selftest


def debug_print(msg: str) -> None:
    print(f"[sots_pipeline_hub] {msg}")


def ask(prompt: str, default: str | None = None) -> str:
    if default is not None:
        full = f"{prompt} [{default}]: "
    else:
        full = f"{prompt}: "
    value = input(full).strip()
    if not value and default is not None:
        return default
    return value


def menu_route_inbox():
    debug_print("Selected: Route inbox")
    inbox_dir = ask("Inbox directory", "chatgpt_inbox")
    dry = ask("Dry run? (y/n)", "n").lower().startswith("y")
    argv = ["--inbox-dir", inbox_dir]
    if dry:
        argv.append("--dry-run")
    rc = inbox_router.main(argv)
    debug_print(f"inbox_router exited with code {rc}")


def menu_validate_pack():
    debug_print("Selected: Validate pack")
    path = ask("Pack file path")
    if not path:
        debug_print("No file specified; aborting.")
        return
    project_root = ask("Project root (blank to skip)", os.getcwd())
    argv = ["--file", path]
    if project_root:
        argv.extend(["--project-root", project_root])
    rc = validate_sots_pack.main(argv)
    debug_print(f"validate_sots_pack exited with code {rc}")


def menu_lint_packs():
    debug_print("Selected: Lint inbox packs")
    inbox_dir = ask("Inbox directory", "chatgpt_inbox")
    project_root = ask("Project root (blank to skip)", os.getcwd())
    argv = ["--inbox-dir", inbox_dir]
    if project_root:
        argv.extend(["--project-root", project_root])
    rc = pack_linter.main(argv)
    debug_print(f"pack_linter exited with code {rc}")


def menu_generate_template():
    debug_print("Selected: Generate pack template")
    print("Templates: tag_audit, omnitrace_sweep, kem_execution_audit")
    template = ask("Template name", "tag_audit")
    output_dir = ask("Output directory", "chatgpt_inbox")
    argv = ["--template", template, "--output-dir", output_dir]
    rc = pack_template_generator.main(argv)
    debug_print(f"pack_template_generator exited with code {rc}")


def menu_status_dashboard():
    debug_print("Selected: DevTools status dashboard/update")
    mode = ask("Mode (dashboard/update)", "dashboard").lower()
    if mode == "update":
        plugin = ask("Plugin name")
        step = ask("Step ID (e.g. V2_11)")
        status = ask("Status (todo/in_progress/done)", "done")
        argv = [
            "--mode",
            "update",
            "--plugin",
            plugin,
            "--step",
            step,
            "--status",
            status,
        ]
    else:
        argv = ["--mode", "dashboard"]
    rc = devtools_status_dashboard.main(argv)
    debug_print(f"devtools_status_dashboard exited with code {rc}")


def menu_export_bundle():
    debug_print("Selected: Export report bundle")
    category = ask("Category substring")
    if not category:
        debug_print("No category specified; aborting.")
        return
    default_sources = f"{os.path.join('DevTools','logs')} {os.path.join('DevTools','reports')}"
    src_raw = ask("Source dirs (space-separated)", default_sources)
    sources = src_raw.split()
    output_dir = ask("Output directory", os.path.join("DevTools", "exports"))
    max_lines = ask("Max lines per file", "400")
    try:
        max_lines_int = int(max_lines)
    except ValueError:
        debug_print(f"Invalid max_lines '{max_lines}', using 400.")
        max_lines_int = 400
    argv = ["--category", category, "--output-dir", output_dir, "--max-lines", str(max_lines_int)]
    if sources:
        argv.extend(["--sources", *sources])
    rc = report_bundle_exporter.main(argv)
    debug_print(f"report_bundle_exporter exited with code {rc}")


def menu_log_error_digest():
    debug_print("Selected: Log error digest")
    logs_dir = ask("Logs directory", os.path.join("Saved", "Logs"))
    limit = ask("How many recent log files?", "10")
    top = ask("How many top messages?", "10")
    argv = ["--logs-dir", logs_dir]
    try:
        argv.extend(["--limit", str(int(limit))])
    except ValueError:
        debug_print(f"Invalid limit '{limit}', using default.")
    try:
        argv.extend(["--top", str(int(top))])
    except ValueError:
        debug_print(f"Invalid top '{top}', using default.")
    rc = log_error_digest.main(argv)
    debug_print(f"log_error_digest exited with code {rc}")


def menu_selftest():
    debug_print("Selected: DevTools selftest (health check)")
    mode = ask("Mode (compile/import)", "compile").lower()
    if mode not in ("compile", "import"):
        debug_print(f"Invalid mode '{mode}', defaulting to 'compile'.")
        mode = "compile"
    recursive_ans = ask("Scan subfolders recursively? (y/n)", "n").lower()
    recursive = recursive_ans.startswith("y")
    argv = ["--mode", mode]
    if recursive:
        argv.append("--recursive")
    rc = devtools_selftest.main(argv)
    debug_print(f"devtools_selftest exited with code {rc}")


def main(argv=None):
    debug_print("SOTS Pipeline Hub starting.")
    while True:
        print("")
        print("=== SOTS DevTools Pipeline Hub ===")
        print("  1) Route inbox ([SOTS_DEVTOOLS] files)")
        print("  2) Validate a single pack")
        print("  3) Lint all packs in inbox")
        print("  4) Generate a pack template")
        print("  5) DevTools status dashboard / update")
        print("  6) Export a report bundle")
        print("  7) Run log error digest")
        print("  8) Run DevTools selftest (health check)")
        print("  0) Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            menu_route_inbox()
        elif choice == "2":
            menu_validate_pack()
        elif choice == "3":
            menu_lint_packs()
        elif choice == "4":
            menu_generate_template()
        elif choice == "5":
            menu_status_dashboard()
        elif choice == "6":
            menu_export_bundle()
        elif choice == "7":
            menu_log_error_digest()
        elif choice == "8":
            menu_selftest()
        elif choice == "0":
            debug_print("Exiting SOTS Pipeline Hub.")
            break
        else:
            print("Invalid choice. Try again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
