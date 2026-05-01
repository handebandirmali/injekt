<<<<<<< HEAD
import csv
import datetime
import os
from pathlib import Path
from typing import List

from config import CSV_FILE_PATH, LOG_FILE_PATH, MAX_UI_LOGS, ensure_runtime_dirs

ensure_runtime_dirs()


def log_to_system(msg: str, status: str = "INFO", save_csv: bool = False, show_ui: bool = True):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{status}] {msg}"

    try:
        Path(LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

    if save_csv:
        try:
            file_exists = os.path.isfile(CSV_FILE_PATH)
            with open(CSV_FILE_PATH, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Tarih_Saat", "Mesaj", "Durum"])
                writer.writerow([timestamp, msg, status])
        except Exception:
            pass

    if show_ui:
        try:
            import streamlit as st
            if "ui_logs" not in st.session_state:
                st.session_state.ui_logs = []
            st.session_state.ui_logs.append(line)
            if len(st.session_state.ui_logs) > MAX_UI_LOGS:
                st.session_state.ui_logs = st.session_state.ui_logs[-MAX_UI_LOGS:]
        except Exception:
            pass


def read_recent_logs(limit: int = 80) -> List[str]:
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f.readlines()]
        return lines[-limit:]
    except Exception:
        return []


# eski kullanım için

def log(msg: str):
    log_to_system(msg, status="INFO", save_csv=True, show_ui=True)
=======
import datetime
import csv
import os
import streamlit as st

log_file_path = r"C:\Users\Hande\Desktop\inkjet\log.txt"
csv_file_path = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"
MAX_UI_LOGS = 30


def log_to_system(msg, status="INFO", save_csv=False, show_ui=True):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # TXT LOG
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{status}] {msg}\n")
    except:
        pass

    # STREAMLIT LOG
    if show_ui:
        try:
            if "ui_logs" not in st.session_state:
                st.session_state.ui_logs = []

            st.session_state.ui_logs.append(f"[{timestamp}] [{status}] {msg}")

            if len(st.session_state.ui_logs) > MAX_UI_LOGS:
                st.session_state.ui_logs = st.session_state.ui_logs[-MAX_UI_LOGS:]
        except:
            pass

    # CSV LOG
    if save_csv:
        try:
            file_exists = os.path.isfile(csv_file_path)

            with open(csv_file_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if not file_exists:
                    writer.writerow(["Tarih_Saat", "Mesaj", "Durum"])

                writer.writerow([timestamp, msg, status])
        except:
            pass


# eski sistem için de çalışsın
def log(msg):
    log_to_system(msg, status="INFO", save_csv=True, show_ui=True)
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
