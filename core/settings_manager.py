import json
import os

import streamlit as st

from config import (
    SETTINGS_FILE_PATH,
    DEFAULT_IMAGE_SETTINGS,
    REJECT_SETTINGS_FILE_PATH,
    DEFAULT_REJECT_SETTINGS,
)


# ================= CAMERA IMAGE SETTINGS =================
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
    except Exception:
        pass

    return {}


def save_camera_settings_to_disk():
    try:
        with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state.camera_settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def ensure_camera_settings_loaded():
    if "camera_settings" not in st.session_state:
        st.session_state.camera_settings = {}

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


# ================= REJECT TIMER SETTINGS =================
def get_default_reject_settings():
    return {
        "gecikme_suresi": float(DEFAULT_REJECT_SETTINGS.get("gecikme_suresi", 1.20))
    }


def load_reject_settings_from_disk():
    if not os.path.exists(REJECT_SETTINGS_FILE_PATH):
        return get_default_reject_settings()

    try:
        with open(REJECT_SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Yeni yapı varsa direkt onu kullan
                if "gecikme_suresi" in data:
                    return {
                        "gecikme_suresi": float(
                            data.get("gecikme_suresi", get_default_reject_settings()["gecikme_suresi"])
                        )
                    }

                # Eski yapıdan otomatik geçiş
                if "delay_seconds" in data:
                    return {
                        "gecikme_suresi": float(
                            data.get("delay_seconds", get_default_reject_settings()["gecikme_suresi"])
                        )
                    }
    except Exception:
        pass

    return get_default_reject_settings()


def save_reject_settings_to_disk():
    try:
        with open(REJECT_SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state.reject_settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def ensure_reject_settings_loaded():
    if "reject_settings" not in st.session_state:
        st.session_state.reject_settings = load_reject_settings_from_disk()


def get_reject_settings():
    if "reject_settings" not in st.session_state:
        ensure_reject_settings_loaded()

    return {
        "gecikme_suresi": float(
            st.session_state.reject_settings.get(
                "gecikme_suresi",
                get_default_reject_settings()["gecikme_suresi"]
            )
        )
    }


def set_reject_settings(gecikme_suresi):
    st.session_state.reject_settings = {
        "gecikme_suresi": float(gecikme_suresi)
    }
    save_reject_settings_to_disk()


def reset_reject_settings():
    st.session_state.reject_settings = get_default_reject_settings()
    save_reject_settings_to_disk()