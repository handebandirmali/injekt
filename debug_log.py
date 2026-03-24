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