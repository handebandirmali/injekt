import json
import os

import streamlit as st

from config import SETTINGS_FILE_PATH, DEFAULT_IMAGE_SETTINGS


def load_camera_settings_from_disk():
    if not os.path.exists(SETTINGS_FILE_PATH):
        return {}

    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                normalized = {}
                for cam_key, settings in data.items():
                    normalized[cam_key] = {
                        "br": int(settings.get("br", 0)),
                        "ct": float(settings.get("ct", 1.0)),
                        "sh": float(settings.get("sh", 0.0)),
                        "r_m": float(settings.get("r_m", 1.0)),
                        "g_m": float(settings.get("g_m", 1.0)),
                        "b_m": float(settings.get("b_m", 1.0)),
                    }
                return normalized
    except:
        pass

    return {}


def save_camera_settings_to_disk():
    try:
        with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state.camera_settings, f, ensure_ascii=False, indent=2)
    except:
        pass


def ensure_camera_settings_loaded():
    if not st.session_state.camera_settings:
        st.session_state.camera_settings = load_camera_settings_from_disk()


def get_default_image_settings():
    return DEFAULT_IMAGE_SETTINGS.copy()


def get_camera_settings(cam_key):
    all_settings = st.session_state.camera_settings
    if cam_key not in all_settings:
        all_settings[cam_key] = get_default_image_settings()
        save_camera_settings_to_disk()
    return all_settings[cam_key]


def set_camera_settings(cam_key, settings_dict):
    st.session_state.camera_settings[cam_key] = {
        "br": int(settings_dict.get("br", 0)),
        "ct": float(settings_dict.get("ct", 1.0)),
        "sh": float(settings_dict.get("sh", 0.0)),
        "r_m": float(settings_dict.get("r_m", 1.0)),
        "g_m": float(settings_dict.get("g_m", 1.0)),
        "b_m": float(settings_dict.get("b_m", 1.0))
    }
    save_camera_settings_to_disk()


def reset_camera_settings(cam_key):
    st.session_state.camera_settings[cam_key] = get_default_image_settings()
    save_camera_settings_to_disk()