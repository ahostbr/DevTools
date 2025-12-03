#!/usr/bin/env python3
"""
run_bpgen_build.py
------------------

Manual DevTools helper for running SOTS_BPGenBuildCommandlet
against a single BPGen Job (and optional GraphSpec).

This script is:
- 100% MANUAL (no watchers, no auto scanning).
- Focused on ONE job per run.
- Responsible for:
    - Resolving JobFile and optional GraphSpecFile.
    - Building the UnrealEditor-Cmd.exe invocation.
    - Optionally executing it.
    - Printing a clear summary.
    - Writing a small log in DevTools/python/logs/.

Usage examples
--------------

1) Dry-run (print command only):

    cd DevTools/python

    python run_bpgen_build.py \
        --job-id BPGEN_MyHUD \
        --use-graph-spec \
        --dry-run

2) Run for a specific job with explicit paths:

    python run_bpgen_build.py \
        --job-id BPGEN_MyHUD \
        --use-graph-spec \
        --ue-cmd "E:/UE5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
        --uproject "E:/SAS/ShadowsAndShurikens/ShadowsAndShurikens.uproject"

3) Using env vars as defaults:

    set SOTS_BPGEN_UE_CMD=E:/UE5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
    set SOTS_BPGEN_UPROJECT=E:/SAS/ShadowsAndShurikens/ShadowsAndShurikens.uproject

    python run_bpgen_build.py --job-id BPGEN_MyHUD --use-graph-spec

Notes
-----
- If both --job-file and --job-id are provided, this script fails fast.
- If Unreal paths are missing and you are NOT in --dry-run mode,
  the script will refuse to execute and explain what you need to pass.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def detect_devtools_root() -> Path:
    """
    Detect DevTools/python root based on this script location.

    Assumes layout:
        DevTools/
            python/
                run_bpgen_build.py   <-- here
                bpgen_jobs/
                bpgen_specs/
                logs/
    """
    return Path(__file__).resolve().parent


def ensure_bpgen_dirs(root: Path) -> Tuple[Path, Path, Path]:
    """
    Ensure bpgen_jobs/, bpgen_specs/, and logs/ exist.
    Returns (jobs_dir, specs_dir, logs_dir).
    """
    jobs_dir = root / "bpgen_jobs"
    specs_dir = root / "bpgen_specs"
    logs_dir = root / "logs"

    jobs_dir.mkdir(parents=True, exist_ok=True)
    specs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return jobs_dir, specs_dir, logs_dir


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def write_log(logs_dir: Path, prefix: str, payload: str) -> Path:
    """
    Write a small log file summarizing what happened.
    """
    log_path = logs_dir / f"{prefix}_{timestamp()}.log"
    try:
        with log_path.open("w", encoding="utf-8") as f:
            f.write(payload)
    except Exception as exc:
        # Don't crash DevTools if logging fails; just emit a warning.
        print(f"[WARN] Failed to write log file '{log_path}': {exc}", file=sys.stderr)
    return log_path


def build_command(
    ue_cmd: str,
    uproject: str,
    job_file: Path,
    graph_spec_file: Optional[Path] = None,
) -> str:
    """
    Build the UnrealEditor-Cmd invocation string.

    We return a single shell command string because:
    - On Windows, quoting paths in a single string is friendlier for copy/paste.
    - This script is strictly manual and not meant as a long-lived daemon.
    """
    parts = [
        f"\"{ue_cmd}\"",
        f"\"{uproject}\"",
        "-run=SOTS_BPGenBuildCommandlet",
        f"-JobFile=\"{str(job_file)}\"",
    ]
    if graph_spec_file is not None:
        parts.append(f"-GraphSpecFile=\"{str(graph_spec_file)}\"")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main command logic
# ---------------------------------------------------------------------------

def resolve_job_path(
    jobs_dir: Path,
    job_id: Optional[str],
    job_file: Optional[str],
) -> Tuple[Path, str]:
    """
    Determine the job file path and concrete job ID.
    """
    if job_id and job_file:
        raise ValueError("Provide either --job-id OR --job-file, not both.")

    if job_file:
        job_path = Path(job_file)
        if not job_path.is_absolute():
            job_path = jobs_dir / job_path
        concrete_job_id = job_path.stem
    elif job_id:
        job_path = jobs_dir / f"{job_id}.json"
        concrete_job_id = job_id
    else:
        raise ValueError("You must provide either --job-id or --job-file.")

    if not job_path.exists():
        raise FileNotFoundError(f"Job file does not exist: {job_path}")

    return job_path.resolve(), concrete_job_id


def resolve_graph_spec_from_job(job_path: Path) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Inspect the Job JSON for a GraphSpecFile/GraphSpecPath hint.

    Returns (path_or_None, field_used_or_None, warning_message_or_None).
    """
    try:
        with job_path.open("r", encoding="utf-8") as job_file:
            data = json.load(job_file)
    except Exception as exc:
        warning = f"[WARN] Failed to inspect job JSON for GraphSpecFile: {exc}"
        return None, None, warning

    for field_name in ("GraphSpecFile", "GraphSpecPath"):
        value = data.get(field_name)
        if isinstance(value, str) and value.strip():
            candidate = Path(value.strip())
            if not candidate.is_absolute():
                candidate = (job_path.parent / candidate)
            return candidate.resolve(), field_name, None

    return None, None, None


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Run SOTS_BPGenBuildCommandlet for a single BPGen job."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--job-id",
        type=str,
        help="BPGen Job ID (resolves to bpgen_jobs/<JobId>.json).",
    )
    group.add_argument(
        "--job-file",
        type=str,
        help="Path to a Job JSON file (absolute or relative to bpgen_jobs/).",
    )

    parser.add_argument(
        "--graph-spec-file",
        type=str,
        default=None,
        help="Path to a GraphSpec JSON file (absolute or relative to bpgen_specs/).",
    )
    parser.add_argument(
        "--use-graph-spec",
        action="store_true",
        help=(
            "If set and --graph-spec-file is not provided, attempts to use "
            "bpgen_specs/<JobId>_graph.json."
        ),
    )

    parser.add_argument(
        "--ue-cmd",
        type=str,
        default=None,
        help=(
            "Path to UnrealEditor-Cmd.exe. If omitted, falls back to "
            "SOTS_BPGEN_UE_CMD env var. If still missing and not in --dry-run "
            "mode, no command will be executed."
        ),
    )
    parser.add_argument(
        "--uproject",
        type=str,
        default=None,
        help=(
            "Path to your .uproject file. If omitted, falls back to "
            "SOTS_BPGEN_UPROJECT env var. If still missing and not in "
            "--dry-run mode, no command will be executed."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved command but do NOT execute it.",
    )

    args = parser.parse_args(argv)

    devtools_root = detect_devtools_root()
    jobs_dir, specs_dir, logs_dir = ensure_bpgen_dirs(devtools_root)

    log_lines = []
    log_lines.append("run_bpgen_build.py started")
    log_lines.append(f"DevTools root : {devtools_root}")
    log_lines.append(f"Jobs dir      : {jobs_dir}")
    log_lines.append(f"Specs dir     : {specs_dir}")
    log_lines.append("")

    # Resolve job + spec paths.
    try:
        job_path, concrete_job_id = resolve_job_path(
            jobs_dir=jobs_dir,
            job_id=args.job_id,
            job_file=args.job_file,
        )
    except Exception as exc:
        msg = f"[ERROR] {exc}"
        print(msg)
        log_lines.append(msg)
        log_path = write_log(logs_dir, "bpgen_run_error", "\n".join(log_lines))
        print(f"[INFO] Log written to: {log_path}")
        return 1

    job_graph_spec_path, job_graph_spec_field, job_graph_spec_warning = resolve_graph_spec_from_job(job_path)
    if job_graph_spec_warning:
        log_lines.append(job_graph_spec_warning)

    graph_spec_path: Optional[Path] = None
    graph_spec_source: Optional[str] = None

    if args.graph_spec_file:
        spec_arg_path = Path(args.graph_spec_file)
        if not spec_arg_path.is_absolute():
            spec_arg_path = specs_dir / spec_arg_path
        if not spec_arg_path.exists():
            msg = f"[ERROR] GraphSpecFile not found: {spec_arg_path}"
            print(msg)
            log_lines.append(msg)
            log_path = write_log(logs_dir, "bpgen_run_error", "\n".join(log_lines))
            print(f"[INFO] Log written to: {log_path}")
            return 1
        graph_spec_path = spec_arg_path.resolve()
        graph_spec_source = "command-line"
    elif job_graph_spec_path:
        if not job_graph_spec_path.exists():
            msg = f"[ERROR] Job-level GraphSpecFile not found: {job_graph_spec_path}"
            print(msg)
            log_lines.append(msg)
            log_path = write_log(logs_dir, "bpgen_run_error", "\n".join(log_lines))
            print(f"[INFO] Log written to: {log_path}")
            return 1
        graph_spec_path = job_graph_spec_path
        field_desc = job_graph_spec_field or "GraphSpecFile"
        graph_spec_source = f"job JSON field '{field_desc}'"
    elif args.use_graph_spec:
        candidate = specs_dir / f"{concrete_job_id}_graph.json"
        if candidate.exists():
            graph_spec_path = candidate.resolve()
            graph_spec_source = "bpgen_specs/<JobId>_graph.json"
        else:
            graph_spec_source = "(use_graph_spec requested but default file missing)"

    log_lines.append(f"JobId         : {concrete_job_id}")
    log_lines.append(f"Job file      : {job_path}")
    if args.graph_spec_file:
        log_lines.append(f"GraphSpec arg : {args.graph_spec_file}")
    else:
        log_lines.append("GraphSpec arg : (none)")

    if graph_spec_path is not None:
        log_lines.append(f"GraphSpecPath : {graph_spec_path} (source: {graph_spec_source})")
    else:
        if args.use_graph_spec:
            log_lines.append(
                "GraphSpecPath : (use_graph_spec requested but no default file found)"
            )
        else:
            log_lines.append("GraphSpecPath : (not used)")

    log_lines.append("")

    # Resolve Unreal paths.
    ue_cmd = args.ue_cmd or os.environ.get("SOTS_BPGEN_UE_CMD")
    uproject = args.uproject or os.environ.get("SOTS_BPGEN_UPROJECT")

    if not ue_cmd:
        log_lines.append("[WARN] UE cmd path not provided (no --ue-cmd and no SOTS_BPGEN_UE_CMD).")
    if not uproject:
        log_lines.append("[WARN] UProject path not provided (no --uproject and no SOTS_BPGEN_UPROJECT).")

    if not ue_cmd:
        # Use a placeholder for printing only.
        ue_cmd_for_print = "UnrealEditor-Cmd.exe"
    else:
        ue_cmd_for_print = ue_cmd

    if not uproject:
        # Use a placeholder for printing only.
        uproject_for_print = "PATH/TO/YourProject.uproject"
    else:
        uproject_for_print = uproject

    cmd_str = build_command(
        ue_cmd=ue_cmd_for_print,
        uproject=uproject_for_print,
        job_file=job_path,
        graph_spec_file=graph_spec_path,
    )

    log_lines.append("Resolved command (printable):")
    log_lines.append(f"  {cmd_str}")
    log_lines.append("")

    print("=== SOTS BPGen Command (run_bpgen_build.py) ===")
    print(cmd_str)
    print("")

    # Decide whether we can execute.
    can_execute = bool(ue_cmd and uproject)

    if args.dry_run:
        print("[INFO] Dry-run mode: NOT executing Unreal. Edit/Copy this command as needed.")
        log_lines.append("Execution    : Dry-run (no process spawned).")
        log_path = write_log(logs_dir, "bpgen_run", "\n".join(log_lines))
        print(f"[INFO] Log written to: {log_path}")
        return 0

    if not can_execute:
        print("[ERROR] Cannot execute command: missing real --ue-cmd and/or --uproject.")
        print("        Either:")
        print("          - Pass --ue-cmd and --uproject explicitly, OR")
        print("          - Set SOTS_BPGEN_UE_CMD and SOTS_BPGEN_UPROJECT env vars,")
        print("        then re-run this script.")
        log_lines.append("Execution    : Skipped (missing UE cmd and/or uproject).")
        log_path = write_log(logs_dir, "bpgen_run_error", "\n".join(log_lines))
        print(f"[INFO] Log written to: {log_path}")
        return 1

    # Execute the command.
    print("[INFO] Executing Commandlet...")
    try:
        completed = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
        )
        exit_code = completed.returncode

        if completed.stdout:
            print(completed.stdout, end="")
            log_lines.append("Commandlet stdout:")
            log_lines.append(completed.stdout.rstrip())

        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
            log_lines.append("Commandlet stderr:")
            log_lines.append(completed.stderr.rstrip())

        log_lines.append(f"Execution    : Ran Commandlet, exit code {exit_code}")
        log_payload = "\n".join(log_lines)
        log_path = write_log(logs_dir, "bpgen_run", log_payload)

        print(f"[INFO] Commandlet exited with code {exit_code}")
        print(f"[INFO] Log written to: {log_path}")
        return exit_code
    except Exception as exc:
        msg = f"[ERROR] Failed to execute Commandlet: {exc}"
        print(msg)
        log_lines.append(msg)
        log_path = write_log(logs_dir, "bpgen_run_error", "\n".join(log_lines))
        print(f"[INFO] Log written to: {log_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
