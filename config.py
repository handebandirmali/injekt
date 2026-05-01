<<<<<<< HEAD
from pathlib import Path
from ids_peak_ipl import ids_peak_ipl

BASE_DIR = Path(r"C:\Users\Hande\Desktop\inkjet")
RUNTIME_DIR = BASE_DIR / "runtime"
FRAMES_DIR = RUNTIME_DIR / "frames"
STATUS_FILE_PATH = RUNTIME_DIR / "status.json"
LOG_FILE_PATH = BASE_DIR / "log.txt"
CSV_FILE_PATH = BASE_DIR / "denetim_kayitlari.csv"
MODEL_PATH = BASE_DIR / "train4_best.pt"
SETTINGS_FILE_PATH = BASE_DIR / "camera_settings.json"
REJECT_SETTINGS_FILE_PATH = BASE_DIR / "reject_settings.json"
MANUAL_CAMERAS_FILE_PATH = BASE_DIR / "manual_cameras.json"
WORKER_PID_FILE_PATH = RUNTIME_DIR / "worker.pid"

TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8
MAX_UI_LOGS = 30
FRAME_SAVE_INTERVAL_SEC = 0.35
STATUS_WRITE_INTERVAL_SEC = 0.50
SETTINGS_REFRESH_INTERVAL_SEC = 1.00
=======
from ids_peak_ipl import ids_peak_ipl

CSV_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"
MODEL_PATH = r"C:\Users\Hande\Desktop\inkjet\train4_best.pt"
SETTINGS_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\camera_settings.json"
REJECT_SETTINGS_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\reject_settings.json"

TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8
MAX_UI_LOGS = 30
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d

DEFAULT_IMAGE_SETTINGS = {
    "br": 0,
    "ct": 1.0,
    "sh": 0.0,
    "r_m": 1.0,
    "g_m": 1.0,
<<<<<<< HEAD
    "b_m": 1.0,
}

DEFAULT_REJECT_SETTINGS = {
    "gecikme_suresi": 1.20,
=======
    "b_m": 1.0
}

DEFAULT_REJECT_SETTINGS = {
    "gecikme_suresi": 1.20
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
}

DEFAULT_IDS_CAMERA = {
    "type": "ids",
    "name": "IDS Kamera",
    "index": 0,
    "ip": "IDS / Yerel Bağlantı",
<<<<<<< HEAD
    "manual": False,
=======
    "manual": False
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
}

EXTRA_IP_CAMERAS = [
    {
        "type": "ip",
        "name": "IP Kamera",
        "url": "rtsp://192.168.8.115:554/live/0",
        "ip": "192.168.8.115",
<<<<<<< HEAD
        "manual": False,
=======
        "manual": False
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
    },
    {
        "type": "ip",
        "name": "IP Kamera",
        "url": "rtsp://192.168.8.164:554/live/0",
        "ip": "192.168.8.164",
<<<<<<< HEAD
        "manual": False,
    },
]


def ensure_runtime_dirs() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
=======
        "manual": False
    }
]
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
