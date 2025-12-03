# SOTS DevTools - sots_chatgpt_dispatcher.py (tuned)
# - Defaults to MANUAL when no 'mode:' header is present (no auto-dispatch).
# - Logs tool/category/plugin/pass/mode for each dispatch.
# - Adds support for 'patch_from_block' and 'run_devtool' tools.
# - Adds conservative fallback for chatgpt_code_block* prompts -> patch_outbox.
#
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "chatgpt_dispatcher.log"


def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [DISPATCHER] {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

def parse_header(prompt_path: Path) -> dict[str, str]:
    """
    Parse the [SOTS_DEVTOOLS] header block from the prompt file.
    Returns a dict of key -> value. If no header, returns {}.
    """
    text = prompt_path.read_text(encoding="utf-8", errors="replace")
    start_tag = "[SOTS_DEVTOOLS]"
    end_tag = "[/SOTS_DEVTOOLS]"

    start_idx = text.find(start_tag)
    end_idx = text.find(end_tag)

    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        log("No SOTS_DEVTOOLS header found.")
        return {}

    header_text = text[start_idx + len(start_tag):end_idx]
    config: dict[str, str] = {}

    for raw_line in header_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Allow "key: value" or "key=value"
        if ":" in line:
            key, value = line.split(":", 1)
        elif "=" in line:
            key, value = line.split("=", 1)
        else:
            log(f"Skipping malformed header line: {line!r}")
            continue
        config[key.strip().lower()] = value.strip()

    if not config:
        log("Header block was present but contained no key/value pairs.")
    else:
        log(f"Parsed header keys: {sorted(config.keys())}")

    return config


def str_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    return default


def should_auto_dispatch(config: dict[str, str]) -> bool:
    """Decide whether to auto-dispatch based on the header.

    Law 6.5 / DevTools convention:
    - If mode is explicitly 'auto' (or close variants), we allow auto-dispatch.
    - If mode is 'manual' (or explicit manual variants), we do NOT auto-dispatch.
    - If mode is missing or anything else, we treat it as MANUAL by default.
    """
    mode = config.get("mode", "").strip().lower()
    if mode in {"auto", "auto_run", "auto-run"}:
        return True
    if mode in {"manual", "manual_only", "manual-run"}:
        return False
    # Default: manual (no auto-dispatch)
    return False


# ---------------------------------------------------------------------------
# Tool runners
# ---------------------------------------------------------------------------

def run_write_files(config: dict[str, str], prompt_path: Path) -> None:
    """Dispatch to write_files.py using the full prompt file as --source.

    Expected header shape:

        [SOTS_DEVTOOLS]
        tool: write_files
        mode: ...
        [/SOTS_DEVTOOLS]

    The write_files.py script will:
      - Parse the body for FILE: ... / === END FILE === blocks
      - Write those files under PROJECT_ROOT
      - Log a summary in DevTools/python/logs/write_files_*.log
    """
    script = ROOT / "write_files.py"
    if not script.is_file():
        log(f"write_files.py not found at {script}")
        return

    cmd = [sys.executable, str(script), "--source", str(prompt_path)]
    log(f"Launching write_files: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running write_files: {e}")


def run_quick_search(config: dict[str, str]) -> None:
    """
    Dispatch to quick_search.py with a simple 'pattern' and optional 'paths'.
    """
    script = ROOT / "quick_search.py"
    if not script.is_file():
        log(f"quick_search.py not found at {script}")
        return

    pattern = config.get("pattern")
    if not pattern:
        log("quick_search requested but 'pattern' is missing.")
        return

    paths = config.get("paths", "").strip()
    cmd = [sys.executable, str(script), "--pattern", pattern]
    if paths:
        cmd += ["--paths", paths]

    log(f"Launching quick_search: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running quick_search: {e}")


def run_regex_replace(config: dict[str, str]) -> None:
    """
    Dispatch to mass_regex_edit.py with a single pattern + replacement.
    """
    script = ROOT / "mass_regex_edit.py"
    if not script.is_file():
        log(f"mass_regex_edit.py not found at {script}")
        return

    pattern = config.get("pattern")
    replacement = config.get("replacement", "")
    paths = config.get("paths", "").strip()

    if not pattern:
        log("regex_replace requested but 'pattern' is missing.")
        return
    if not paths:
        log("regex_replace requested but 'paths' is missing.")
        return

    cmd = [
        sys.executable,
        str(script),
        "--pattern", pattern,
        "--replacement", replacement,
        "--paths", paths,
    ]

    log(f"Launching regex_replace via mass_regex_edit: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running regex_replace: {e}")


def split_paths(value: str) -> list[str]:
    # Split on ; or , and trim
    parts = re.split(r"[;,]", value)
    return [p.strip() for p in parts if p.strip()]


def run_delete_paths(config: dict[str, str]) -> None:
    """
    Dispatch to delete_paths.py with list of paths and dry_run.
    """
    paths_str = config.get("paths")
    if not paths_str:
        log("delete_paths requested but 'paths' is missing.")
        return

    paths = split_paths(paths_str)
    if not paths:
        log("delete_paths: no valid paths after parsing.")
        return

    dry_run = str_to_bool(config.get("dry_run"), default=True)

    script = ROOT / "delete_paths.py"
    if not script.is_file():
        log(f"delete_paths.py not found at {script}")
        return

    cmd = [sys.executable, str(script)]
    for p in paths:
        cmd += ["--path", p]
    if dry_run:
        cmd.append("--dry_run")

    log(f"Launching delete_paths: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running delete_paths: {e}")


# ---------------------------------------------------------------------------
# Dispatch helpers (exported for sots_tools.py)
# ---------------------------------------------------------------------------
def run_patch_from_block_header(config: dict[str, str], prompt_path: Path) -> None:
    """Dispatch to patch_from_block.py using header fields.

    Expected header shape:

        [SOTS_DEVTOOLS]
        tool: patch_from_block
        mode: file | patch
        target: <informational target path>
        label: <short label, optional>
        [/SOTS_DEVTOOLS]

    This never applies patches directly. It only writes a payload file under
    DevTools/python/patch_outbox plus a small log entry.
    """
    mode = config.get("mode", "file").strip().lower() or "file"
    if mode not in {"file", "patch"}:
        log(f"patch_from_block: unexpected mode {mode!r}, falling back to 'file'.")
        mode = "file"

    target = config.get("target", "").strip() or "<unspecified-target>"
    label = config.get("label", "").strip() or "chatgpt_block"

    script = ROOT / "patch_from_block.py"
    if not script.is_file():
        log(f"patch_from_block.py not found at {script}")
        return

    cmd = [
        sys.executable,
        str(script),
        "--mode", mode,
        "--target", target,
        "--label", label,
        "--source", str(prompt_path),
    ]
    log(f"Launching patch_from_block (header): {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running patch_from_block (header): {e}")


def run_patch_from_block_fallback(prompt_path: Path) -> None:
    """Fallback helper when there is no header but the filename looks
    like a ChatGPT code-block export.

    We always run in FILE mode with a synthetic target and label so the
    payload is easy to find in patch_outbox.
    """
    script = ROOT / "patch_from_block.py"
    if not script.is_file():
        log(f"patch_from_block.py not found at {script}")
        return

    label = prompt_path.stem or "chatgpt_code_block"
    target = "<no-header-fallback>"

    cmd = [
        sys.executable,
        str(script),
        "--mode", "file",
        "--target", target,
        "--label", label,
        "--source", str(prompt_path),
    ]
    log(f"Launching patch_from_block (fallback): {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running patch_from_block (fallback): {e}")


def run_devtool(config: dict[str, str]) -> None:
    """Generic adapter over run_devtool.py.

    Expected header shape:

        [SOTS_DEVTOOLS]
        tool: run_devtool
        script: some_tool.py
        args: --foo bar --flag
        mode: manual | auto  # obeyed at dispatcher level
        [/SOTS_DEVTOOLS]

    This simply launches:

        python run_devtool.py --script <script> --args "<args>"

    leaving run_devtool.py to handle logging and process lifetime.
    """
    script_name = config.get("script", "").strip()
    if not script_name:
        log("run_devtool requested but 'script:' header is missing.")
        return

    args_str = config.get("args", "").strip()

    launcher = ROOT / "run_devtool.py"
    if not launcher.is_file():
        log(f"run_devtool.py not found at {launcher}")
        return

    cmd = [
        sys.executable,
        str(launcher),
        "--script", script_name,
    ]
    if args_str:
        cmd.extend(["--args", args_str])

    log(f"Launching run_devtool: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd, cwd=str(ROOT))
    except Exception as e:
        log(f"ERROR running run_devtool: {e}")


def _dispatch_config(config: dict[str, str], prompt_path: Path, *, force: bool) -> None:
    if not config:
        log("No config; nothing to dispatch.")
        return

    # Respect manual-vs-auto conventions unless force=True (manual CLI call).
    if not force and not should_auto_dispatch(config):
        log("Header mode implies manual; skipping auto-dispatch. Use sots_tools.py (Apply latest inbox) for a manual run.")
        return

    tool = config.get("tool", "").lower()
    log_parts = [
        f"tool={tool!r}",
        f"mode={config.get('mode', '').strip()!r}",
        f"category={config.get('category', '').strip()!r}",
        f"plugin={config.get('plugin', '').strip()!r}",
        f"pass={config.get('pass', '').strip()!r}",
        f"force={force}",
    ]
    log("Dispatching with header: " + ", ".join(log_parts))

    if tool == "write_files":
        run_write_files(config, prompt_path)
    elif tool == "quick_search":
        run_quick_search(config)
    elif tool == "regex_replace":
        run_regex_replace(config)
    elif tool == "delete_paths":
        run_delete_paths(config)
    elif tool == "patch_from_block":
        run_patch_from_block_header(config, prompt_path)
    elif tool == "run_devtool":
        run_devtool(config)
    else:
        log(f"Unknown or unsupported tool: {tool!r}")


def fallback_dispatch(prompt_path: Path) -> None:
    """Fallback when no [SOTS_DEVTOOLS] header is present.

    Today this is intentionally conservative:
    - If the file name suggests a raw code block export
      (contains 'chatgpt_code_block'), we feed it into patch_from_block.py
      in FILE mode so it lands in DevTools/python/patch_outbox.
    - Otherwise we just log and do nothing.
    """
    stem_lower = prompt_path.stem.lower()
    log(f"No header; fallback dispatch for {prompt_path.name}")

    if "chatgpt_code_block" in stem_lower:
        run_patch_from_block_fallback(prompt_path)
    else:
        log("No known fallback handler for this prompt file; doing nothing.")


def dispatch_file(prompt_path: Path, *, force: bool = False) -> None:
    """
    Public entrypoint for other scripts (bridge_runner, sots_tools).

    Behavior:
    - Reads the [SOTS_DEVTOOLS] header (if any) from prompt_path.
    - If there is a header, routes through _dispatch_config which respects
      mode=manual vs mode=auto unless force=True.
    - If there is *no* header, we fall back to conservative handling
      (currently patch_from_block for chatgpt_code_block files).
    """
    if not prompt_path.is_file():
        log(f"ERROR: Prompt file not found: {prompt_path}")
        return

    log(f"Processing prompt file: {prompt_path} (force={force})")
    config = parse_header(prompt_path)
    if not config:
        fallback_dispatch(prompt_path)
        return

    _dispatch_config(config, prompt_path, force=force)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SOTS ChatGPT DevTools dispatcher")
    parser.add_argument(
        "--prompt_file",
        type=Path,
        required=True,
        help="Path to the prompt .txt file from ChatGPT inbox",
    )
    args = parser.parse_args()

    dispatch_file(args.prompt_file, force=False)


if __name__ == "__main__":
    main()
