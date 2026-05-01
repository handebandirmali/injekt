import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
import cv2
from config import FRAMES_DIR, FRAME_SAVE_INTERVAL_SEC, STATUS_FILE_PATH, STATUS_WRITE_INTERVAL_SEC, WORKER_PID_FILE_PATH, ensure_runtime_dirs

ensure_runtime_dirs()

_LOCK = threading.Lock()
_RUNTIME_STATE: Dict[str, Any] = {
    "service": {
        "running": False,
        "started_at": None,
        "heartbeat": None,
        "pid": None,
        "version": "background-worker-v1",
    },
    "cameras": {},
}


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def set_service_running(running: bool, started_at: Optional[str] = None, pid: Optional[int] = None):
    with _LOCK:
        _RUNTIME_STATE["service"]["running"] = running
        _RUNTIME_STATE["service"]["heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if started_at is not None:
            _RUNTIME_STATE["service"]["started_at"] = started_at
        if pid is not None:
            _RUNTIME_STATE["service"]["pid"] = pid
        flush_runtime_state(force=True)


def update_service_heartbeat():
    with _LOCK:
        _RUNTIME_STATE["service"]["heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")


def update_camera_status(cam_key: str, data: Dict[str, Any], force: bool = False):
    with _LOCK:
        item = _RUNTIME_STATE["cameras"].setdefault(cam_key, {})
        item.update(data)
        item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if force:
            flush_runtime_state(force=True)


_LAST_FLUSH = 0.0


def flush_runtime_state(force: bool = False):
    global _LAST_FLUSH
    now = time.time()
    if not force and (now - _LAST_FLUSH) < STATUS_WRITE_INTERVAL_SEC:
        return
    _LAST_FLUSH = now
    ensure_runtime_dirs()
    _atomic_write_json(str(STATUS_FILE_PATH), _RUNTIME_STATE)
    pid = _RUNTIME_STATE.get("service", {}).get("pid")
    if pid:
        Path(WORKER_PID_FILE_PATH).write_text(str(pid), encoding="utf-8")


def mark_camera_offline(cam_key: str, source_info: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    payload = {
        "running": False,
        "fps": 0.0,
        "last_error": error,
    }
    if source_info:
        payload["source_info"] = source_info
        payload.setdefault("display_name", source_info.get("display_name"))
        payload.setdefault("ip", source_info.get("ip"))
        payload.setdefault("type", source_info.get("type"))
    update_camera_status(cam_key, payload, force=True)


_LAST_FRAME_SAVE: Dict[str, float] = {}


from typing import Optional

def save_camera_frame(cam_key: str, frame_rgb, display_name: Optional[str] = None) -> Optional[str]:
    now = time.time()
    last = _LAST_FRAME_SAVE.get(cam_key, 0.0)
    if (now - last) < FRAME_SAVE_INTERVAL_SEC:
        return None
    _LAST_FRAME_SAVE[cam_key] = now

    ensure_runtime_dirs()
    frame_path = FRAMES_DIR / f"{cam_key}.jpg"
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(frame_path), frame_bgr)
    if not ok:
        return None

    update_camera_status(
        cam_key,
        {
            "frame_path": str(frame_path),
            "display_name": display_name,
        },
        force=False,
    )
    return str(frame_path)


def load_runtime_state() -> Dict[str, Any]:
    try:
        with open(STATUS_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"service": {"running": False}, "cameras": {}}
