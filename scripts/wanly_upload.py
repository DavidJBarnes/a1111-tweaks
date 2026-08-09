"""Shared helpers for uploading images to the wanly API.

Imported by ``upload_to_wanly.py`` and ``gallery.py``. This module is not a
``scripts.Script`` subclass -- A1111 still loads it as a script file, so it must
not register callbacks or start threads at import time.
"""

import collections
import io
import json
import os
import queue
import threading

import requests
from PIL import Image
from modules import scripts, shared

LOG_PREFIX = "[Wanly Upload]"
CONFIG_FILENAME = "upload_to_wanly_config.json"
API_URL = "http://api.wanly22.com:8001"
DEFAULT_CONFIG = {"api_key": "", "auto_upload": False}

MAX_QUEUE_SIZE = 200
MAX_CONSECUTIVE_FAILURES = 5
SEEN_HISTORY = 500


def config_path():
    return os.path.join(scripts.basedir(), CONFIG_FILENAME)


def load_wanly_config():
    """Load wanly upload config from JSON, filling in defaults."""
    config = dict(DEFAULT_CONFIG)
    path = config_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"{LOG_PREFIX} Error loading config: {e}")
    return config


def save_wanly_config(config):
    """Write config back to JSON. Returns True on success."""
    config = {k: v for k, v in config.items() if k in DEFAULT_CONFIG}
    try:
        with open(config_path(), "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"{LOG_PREFIX} Error saving config: {e}")
        return False


def upload_image_to_wanly(image, filename, api_key=None):
    """Upload a PIL Image to the wanly API. Returns (success, message)."""
    if api_key is None:
        api_key = load_wanly_config().get("api_key", "")

    if not api_key:
        return False, "Error: API Key not set."

    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        resp = requests.post(
            f"{API_URL}/images/upload",
            params={"filename": filename},
            headers={"X-API-Key": api_key},
            files={"file": (filename, buf, "image/png")},
            timeout=60,
        )
        if resp.status_code == 200:
            path = resp.json().get("path", "")
            return True, f"Uploaded: {path}"
        else:
            return False, f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Error: {e}"


def is_grid_image(params):
    """True if an on_image_saved payload is a grid rather than a single image.

    Grids are saved last, so without this filter they would be picked up as the
    "last image" and auto-uploaded alongside the images they contain. Falls back
    to False (treat as a real image) whenever detection is uncertain.
    """
    try:
        filename = getattr(params, "filename", "") or ""
        if os.path.basename(filename).startswith("grid-"):
            return True

        dirname = os.path.abspath(os.path.dirname(filename))
        p = getattr(params, "p", None)

        # If it landed in the samples dir it is not a grid, even when the user
        # has pointed both outputs at the same folder.
        samples_dir = getattr(p, "outpath_samples", None) if p is not None else None
        if samples_dir and os.path.abspath(samples_dir) == dirname:
            return False

        candidates = []
        if p is not None and getattr(p, "outpath_grids", None):
            candidates.append(p.outpath_grids)
        for key in ("outdir_grids", "outdir_txt2img_grids", "outdir_img2img_grids"):
            value = getattr(shared.opts, key, None)
            if value:
                candidates.append(value)

        return any(os.path.abspath(c) == dirname for c in candidates)
    except Exception:
        return False


# --- Background auto-upload worker -----------------------------------------
#
# on_image_saved runs on the generation thread, so uploading inline would stall
# the next "generate forever" iteration for the length of the HTTP request. File
# paths (not PIL images) are queued so a long run does not accumulate decoded
# images in memory -- the file is already on disk when the callback fires.

_upload_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
_worker_thread = None
_worker_lock = threading.Lock()

_seen = collections.OrderedDict()
_seen_lock = threading.Lock()

_stats_lock = threading.Lock()
_stats = {"uploaded": 0, "failed": 0, "last": "", "paused_reason": None}

# Only touched by the worker thread.
_consecutive_failures = 0


def auto_upload_status():
    """Human-readable summary of the background uploader."""
    with _stats_lock:
        stats = dict(_stats)
    lines = [
        f"Uploaded: {stats['uploaded']}   Failed: {stats['failed']}   "
        f"Pending: {_upload_queue.qsize()}"
    ]
    if stats["paused_reason"]:
        lines.append(f"PAUSED - {stats['paused_reason']}")
    if stats["last"]:
        lines.append(stats["last"])
    return "\n".join(lines)


def reset_auto_upload():
    """Clear the paused state so queuing resumes. Keeps the running totals."""
    global _consecutive_failures
    _consecutive_failures = 0
    with _stats_lock:
        _stats["paused_reason"] = None
        _stats["last"] = ""


def queue_auto_upload(path):
    """Queue a saved image path for background upload. Returns True if queued."""
    if not path:
        return False

    with _stats_lock:
        if _stats["paused_reason"]:
            return False

    with _seen_lock:
        if path in _seen:
            return False
        _seen[path] = True
        while len(_seen) > SEEN_HISTORY:
            _seen.popitem(last=False)

    _start_worker()

    try:
        _upload_queue.put_nowait(path)
    except queue.Full:
        with _seen_lock:
            _seen.pop(path, None)
        with _stats_lock:
            _stats["last"] = "Upload queue full - image skipped."
        print(f"{LOG_PREFIX} Queue full, skipped {os.path.basename(path)}")
        return False

    return True


def _start_worker():
    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(
            target=_worker_loop, name="wanly-auto-upload", daemon=True
        )
        _worker_thread.start()


def _worker_loop():
    global _consecutive_failures
    while True:
        path = _upload_queue.get()
        try:
            success, message = _upload_path(path)
            with _stats_lock:
                _stats["last"] = f"{os.path.basename(path)}: {message}"
                if success:
                    _stats["uploaded"] += 1
                else:
                    _stats["failed"] += 1

            if success:
                _consecutive_failures = 0
            else:
                _consecutive_failures += 1
                print(f"{LOG_PREFIX} {os.path.basename(path)}: {message}")
                if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    _pause(
                        f"{MAX_CONSECUTIVE_FAILURES} uploads failed in a row. "
                        "Check the API settings, then re-enable auto-upload."
                    )
        except Exception as e:
            print(f"{LOG_PREFIX} Unexpected error uploading {path}: {e}")
        finally:
            _upload_queue.task_done()


def _upload_path(path):
    if not os.path.exists(path):
        return False, "File no longer exists."
    try:
        with Image.open(path) as img:
            img.load()
            return upload_image_to_wanly(img, os.path.basename(path))
    except Exception as e:
        return False, f"Error: {e}"


def _pause(reason):
    """Stop auto-uploading and drop anything still queued."""
    with _stats_lock:
        _stats["paused_reason"] = reason
    while True:
        try:
            _upload_queue.get_nowait()
        except queue.Empty:
            break
        else:
            _upload_queue.task_done()
    print(f"{LOG_PREFIX} Auto-upload paused: {reason}")
