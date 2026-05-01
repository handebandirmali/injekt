from __future__ import annotations
import json
import os
from copy import deepcopy
from typing import Dict, List

from typing import Dict, Union, Optional

from config import (
    DEFAULT_IMAGE_SETTINGS,
    DEFAULT_REJECT_SETTINGS,
    MANUAL_CAMERAS_FILE_PATH,
    REJECT_SETTINGS_FILE_PATH,
    SETTINGS_FILE_PATH,
    ensure_runtime_dirs,
)

ensure_runtime_dirs()


_CAMERA_SETTINGS_CACHE: Optional[Dict[str, Dict]] = None
_REJECT_SETTINGS_CACHE: Dict | None = None
_MANUAL_CAMERAS_CACHE: List[Dict] | None = None


def _read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(default, dict) and isinstance(data, dict):
                    return data
                if isinstance(default, list) and isinstance(data, list):
                    return data
    except Exception:
        pass
    return deepcopy(default)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================= CAMERA IMAGE SETTINGS =================
def load_camera_settings_from_disk() -> Dict[str, Dict]:
    raw = _read_json(SETTINGS_FILE_PATH, {})
    normalized = {}
    for cam_key, settings in raw.items():
        normalized[cam_key] = {
            "br": int(settings.get("br", 0)),
            "ct": float(settings.get("ct", 1.0)),
            "sh": float(settings.get("sh", 0.0)),
            "r_m": float(settings.get("r_m", 1.0)),
            "g_m": float(settings.get("g_m", 1.0)),
            "b_m": float(settings.get("b_m", 1.0)),
        }
    return normalized


def get_default_image_settings() -> Dict:
    return deepcopy(DEFAULT_IMAGE_SETTINGS)


def get_all_camera_settings() -> Dict[str, Dict]:
    global _CAMERA_SETTINGS_CACHE
    if _CAMERA_SETTINGS_CACHE is None:
        _CAMERA_SETTINGS_CACHE = load_camera_settings_from_disk()
    return _CAMERA_SETTINGS_CACHE


def save_camera_settings_to_disk() -> None:
    _write_json(SETTINGS_FILE_PATH, get_all_camera_settings())


def reload_camera_settings() -> Dict[str, Dict]:
    global _CAMERA_SETTINGS_CACHE
    _CAMERA_SETTINGS_CACHE = load_camera_settings_from_disk()
    return _CAMERA_SETTINGS_CACHE


def get_camera_settings(cam_key: str, reload_from_disk: bool = False) -> Dict:
    all_settings = reload_camera_settings() if reload_from_disk else get_all_camera_settings()
    if cam_key not in all_settings:
        all_settings[cam_key] = get_default_image_settings()
        save_camera_settings_to_disk()
    return deepcopy(all_settings[cam_key])


def set_camera_settings(cam_key: str, settings_dict: Dict) -> None:
    all_settings = get_all_camera_settings()
    all_settings[cam_key] = {
        "br": int(settings_dict.get("br", 0)),
        "ct": float(settings_dict.get("ct", 1.0)),
        "sh": float(settings_dict.get("sh", 0.0)),
        "r_m": float(settings_dict.get("r_m", 1.0)),
        "g_m": float(settings_dict.get("g_m", 1.0)),
        "b_m": float(settings_dict.get("b_m", 1.0)),
    }
    save_camera_settings_to_disk()


def reset_camera_settings(cam_key: str) -> None:
    get_all_camera_settings()[cam_key] = get_default_image_settings()
    save_camera_settings_to_disk()


# ================= REJECT TIMER SETTINGS =================
def get_default_reject_settings() -> Dict:
    return {"gecikme_suresi": float(DEFAULT_REJECT_SETTINGS.get("gecikme_suresi", 1.20))}


def load_reject_settings_from_disk() -> Dict:
    data = _read_json(REJECT_SETTINGS_FILE_PATH, get_default_reject_settings())
    if "gecikme_suresi" in data:
        return {"gecikme_suresi": float(data.get("gecikme_suresi", 1.20))}
    if "delay_seconds" in data:
        return {"gecikme_suresi": float(data.get("delay_seconds", 1.20))}
    return get_default_reject_settings()


def reload_reject_settings() -> Dict:
    global _REJECT_SETTINGS_CACHE
    _REJECT_SETTINGS_CACHE = load_reject_settings_from_disk()
    return deepcopy(_REJECT_SETTINGS_CACHE)


def get_reject_settings(reload_from_disk: bool = False) -> Dict:
    global _REJECT_SETTINGS_CACHE
    if _REJECT_SETTINGS_CACHE is None or reload_from_disk:
        _REJECT_SETTINGS_CACHE = load_reject_settings_from_disk()
    return deepcopy(_REJECT_SETTINGS_CACHE)


def save_reject_settings_to_disk() -> None:
    global _REJECT_SETTINGS_CACHE
    if _REJECT_SETTINGS_CACHE is None:
        _REJECT_SETTINGS_CACHE = get_default_reject_settings()
    _write_json(REJECT_SETTINGS_FILE_PATH, _REJECT_SETTINGS_CACHE)


def set_reject_settings(gecikme_suresi: float) -> None:
    global _REJECT_SETTINGS_CACHE
    _REJECT_SETTINGS_CACHE = {"gecikme_suresi": float(gecikme_suresi)}
    save_reject_settings_to_disk()


def reset_reject_settings() -> None:
    global _REJECT_SETTINGS_CACHE
    _REJECT_SETTINGS_CACHE = get_default_reject_settings()
    save_reject_settings_to_disk()


# ================= MANUAL CAMERAS =================
def load_manual_cameras_from_disk() -> List[Dict]:
    return _read_json(MANUAL_CAMERAS_FILE_PATH, [])


def reload_manual_cameras() -> List[Dict]:
    global _MANUAL_CAMERAS_CACHE
    _MANUAL_CAMERAS_CACHE = load_manual_cameras_from_disk()
    return deepcopy(_MANUAL_CAMERAS_CACHE)


def get_manual_cameras(reload_from_disk: bool = False) -> List[Dict]:
    global _MANUAL_CAMERAS_CACHE
    if _MANUAL_CAMERAS_CACHE is None or reload_from_disk:
        _MANUAL_CAMERAS_CACHE = load_manual_cameras_from_disk()
    return deepcopy(_MANUAL_CAMERAS_CACHE)


def save_manual_cameras(cameras: List[Dict]) -> None:
    global _MANUAL_CAMERAS_CACHE
    _MANUAL_CAMERAS_CACHE = deepcopy(cameras)
    _write_json(MANUAL_CAMERAS_FILE_PATH, _MANUAL_CAMERAS_CACHE)
