import streamlit as st
import cv2
import time
import numpy as np
import threading
import os
import pandas as pd
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

# ================== CONFIG & PATHS ==================
LOG_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\log.txt"
CSV_FILE_PATH = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"
MODEL_PATH = r"C:\Users\Hande\Desktop\inkjet\train4_best.pt"
TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8

# ================== VARSAYILAN IDS ==================
DEFAULT_IDS_CAMERA = {
    "type": "ids",
    "name": "IDS Kamera",
    "index": 0,
    "ip": "IDS / Yerel Bağlantı",
    "manual": False
}

# ================== YARDIMCI FONKSİYONLAR ==================
def log_to_system(msg, status="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{status}] {msg}\n")
    except:
        pass

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

        log_to_system(f"IDS tarama tamamlandı. Bulunan cihaz sayısı: {len(cameras)}", "INFO")

    except Exception as e:
        log_to_system(f"IDS kamera tarama hatası: {e}", "HATA")

    return cameras


def get_all_cameras():
    detected_ids = get_detected_ids_cameras()
    all_sources = []

    # IDS bağlıysa gerçek kameraları al, bağlı değilse varsayılan bir IDS seçeneği göster
    if detected_ids:
        all_sources.extend(detected_ids)
    else:
        all_sources.append(DEFAULT_IDS_CAMERA.copy())

    # Elle eklenen kameraları ekle
    for cam in st.session_state.manual_cameras:
        all_sources.append(cam.copy())

    # Hat 1 / Hat 2 / Hat 3 isimlendirmesi
    labeled_sources = []
    for i, cam in enumerate(all_sources):
        cam_copy = cam.copy()
        cam_copy["display_name"] = safe_camera_label(i, cam_copy)
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
    log_to_system(f"Manuel kamera eklendi: {custom_name} ({camera_type.upper()})", "OK")


def remove_manual_camera(idx):
    if 0 <= idx < len(st.session_state.manual_cameras):
        removed = st.session_state.manual_cameras.pop(idx)
        log_to_system(f"Manuel kamera silindi: {removed.get('name', 'Bilinmeyen')}", "UYARI")


# ================== KAMERA SINIFI ==================
@st.cache_resource
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
                log_to_system("Bilinmeyen kamera tipi", "HATA")
                return False

        except Exception as e:
            log_to_system(f"Kamera başlatma hatası: {e}", "HATA")
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
        log_to_system(f"IDS kamera başlatıldı: {self.source_info['display_name']}", "OK")
        threading.Thread(target=self._update_loop_ids, daemon=True).start()
        return True

    def _start_ip_camera(self, url):
        log_to_system(f"IP kamera bağlanmaya çalışılıyor: {url}", "INFO")

        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            log_to_system("FFMPEG ile açılamadı, normal bağlantı deneniyor...", "UYARI")
            try:
                self.cap.release()
            except:
                pass
            self.cap = cv2.VideoCapture(url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            raise Exception(f"IP kamera açılamadı: {url}")

        ret, test_frame = self.cap.read()
        if not ret or test_frame is None:
            self.cap.release()
            self.cap = None
            raise Exception(f"Kamera açıldı ama görüntü gelmedi: {url}")

        self.running = True
        log_to_system(f"IP kamera başlatıldı: {self.source_info['display_name']} - {url}", "OK")
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

            except Exception as e:
                log_to_system(f"IDS akış hatası: {e}", "HATA")
                break

        self.running = False

    def _update_loop_ip(self):
        last_time = time.time()

        while self.running and self.cap is not None:
            try:
                ret, frame_bgr = self.cap.read()

                if not ret or frame_bgr is None:
                    log_to_system("IP kameradan görüntü alınamadı", "UYARI")
                    time.sleep(0.2)
                    continue

                frame_bgr = self._process_frame(frame_bgr)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb

            except Exception as e:
                log_to_system(f"IP akış hatası: {e}", "HATA")
                break

        self.running = False

    def stop(self):
        self.running = False
        time.sleep(0.3)

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

        log_to_system("Kamera durduruldu", "UYARI")


streamer = CameraStreamer()

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

    # ===== Kamera Ekleme Bölümü =====
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

    # ===== Eklenen kameraları göster =====
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

    all_cameras = get_all_cameras()
    camera_names = [cam["display_name"] for cam in all_cameras]
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
        st.rerun()

    streamer.img_settings.update({
        "br": st.session_state.br,
        "ct": st.session_state.ct,
        "sh": st.session_state.sh,
        "r_m": st.session_state.r_m,
        "g_m": st.session_state.g_m,
        "b_m": st.session_state.b_m
    })

# ================== ÜST PANEL ==================
selected_ip_text = selected_source.get("ip", "-")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cihaz", selected_source["display_name"])
m2.metric("Durum", "Online" if streamer.running else "Offline", delta="Aktif" if streamer.running else "Pasif")
m3.metric("FPS", f"{streamer.current_fps:.1f}")
m4.metric("Kamera IP", selected_ip_text)

st.divider()

# ================== ORTA PANEL ==================
left_col, center_col, right_col = st.columns([1, 4, 1])

with left_col:
    st.write("### 🎮 Akış")

    if st.button("▶ Başlat", type="primary", use_container_width=True):
        streamer.stop()
        success = streamer.start(selected_source)
        if success:
            st.rerun()
        else:
            st.error("Seçilen kamera başlatılamadı.")

    if st.button("■ Durdur", use_container_width=True):
        streamer.stop()
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
        st.rerun()

with center_col:
    if view_mode == "Tekli Odak":
        video_box = st.empty()
    else:
        grid_col1, grid_col2 = st.columns(2)
        video_box = grid_col1.empty()
        grid_col2.image(
            np.zeros((450, 800, 3), dtype=np.uint8),
            caption="Diğer Kamera Bekleniyor...",
            use_container_width=True
        )

with right_col:
    st.write("### 📊 Rapor")
    if os.path.exists(CSV_FILE_PATH):
        try:
            df = pd.read_csv(CSV_FILE_PATH)
            st.metric("Tespit", len(df))
            with open(CSV_FILE_PATH, "rb") as f:
                st.download_button("📥 CSV İndir", f, "rapor.csv", "text/csv")
        except:
            st.metric("Tespit", 0)
    else:
        st.metric("Tespit", 0)

# ================== ALT PANEL ==================
st.divider()
st.write("### 📝 Sistem Terminali")
log_container = st.empty()

# ================== CANLI DÖNGÜ ==================
if streamer.running:
    while streamer.running:
        with streamer.lock:
            frame = streamer.latest_frame

        if frame is not None:
            video_box.image(frame, channels="RGB", use_container_width=True)

        if os.path.exists(LOG_FILE_PATH):
            try:
                with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
                    logs = f.readlines()[-10:]
                    html_logs = "".join([f"<div>{l.strip()}</div>" for l in logs[::-1]])
                    log_container.markdown(
                        f"<div class='terminal-log'>{html_logs}</div>",
                        unsafe_allow_html=True
                    )
            except:
                pass

        time.sleep(0.03)
else:
    video_box.image(
        np.zeros((450, 800, 3), dtype=np.uint8),
        caption="Kamera Kapalı",
        use_container_width=True
    )