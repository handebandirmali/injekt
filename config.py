from ids_peak_ipl import ids_peak_ipl

CSV_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"
MODEL_PATH = r"C:\Users\Hande\Desktop\inkjet\train4_best.pt"
SETTINGS_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\camera_settings.json"
REJECT_SETTINGS_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\reject_settings.json"

TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8
MAX_UI_LOGS = 30

DEFAULT_IMAGE_SETTINGS = {
    "br": 0,
    "ct": 1.0,
    "sh": 0.0,
    "r_m": 1.0,
    "g_m": 1.0,
    "b_m": 1.0
}

DEFAULT_REJECT_SETTINGS = {
    "gecikme_suresi": 1.20
}

DEFAULT_IDS_CAMERA = {
    "type": "ids",
    "name": "IDS Kamera",
    "index": 0,
    "ip": "IDS / Yerel Bağlantı",
    "manual": False
}

EXTRA_IP_CAMERAS = [
    {
        "type": "ip",
        "name": "IP Kamera",
        "url": "rtsp://192.168.8.115:554/live/0",
        "ip": "192.168.8.115",
        "manual": False
    },
    {
        "type": "ip",
        "name": "IP Kamera",
        "url": "rtsp://192.168.8.164:554/live/0",
        "ip": "192.168.8.164",
        "manual": False
    }
]