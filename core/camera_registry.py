<<<<<<< HEAD
=======
import streamlit as st
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
from ids_peak import ids_peak

from config import DEFAULT_IDS_CAMERA, EXTRA_IP_CAMERAS
from debug_log import log_to_system
<<<<<<< HEAD
from core.settings_manager import (
    get_all_camera_settings,
    get_manual_cameras,
    save_camera_settings_to_disk,
    save_manual_cameras,
)
=======
from core.settings_manager import save_camera_settings_to_disk
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d


def safe_camera_label(index, cam):
    return f"Hat {index + 1} - {cam['name']}"


def get_camera_key(cam):
    if cam["type"] == "ids":
        return f"ids_{cam.get('index', 0)}_{cam.get('name', 'cam')}"
    return f"ip_{cam.get('ip', 'unknown')}_{cam.get('name', 'cam')}"


def get_detected_ids_cameras():
    cameras = []
    try:
        ids_peak.Library.Initialize()
<<<<<<< HEAD
    except Exception:
=======
    except:
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
        pass

    try:
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        devices = device_manager.Devices()

        if not devices.empty():
            for i, d in enumerate(devices):
                try:
                    model = d.ModelName()
<<<<<<< HEAD
                except Exception:
=======
                except:
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
                    model = "IDS Kamera"

                try:
                    serial = d.SerialNumber()
<<<<<<< HEAD
                except Exception:
=======
                except:
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
                    serial = f"SERI-{i}"

                cameras.append({
                    "type": "ids",
                    "name": f"{model} ({serial})",
                    "index": i,
                    "ip": "IDS / Yerel Bağlantı",
<<<<<<< HEAD
                    "manual": False,
                })
    except Exception:
=======
                    "manual": False
                })
    except:
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
        pass

    return cameras


def get_all_cameras():
    detected_ids = get_detected_ids_cameras()
    all_sources = []

    if detected_ids:
        all_sources.extend(detected_ids)
    else:
        all_sources.append(DEFAULT_IDS_CAMERA.copy())

    for cam in EXTRA_IP_CAMERAS:
        all_sources.append(cam.copy())

<<<<<<< HEAD
    for cam in get_manual_cameras(reload_from_disk=True):
=======
    for cam in st.session_state.manual_cameras:
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
        all_sources.append(cam.copy())

    labeled_sources = []
    for i, cam in enumerate(all_sources):
        cam_copy = cam.copy()
        cam_copy["display_name"] = safe_camera_label(i, cam_copy)
        cam_copy["cam_key"] = get_camera_key(cam_copy)
        labeled_sources.append(cam_copy)

    return labeled_sources


def add_manual_camera(camera_type, custom_name, ip_address="", rtsp_path="", full_url=""):
    camera_type = camera_type.lower().strip()
    custom_name = custom_name.strip() if custom_name else ""
<<<<<<< HEAD
    cameras = get_manual_cameras(reload_from_disk=True)
=======
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d

    if not custom_name:
        custom_name = "Yeni Kamera"

    if camera_type == "ip":
        ip_address = ip_address.strip()
        rtsp_path = rtsp_path.strip()
        full_url = full_url.strip()

        if full_url:
            final_url = full_url
        else:
            if not ip_address:
                raise ValueError("IP kamera için IP adresi girmen lazım.")
            if not rtsp_path:
<<<<<<< HEAD
                raise ValueError("IP kamera için RTSP yolu girmen lazım. Örnek: /live/1")
=======
                raise ValueError("IP kamera için RTSP yolu girmen lazım. Örnek: /live/0")
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
            if not rtsp_path.startswith("/"):
                rtsp_path = "/" + rtsp_path
            final_url = f"rtsp://{ip_address}:554{rtsp_path}"

        camera = {
            "type": "ip",
            "name": custom_name,
            "url": final_url,
            "ip": ip_address if ip_address else final_url,
<<<<<<< HEAD
            "manual": True,
        }
=======
            "manual": True
        }

>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
    elif camera_type == "ids":
        camera = {
            "type": "ids",
            "name": custom_name,
            "index": 0,
            "ip": "IDS / Yerel Bağlantı",
<<<<<<< HEAD
            "manual": True,
=======
            "manual": True
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
        }
    else:
        raise ValueError("Geçersiz kamera tipi.")

<<<<<<< HEAD
    cameras.append(camera)
    save_manual_cameras(cameras)
=======
    st.session_state.manual_cameras.append(camera)
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
    log_to_system(
        f"Manuel kamera eklendi: {custom_name} ({camera_type.upper()})",
        "OK",
        save_csv=True,
<<<<<<< HEAD
        show_ui=True,
=======
        show_ui=True
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
    )


def remove_manual_camera(idx):
<<<<<<< HEAD
    cameras = get_manual_cameras(reload_from_disk=True)
    if 0 <= idx < len(cameras):
        removed = cameras.pop(idx)
        save_manual_cameras(cameras)

        removed_key = get_camera_key(removed)
        all_settings = get_all_camera_settings()
        if removed_key in all_settings:
            del all_settings[removed_key]
=======
    if 0 <= idx < len(st.session_state.manual_cameras):
        removed = st.session_state.manual_cameras.pop(idx)

        removed_key = get_camera_key(removed)
        if removed_key in st.session_state.camera_settings:
            del st.session_state.camera_settings[removed_key]
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
            save_camera_settings_to_disk()

        log_to_system(
            f"Manuel kamera silindi: {removed.get('name', 'Bilinmeyen')}",
            "UYARI",
            save_csv=True,
<<<<<<< HEAD
            show_ui=True,
        )
=======
            show_ui=True
        )
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
