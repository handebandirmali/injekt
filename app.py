import streamlit as st
import cv2
import time
import numpy as np
import threading
import os
import pandas as pd
import atexit
from datetime import datetime
from ids_peak import ids_peak, ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl
from inkjet_check_save import InkjetCheck

# ================== SESSION STATE BAŞLATMA ==================
if 'ct' not in st.session_state:
    st.session_state.ct = 1.0
if 'br' not in st.session_state:
    st.session_state.br = 0
if 'sh' not in st.session_state:
    st.session_state.sh = 0.0
if 'r_m' not in st.session_state:
    st.session_state.r_m = 1.0
if 'g_m' not in st.session_state:
    st.session_state.g_m = 1.0
if 'b_m' not in st.session_state:
    st.session_state.b_m = 1.0
if 'manual_cameras' not in st.session_state:
    st.session_state.manual_cameras = []
if 'grid_selected_cameras' not in st.session_state:
    st.session_state.grid_selected_cameras = []
if 'ui_logs' not in st.session_state:
    st.session_state.ui_logs = []
if 'streamers' not in st.session_state:
    st.session_state.streamers = {}

# ================== CONFIG & PATHS ==================
CSV_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"
MODEL_PATH = r"C:\Users\Hande\Desktop\inkjet\train4_best.pt"
TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8
MAX_UI_LOGS = 30

# ================== VARSAYILAN IDS ==================
DEFAULT_IDS_CAMERA = {
    "type": "ids",
    "name": "IDS Kamera",
    "index": 0,
    "ip": "IDS / Yerel Bağlantı",
    "manual": False
}

# ================== SABİT IP KAMERALAR ==================
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

# ================== YARDIMCI FONKSİYONLAR ==================
def log_to_system(msg, status="INFO", save_csv=False, show_ui=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{status}] {msg}"

    if show_ui:
        logs = st.session_state.ui_logs
        last_msg_only = logs[-1].split("] ", 2)[-1] if logs else None
        if not logs or last_msg_only != f"[{status}] {msg}":
            logs.append(line)
            if len(logs) > MAX_UI_LOGS:
                st.session_state.ui_logs = logs[-MAX_UI_LOGS:]

    if save_csv:
        try:
            file_exists = os.path.isfile(CSV_FILE_PATH)
            df_new = pd.DataFrame([[timestamp, msg, status]], columns=["Tarih_Saat", "Mesaj", "Durum"])
            df_new.to_csv(CSV_FILE_PATH, mode="a", index=False, header=not file_exists, encoding="utf-8-sig")
        except:
            pass


@st.cache_resource
def load_detector():
    return InkjetCheck(MODEL_PATH)


detector = load_detector()


