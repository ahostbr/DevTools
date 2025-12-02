from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify


# ---------------------------------------------------------------------------
# Paths / dirs
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
PYTHON_ROOT = THIS_FILE.parent            # .../DevTools/python
DEVTOOLS_ROOT = PYTHON_ROOT.parent        # .../DevTools
PROJECT_ROOT = DEVTOOLS_ROOT.parent       # .../ShadowsAndShurikens

INBOX_DIR = PYTHON_ROOT / "chatgpt_inbox"
LOG_DIR = PYTHON_ROOT / "logs"
LOG_FILE = LOG_DIR / "sots_bridge_server.log"

INBOX_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def bridge_log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [SOTS_BRIDGE] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Logging must never kill the server
        pass


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def sanitize_label(label: str) -> str:
    safe = []
    for ch in label:
        if ch.isalnum() or ch in "-_":
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe) or "chatgpt_prompt"


def store_prompt_to_inbox(prompt: str, label: str, meta: dict) -> Path:
    """Write the prompt text to chatgpt_inbox as a timestamped .txt file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = sanitize_label(label)
    filename = f"{ts}_{safe_label}.txt"
    out_path = INBOX_DIR / filename

    header_lines = [
        "ChatGPT inbox file",
        f"Label: {label}",
        f"URL: {meta.get('url', '')}",
        f"Type: {meta.get('type', '')}",
        "",
    ]
    content = "\n".join(header_lines) + prompt
    if not content.endswith("\n"):
        content += "\n"

    out_path.write_text(content, encoding="utf-8")
    bridge_log(f"Stored prompt -> {out_path}")
    return out_path


def handle_open_file(devtools_path: str) -> tuple[dict, int]:
    """
    Handle action='open_file' from the userscript.

    devtools_path is expected to look like:
        DevTools/python/quick_search.py
    """
    if not devtools_path:
        bridge_log("open_file: missing devtools_path")
        return {"ok": False, "error": "missing devtools_path"}, 400

    norm = devtools_path.replace("\\", "/")
    if not norm.lower().startswith("devtools/"):
        bridge_log(f"open_file: rejecting non-DevTools path: {devtools_path}")
        return {
            "ok": False,
            "error": "devtools_path must start with 'DevTools/'",
        }, 400

    # Strip the leading "DevTools/" and resolve under DEVTOOLS_ROOT
    rel_part = norm.split("/", 1)[1] if "/" in norm else ""
    abs_path = DEVTOOLS_ROOT / rel_part
    exists = abs_path.exists()
    bridge_log(f"open_file: {devtools_path} -> {abs_path} (exists={exists})")

    if not exists:
        return {
            "ok": False,
            "error": f"file not found: {abs_path}",
            "path": str(abs_path),
        }, 404

    # Try to open with VS Code CLI (code / code.cmd). Non-blocking.
    launched = False
    err_msg = None
    for cmd in (["code", str(abs_path)], ["code.cmd", str(abs_path)]):
        try:
            subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
            launched = True
            break
        except FileNotFoundError:
            continue
        except Exception as exc:  # pragma: no cover - defensive
            err_msg = str(exc)
            break

    if launched:
        bridge_log(f"open_file: launched VS Code on {abs_path}")
        return {
            "ok": True,
            "launched": True,
            "path": str(abs_path),
        }, 200

    if err_msg:
        bridge_log(f"open_file: failed to launch editor: {err_msg}")

    # If we can't find 'code', still treat it as OK but report that we only logged.
    return {
        "ok": True,
        "launched": False,
        "path": str(abs_path),
        "note": "VS Code CLI not found; path logged only.",
    }, 200


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/sots/run_prompt", methods=["POST"])
def run_prompt() -> tuple:
    """
    Main entrypoint for ChatGPT → SOTS bridge.

    Supports:
      - Normal prompt files (last markdown, code blocks, etc.)
      - open_file style actions coming from DevTools labels
    """
    data = request.get_json(force=True, silent=True) or {}

    action = (data.get("action") or "").strip()
    label = (data.get("label") or "chatgpt_prompt").strip()
    meta = data.get("meta") or {}

    # devtools_path may live in meta or at the top level
    devtools_path = meta.get("devtools_path") or data.get("devtools_path", "")

    bridge_log(
        f"run_prompt: action={action!r}, label={label!r}, "
        f"has_devtools_path={bool(devtools_path)}"
    )

    # --- Any request that looks like an open-file intent ---
    if action == "open_file" or devtools_path:
        bridge_log(f"Received open_file-style request for {devtools_path!r}")
        payload, status = handle_open_file(devtools_path)
        return jsonify(payload), status

    # --- Normal prompt path (last message, code blocks, etc.) ---
    prompt = (data.get("prompt") or "").rstrip()
    if not prompt:
        bridge_log(f"Rejected request: empty prompt (action={action!r})")
        return jsonify({"ok": False, "error": "empty prompt"}), 400

    bridge_log(f"Received prompt (label={label}, len={len(prompt)})")

    out_path = store_prompt_to_inbox(prompt, label, meta)
    resp = {
        "ok": True,
        "file": str(out_path),
        "label": label,
    }
    return jsonify(resp), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    bridge_log("SOTS DevTools Flask bridge starting on http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)