def apply_sharpness(frame_bgr, sharpness_value):
    if abs(sharpness_value) < 0.01:
        return frame_bgr

    if sharpness_value > 0:
        kernel = np.array([
            [0, -1, 0],
            [-1, 5 + sharpness_value, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        return cv2.filter2D(frame_bgr, -1, kernel)
    else:
        k = int(min(max(abs(sharpness_value) * 2 + 1, 1), 9))
        if k % 2 == 0:
            k += 1
        return cv2.GaussianBlur(frame_bgr, (k, k), 0)


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
    except:
        pass

    try:
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        devices = device_manager.Devices()

        if not devices.empty():
            for i, d in enumerate(devices):
                try:
                    model = d.ModelName()
                except:
                    model = "IDS Kamera"

                try:
                    serial = d.SerialNumber()
                except:
                    serial = f"SERI-{i}"

                cameras.append({
                    "type": "ids",
                    "name": f"{model} ({serial})",
                    "index": i,
                    "ip": "IDS / Yerel Bağlantı",
                    "manual": False
                })
    except:
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

    for cam in st.session_state.manual_cameras:
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
                raise ValueError("IP kamera için RTSP yolu girmen lazım. Örnek: /live/0")
            if not rtsp_path.startswith("/"):
                rtsp_path = "/" + rtsp_path
            final_url = f"rtsp://{ip_address}:554{rtsp_path}"

        camera = {
            "type": "ip",
            "name": custom_name,
            "url": final_url,
            "ip": ip_address if ip_address else final_url,
            "manual": True
        }

    elif camera_type == "ids":
        camera = {
            "type": "ids",
            "name": custom_name,
            "index": 0,
            "ip": "IDS / Yerel Bağlantı",
            "manual": True
        }
    else:
        raise ValueError("Geçersiz kamera tipi.")

    st.session_state.manual_cameras.append(camera)
    log_to_system(f"Manuel kamera eklendi: {custom_name} ({camera_type.upper()})", "OK", save_csv=True, show_ui=True)


def remove_manual_camera(idx):
    if 0 <= idx < len(st.session_state.manual_cameras):
        removed = st.session_state.manual_cameras.pop(idx)
        log_to_system(f"Manuel kamera silindi: {removed.get('name', 'Bilinmeyen')}", "UYARI", save_csv=True, show_ui=True)


# ================== KAMERA SINIFI ==================
class CameraStreamer:
    def __init__(self):
        self.device = None
        self.datastream = None
        self.nodemap = None
        self.cap = None
        self.converter = ids_peak_ipl.ImageConverter()

        self.running = False
        self.latest_frame = None
        self.current_fps = 0.0
        self.ai_enabled = True
        self.lock = threading.Lock()
        self.source_info = None

        self.img_settings = {
            "br": 0,
            "ct": 1.0,
            "sh": 0.0,
            "r_m": 1.0,
            "g_m": 1.0,
            "b_m": 1.0
        }

        try:
            ids_peak.Library.Initialize()
        except:
            pass

    def start(self, source_info):
        if self.running:
            self.stop()

        self.source_info = source_info

        try:
            source_type = source_info.get("type")

            if source_type == "ids":
                return self._start_ids_camera(source_info.get("index", 0))
            elif source_type == "ip":
                return self._start_ip_camera(source_info["url"])
            else:
                return False
        except:
            self.stop()
            return False

    def _start_ids_camera(self, camera_index=0):
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        devices = device_manager.Devices()

        if devices.empty():
            raise Exception("IDS kamera bağlı değil veya sistem tarafından görülmüyor.")

        if camera_index >= len(devices):
            raise Exception(f"İstenen IDS kamera indexi bulunamadı: {camera_index}")

        self.device = devices[camera_index].OpenDevice(ids_peak.DeviceAccessType_Control)
        self.datastream = self.device.DataStreams()[0].OpenDataStream()
        self.nodemap = self.device.RemoteDevice().NodeMaps()[0]

        payload_size = self.nodemap.FindNode("PayloadSize").Value()

        for _ in range(self.datastream.NumBuffersAnnouncedMinRequired()):
            buf = self.datastream.AllocAndAnnounceBuffer(payload_size)
            self.datastream.QueueBuffer(buf)

        self.datastream.StartAcquisition()
        self.nodemap.FindNode("AcquisitionStart").Execute()

        self.running = True
        threading.Thread(target=self._update_loop_ids, daemon=True).start()
        return True

    def _start_ip_camera(self, url):
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            try:
                self.cap.release()
            except:
                pass
            self.cap = cv2.VideoCapture(url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            raise Exception(f"IP kamera açılamadı: {self.source_info['display_name']}")

        ret, test_frame = self.cap.read()
        if not ret or test_frame is None:
            self.cap.release()
            self.cap = None
            raise Exception(f"Kamera açıldı ama görüntü gelmedi: {self.source_info['display_name']}")

        self.running = True
        threading.Thread(target=self._update_loop_ip, daemon=True).start()
        return True

    def _process_frame(self, frame_bgr):
        sets = self.img_settings

        if sets["ct"] != 1.0 or sets["br"] != 0:
            frame_bgr = cv2.convertScaleAbs(frame_bgr, alpha=sets["ct"], beta=sets["br"])

        if sets["r_m"] != 1.0 or sets["g_m"] != 1.0 or sets["b_m"] != 1.0:
            frame_bgr = frame_bgr.astype(np.float32)
            frame_bgr[:, :, 2] *= sets["r_m"]
            frame_bgr[:, :, 1] *= sets["g_m"]
            frame_bgr[:, :, 0] *= sets["b_m"]
            frame_bgr = np.clip(frame_bgr, 0, 255).astype(np.uint8)

        if sets["sh"] != 0.0:
            frame_bgr = apply_sharpness(frame_bgr, sets["sh"])

        if self.ai_enabled:
            frame_bgr = detector.check(frame_bgr)

        return frame_bgr

    def _update_loop_ids(self):
        last_time = time.time()

        while self.running:
            try:
                buffer = self.datastream.WaitForFinishedBuffer(1000)
                ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
                converted = self.converter.Convert(ipl_image, TARGET_PIXEL_FORMAT)
                self.datastream.QueueBuffer(buffer)

                frame_bgr = converted.get_numpy_3D()[:, :, :3].copy()
                frame_bgr = self._process_frame(frame_bgr)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb
            except:
                break

        self.running = False

    def _update_loop_ip(self):
        last_time = time.time()

        while self.running and self.cap is not None:
            try:
                ret, frame_bgr = self.cap.read()

                if not ret or frame_bgr is None:
                    time.sleep(0.2)
                    continue

                frame_bgr = self._process_frame(frame_bgr)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb
            except:
                break

        self.running = False

    def stop(self):
        self.running = False
        time.sleep(0.1)

        try:
            if self.datastream:
                self.datastream.KillWait()
                self.datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
                self.datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
        except:
            pass

        try:
            if self.device:
                self.device.Close()
        except:
            pass

        try:
            if self.cap is not None:
                self.cap.release()
        except:
            pass

        self.device = None
        self.datastream = None
        self.nodemap = None
        self.cap = None
        self.latest_frame = None
        self.current_fps = 0.0


streamers = st.session_state.streamers


def get_or_create_streamer(cam_key):
    if cam_key not in streamers:
        streamers[cam_key] = CameraStreamer()
    return streamers[cam_key]


def stop_all_streamers():
    for key, s in list(streamers.items()):
        try:
            s.stop()
        except:
            pass
    streamers.clear()
    st.session_state.streamers = streamers


def stop_unselected_streamers(selected_keys):
    for cam_key in list(streamers.keys()):
        if cam_key not in selected_keys:
            try:
                streamers[cam_key].stop()
            except:
                pass
            del streamers[cam_key]
    st.session_state.streamers = streamers


def any_camera_running():
    return any(s.running for s in streamers.values())


def total_fps():
    vals = [s.current_fps for s in streamers.values() if s.running]
    return sum(vals) if vals else 0.0


def apply_settings_to_all_streamers():
    settings = {
        "br": st.session_state.br,
        "ct": st.session_state.ct,
        "sh": st.session_state.sh,
        "r_m": st.session_state.r_m,
        "g_m": st.session_state.g_m,
        "b_m": st.session_state.b_m
    }
    for s in streamers.values():
        s.img_settings.update(settings)


def cleanup_all():
    try:
        for s in list(streamers.values()):
            try:
                s.stop()
            except:
                pass
        streamers.clear()
    except:
        pass


atexit.register(cleanup_all)

# ================== ARAYÜZ ==================
st.set_page_config(layout="wide", page_title="VISION-PRO V3.0", page_icon="👁️")

st.markdown("""
<style>
.main { background-color: #0e1117; }

div.stButton > button {
    border-radius: 5px;
    height: 45px;
    font-weight: bold;
}

.stMetric {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 10px;
    border-radius: 10px;
}

.terminal-log {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: monospace;
    padding: 10px;
    border-radius: 5px;
    height: 200px;
    overflow-y: auto;
    border: 1px solid #30363d;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ================== SIDEBAR ==================
with st.sidebar:
    st.title("⚙️ Kontrol Merkezi")
    view_mode = st.radio("Düzen Seçin", ["Tekli Odak", "Izgara (Grid)"], horizontal=True)

    st.divider()

    all_cameras = get_all_cameras()
    camera_names = [cam["display_name"] for cam in all_cameras]

    if view_mode == "Izgara (Grid)":
        st.subheader("🧩 Grid Kamera Seçimi")

        default_grid_selection = st.session_state.grid_selected_cameras
        valid_names = [name for name in default_grid_selection if name in camera_names]

        selected_grid_camera_names = st.multiselect(
            "Grid modunda açılacak kameralar",
            options=camera_names,
            default=valid_names if valid_names else camera_names[:2],
            key="grid_camera_selector"
        )

        st.session_state.grid_selected_cameras = selected_grid_camera_names
        st.divider()

    with st.expander("➕ Kamera Ekle", expanded=False):
        add_type = st.selectbox("Kamera Türü", ["IDS", "IP"], key="add_cam_type")
        add_name = st.text_input("Kamera Adı", value="", placeholder="Örn: Dolum Hattı", key="add_cam_name")

        add_ip = ""
        add_rtsp = ""
        add_full_url = ""

        if add_type == "IP":
            add_ip = st.text_input("IP Adresi", value="", placeholder="Örn: 192.168.8.115", key="add_cam_ip")
            add_rtsp = st.text_input("RTSP Yolu", value="/live/0", placeholder="/live/0", key="add_cam_rtsp")
            add_full_url = st.text_input(
                "Tam RTSP URL (istersen direkt bunu kullan)",
                value="",
                placeholder="Örn: rtsp://192.168.8.115:554/live/0",
                key="add_cam_full_url"
            )

        if st.button("Kamera Ekle", use_container_width=True):
            try:
                add_manual_camera(
                    camera_type=add_type,
                    custom_name=add_name,
                    ip_address=add_ip,
                    rtsp_path=add_rtsp,
                    full_url=add_full_url
                )
                st.success("Kamera eklendi.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.session_state.manual_cameras:
        with st.expander("🗂️ Eklenen Kameralar", expanded=False):
            for i, cam in enumerate(st.session_state.manual_cameras):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(f"**{cam['name']}**")
                    st.caption(f"{cam['type'].upper()} | {cam.get('ip', '-')}")
                with col_b:
                    if st.button("Sil", key=f"del_cam_{i}"):
                        remove_manual_camera(i)
                        st.rerun()

    st.divider()

    selected_cam_name = st.selectbox("Aktif Cihaz", camera_names)

    selected_source = next(
        (cam for cam in all_cameras if cam["display_name"] == selected_cam_name),
        all_cameras[0]
    )

    st.caption(f"Bağlantı Türü: {selected_source['type'].upper()}")
    st.caption(f"IP / Bilgi: {selected_source.get('ip', '-')}")

    st.divider()
    st.subheader("🎨 Görüntü Ayarları")

    ct_val = st.slider("Parlaklık", 0.1, 3.0, value=float(st.session_state.ct))
    br_val = st.slider("Kontrast", -100, 100, value=int(st.session_state.br))
    sh_val = st.slider("Keskinlik", -5.0, 5.0, value=float(st.session_state.sh))

    with st.expander("RGB Kanalları", expanded=False):
        r_val = st.slider("Kırmızı", 0.0, 2.0, value=float(st.session_state.r_m))
        g_val = st.slider("Yeşil", 0.0, 2.0, value=float(st.session_state.g_m))
        b_val = st.slider("Mavi", 0.0, 2.0, value=float(st.session_state.b_m))

    st.session_state.ct = ct_val
    st.session_state.br = br_val
    st.session_state.sh = sh_val
    st.session_state.r_m = r_val
    st.session_state.g_m = g_val
    st.session_state.b_m = b_val

    if st.button("↺ Ayarları Sıfırla", use_container_width=True):
        st.session_state.ct = 1.0
        st.session_state.br = 0
        st.session_state.sh = 0.0
        st.session_state.r_m = 1.0
        st.session_state.g_m = 1.0
        st.session_state.b_m = 1.0
        apply_settings_to_all_streamers()
        log_to_system("Görüntü ayarları sıfırlandı.", "INFO", save_csv=False, show_ui=True)
        st.rerun()

apply_settings_to_all_streamers()

# ================== GRID İÇİN SEÇİLEN KAMERALAR ==================
selected_grid_cameras = [
    cam for cam in all_cameras
    if cam["display_name"] in st.session_state.grid_selected_cameras
]

if not selected_grid_cameras and all_cameras:
    selected_grid_cameras = all_cameras[:1]

# ================== ÜST PANEL ==================
selected_ip_text = selected_source.get("ip", "-")
running_count = sum(1 for s in streamers.values() if s.running)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cihaz", selected_source["display_name"])
m2.metric("Durum", "Online" if any_camera_running() else "Offline", delta=f"{running_count} Aktif")
m3.metric("Toplam FPS", f"{total_fps():.1f}")
m4.metric("Kamera IP", selected_ip_text)

st.divider()

# ================== ORTA PANEL ==================
left_col, center_col, right_col = st.columns([1, 4, 1])

with left_col:
    st.write("### 🎮 Akış")

    if st.button("▶ Başlat", type="primary", use_container_width=True):
        if view_mode == "Tekli Odak":
            stop_all_streamers()
            s = get_or_create_streamer(selected_source["cam_key"])
            s.img_settings.update({
                "br": st.session_state.br,
                "ct": st.session_state.ct,
                "sh": st.session_state.sh,
                "r_m": st.session_state.r_m,
                "g_m": st.session_state.g_m,
                "b_m": st.session_state.b_m
            })
            success = s.start(selected_source)
            if success:
                log_to_system(f"Kamera başlatıldı: {selected_source['display_name']}", "OK", save_csv=True, show_ui=True)
            else:
                log_to_system(f"Kamera başlatılamadı: {selected_source['display_name']}", "HATA", save_csv=True, show_ui=True)
                st.error("Seçilen kamera başlatılamadı.")
        else:
            selected_keys = [cam["cam_key"] for cam in selected_grid_cameras]
            stop_unselected_streamers(selected_keys)

            started_any = False
            for cam in selected_grid_cameras:
                s = get_or_create_streamer(cam["cam_key"])
                s.img_settings.update({
                    "br": st.session_state.br,
                    "ct": st.session_state.ct,
                    "sh": st.session_state.sh,
                    "r_m": st.session_state.r_m,
                    "g_m": st.session_state.g_m,
                    "b_m": st.session_state.b_m
                })
                ok = s.start(cam)
                if ok:
                    started_any = True
                    log_to_system(f"Kamera başlatıldı: {cam['display_name']}", "OK", save_csv=True, show_ui=True)

            if not started_any:
                log_to_system("Seçili grid kameraları başlatılamadı.", "HATA", save_csv=True, show_ui=True)
                st.error("Seçili grid kameraları başlatılamadı.")

        st.rerun()

    if st.button("■ Durdur", use_container_width=True):
        stop_all_streamers()
        log_to_system("Tüm kameralar durduruldu.", "INFO", save_csv=False, show_ui=True)
        st.rerun()

    if st.button("↺ Sıfırla", use_container_width=True):
        st.session_state.update({
            "br": 0,
            "ct": 1.0,
            "sh": 0.0,
            "r_m": 1.0,
            "g_m": 1.0,
            "b_m": 1.0
        })
        apply_settings_to_all_streamers()
        log_to_system("Görüntü ayarları sıfırlandı.", "INFO", save_csv=False, show_ui=True)
        st.rerun()

with center_col:
    if view_mode == "Tekli Odak":
        single_info = st.empty()
        single_box = st.empty()
        grid_boxes = []
    else:
        grid_boxes = []
        cols_per_row = 2
        cams_to_show = selected_grid_cameras

        for i in range(0, len(cams_to_show), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                cam_index = i + j
                if cam_index < len(cams_to_show):
                    cam = cams_to_show[cam_index]
                    with cols[j]:
                        st.markdown(f"**{cam['display_name']}**")
                        info = st.empty()
                        box = st.empty()
                        grid_boxes.append((cam, box, info))
                else:
                    with cols[j]:
                        st.empty()

with right_col:
    st.write("### 📊 Rapor")
    if os.path.exists(CSV_FILE_PATH):
        try:
            df = pd.read_csv(CSV_FILE_PATH)
            st.metric("Kayıt", len(df))
            with open(CSV_FILE_PATH, "rb") as f:
                st.download_button("📥 CSV İndir", f, "rapor.csv", "text/csv")
        except:
            st.metric("Kayıt", 0)
    else:
        st.metric("Kayıt", 0)

st.divider()
st.write("### 📝 Sistem Terminali")
log_container = st.empty()

# ================== CANLI DÖNGÜ ==================
if any_camera_running():
    while any_camera_running():
        if view_mode == "Tekli Odak":
            selected_streamer = get_or_create_streamer(selected_source["cam_key"])
            with selected_streamer.lock:
                frame = selected_streamer.latest_frame
                fps = selected_streamer.current_fps
                is_running = selected_streamer.running

            status_text = "Online" if is_running else "Offline"
            single_info.caption(f"Durum: {status_text} | FPS: {fps:.1f}")

            if frame is not None:
                single_box.image(frame, channels="RGB", use_container_width=True)
            else:
                single_box.image(
                    np.zeros((450, 800, 3), dtype=np.uint8),
                    caption="Görüntü Bekleniyor...",
                    use_container_width=True
                )
        else:
            for cam, box, info in grid_boxes:
                s = get_or_create_streamer(cam["cam_key"])
                with s.lock:
                    frame = s.latest_frame
                    fps = s.current_fps
                    is_running = s.running

                info.caption(f"Durum: {'Online' if is_running else 'Offline'} | FPS: {fps:.1f}")

                if frame is not None:
                    box.image(frame, channels="RGB", use_container_width=True)
                else:
                    box.image(
                        np.zeros((350, 600, 3), dtype=np.uint8),
                        caption=f"{cam['display_name']} - Görüntü Bekleniyor...",
                        use_container_width=True
                    )

        try:
            logs = st.session_state.ui_logs[-8:]
            html_logs = "".join([f"<div>{l}</div>" for l in logs[::-1]])
            log_container.markdown(
                f"<div class='terminal-log'>{html_logs}</div>",
                unsafe_allow_html=True
            )
        except:
            pass

        time.sleep(0.03)
else:
    if view_mode == "Tekli Odak":
        single_info = st.empty()
        single_box = st.empty()

        single_info.caption("Durum: Offline | FPS: 0.0")
        single_box.image(
            np.zeros((450, 800, 3), dtype=np.uint8),
            caption="Kamera Kapalı",
            use_container_width=True
        )
    else:
        cols_per_row = 2
        cams_to_show = selected_grid_cameras

        if cams_to_show:
            for i in range(0, len(cams_to_show), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    cam_index = i + j
                    if cam_index < len(cams_to_show):
                        cam = cams_to_show[cam_index]
                        with cols[j]:
                            st.markdown(f"**{cam['display_name']}**")
                            st.caption("Durum: Offline | FPS: 0.0")
                            st.image(
                                np.zeros((350, 600, 3), dtype=np.uint8),
                                caption=f"{cam['display_name']} - Kamera Kapalı",
                                use_container_width=True
                            )
        else:
            st.info("Grid için en az bir kamera seç.")