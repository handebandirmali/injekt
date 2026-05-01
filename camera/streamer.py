import atexit
import threading
import time
import traceback

import cv2
import numpy as np
from ids_peak import ids_peak, ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl

from config import SETTINGS_REFRESH_INTERVAL_SEC, TARGET_PIXEL_FORMAT
from core.detector import load_detector
from core.image_utils import apply_sharpness
from core.runtime_state import (
    flush_runtime_state,
    mark_camera_offline,
    save_camera_frame,
    update_camera_status,
)
from core.settings_manager import (
    get_camera_settings,
    get_default_image_settings,
    get_reject_settings,
)
from reject.reject_timer import RejectTimer

detector = load_detector()
STREAMERS = {}

# IP kamera bağlantı kopunca kaç kez yeniden dene
IP_MAX_RECONNECT = 5
# Her yeniden denemede kaç saniye bekle
IP_RECONNECT_DELAY = 3.0
# Kaç ardışık boş frame gelince bağlantı kopmuş say
IP_MAX_EMPTY_FRAMES = 30


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
        self.cam_key = None

        # --- DÜZELTME 3: Thread referansını tut ---
        self._thread = None

        self.img_settings = get_default_image_settings()
        self.last_settings_refresh = 0.0
        self.last_error = None
        self.access_mode = None

        reject_settings = get_reject_settings(reload_from_disk=True)
        gecikme = reject_settings.get("gecikme_suresi", 1.20)
        self.reject_timer = RejectTimer(gecikme_suresi=gecikme)
        self.reject_enabled = True

        try:
            ids_peak.Library.Initialize()
        except Exception as e:
            self.last_error = f"ids_peak.Library.Initialize hatası: {e}"

    def is_alive(self):
        """Thread gerçekten çalışıyor mu?"""
        return self._thread is not None and self._thread.is_alive()

    def refresh_runtime_settings(self, force: bool = False):
        now = time.time()
        if not force and (now - self.last_settings_refresh) < SETTINGS_REFRESH_INTERVAL_SEC:
            return
        self.last_settings_refresh = now
        if self.cam_key:
            self.img_settings = get_camera_settings(self.cam_key, reload_from_disk=True)
        reject_settings = get_reject_settings(reload_from_disk=True)
        self.reject_timer.update_settings(gecikme_suresi=reject_settings.get("gecikme_suresi", 1.20))

    def start(self, source_info):
        # --- DÜZELTME 1: Zaten çalışıyorsa dokunma ---
        if self.running and self.is_alive():
            return True

        # Önceki thread bitmişse temizle
        if self._thread is not None and not self._thread.is_alive():
            self._thread = None

        self.source_info = source_info
        self.cam_key = source_info.get("cam_key")
        self.last_error = None
        self.access_mode = None
        self.refresh_runtime_settings(force=True)

        try:
            source_type = source_info.get("type")
            if source_type == "ids":
                return self._start_ids_camera(source_info.get("index", 0))
            if source_type == "ip":
                return self._start_ip_camera(source_info["url"])
            self.last_error = f"Bilinmeyen kamera tipi: {source_type}"
            mark_camera_offline(self.cam_key, self.source_info, self.last_error)
            return False
        except Exception as e:
            self.last_error = f"start() hatası: {e}\n{traceback.format_exc()}"
            self.stop()
            return False

    def _open_ids_device_with_fallback(self, dev):
        attempts = []
        access_modes = [
            ("control", getattr(ids_peak, "DeviceAccessType_Control", None)),
            ("readonly", getattr(ids_peak, "DeviceAccessType_ReadOnly", None)),
        ]
        for label, mode in access_modes:
            if mode is None:
                continue
            try:
                opened = dev.OpenDevice(mode)
                if opened is not None:
                    return opened, label
            except Exception as e:
                attempts.append(f"{label}: {e}")
        raise Exception(" | ".join(attempts) if attempts else "Uygun access mode bulunamadı.")

    def _start_ids_camera(self, camera_index=0):
        try:
            device_manager = ids_peak.DeviceManager.Instance()
            device_manager.Update()
            devices = device_manager.Devices()
            if devices.empty():
                raise Exception("IDS kamera bağlı değil veya sistem tarafından görülmüyor.")

            try:
                device_count = len(devices)
            except Exception:
                device_count = devices.size()

            if camera_index >= device_count:
                raise Exception(f"İstenen IDS kamera indexi bulunamadı: {camera_index}")

            dev = devices[camera_index]
            self.device, self.access_mode = self._open_ids_device_with_fallback(dev)
            if self.device is None:
                raise Exception("OpenDevice başarısız oldu.")

            self.datastream = self.device.DataStreams()[0].OpenDataStream()
            if self.datastream is None:
                raise Exception("DataStream açılamadı.")

            remote_device = self.device.RemoteDevice()
            if remote_device is None:
                raise Exception("RemoteDevice alınamadı.")

            self.nodemap = remote_device.NodeMaps()[0]
            payload_size = self.nodemap.FindNode("PayloadSize").Value()
            min_required = self.datastream.NumBuffersAnnouncedMinRequired()
            if min_required <= 0:
                min_required = 3

            for _ in range(min_required):
                buf = self.datastream.AllocAndAnnounceBuffer(payload_size)
                self.datastream.QueueBuffer(buf)

            self.datastream.StartAcquisition()
            self.nodemap.FindNode("AcquisitionStart").Execute()

            self.running = True
            update_camera_status(
                self.cam_key,
                {
                    "running": True,
                    "type": "ids",
                    "access_mode": self.access_mode,
                    "display_name": self.source_info.get("display_name"),
                    "ip": self.source_info.get("ip"),
                    "source_info": self.source_info,
                    "last_error": None,
                },
                force=True,
            )
            t = threading.Thread(target=self._update_loop_ids, daemon=True)
            t.start()
            self._thread = t
            return True
        except Exception as e:
            self.last_error = f"IDS start hatası: {e}\n{traceback.format_exc()}"
            self.stop()
            return False

    def _start_ip_camera(self, url):
        try:
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                try:
                    cap.release()
                except Exception:
                    pass
                cap = cv2.VideoCapture(url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                raise Exception(f"IP kamera açılamadı: {self.source_info['display_name']}")

            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                cap.release()
                raise Exception(f"Kamera açıldı ama görüntü gelmedi: {self.source_info['display_name']}")

            self.cap = cap
            self.running = True
            update_camera_status(
                self.cam_key,
                {
                    "running": True,
                    "type": "ip",
                    "display_name": self.source_info.get("display_name"),
                    "ip": self.source_info.get("ip"),
                    "source_info": self.source_info,
                    "last_error": None,
                },
                force=True,
            )
            t = threading.Thread(target=self._update_loop_ip, daemon=True)
            t.start()
            self._thread = t
            return True
        except Exception as e:
            self.last_error = f"IP start hatası: {e}\n{traceback.format_exc()}"
            self.stop()
            return False

    def _extract_detector_result(self):
        detected = False
        meta = {}
        try:
            if hasattr(detector, "last_status"):
                detected = str(detector.last_status).lower() == "detected"
            elif hasattr(detector, "last_detected"):
                detected = bool(detector.last_detected)
            elif hasattr(detector, "detected"):
                detected = bool(detector.detected)
        except Exception:
            detected = False

        for attr, key, cast in [
            ("last_confidence", "confidence", float),
            ("last_box_count", "box_count", int),
        ]:
            try:
                if hasattr(detector, attr):
                    meta[key] = cast(getattr(detector, attr))
            except Exception:
                pass

        if self.source_info:
            meta["camera"] = self.source_info.get("display_name", "unknown")
        return detected, meta

    def _handle_reject_if_needed(self):
        try:
            self.reject_timer.process()
        except Exception:
            pass

    def _process_frame(self, frame_bgr):
        self.refresh_runtime_settings()
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
            detected, meta = self._extract_detector_result()
            if self.reject_enabled and detected:
                self.reject_timer.schedule(source="AI_DETECT", meta=meta)
            update_camera_status(
                self.cam_key,
                {
                    "detected": detected,
                    "detector_meta": meta,
                    "last_detection_status": "detected" if detected else "not_found",
                },
                force=False,
            )
        return frame_bgr

    def _store_processed_frame(self, frame_rgb):
        save_camera_frame(self.cam_key, frame_rgb, self.source_info.get("display_name"))
        update_camera_status(
            self.cam_key,
            {
                "running": self.running,
                "fps": round(float(self.current_fps), 2),
                "last_error": self.last_error,
                "access_mode": self.access_mode,
            },
            force=False,
        )
        flush_runtime_state(force=False)

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
                self._handle_reject_if_needed()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb
                self._store_processed_frame(frame_rgb)
            except Exception as e:
                self.last_error = f"IDS update loop hatası: {e}\n{traceback.format_exc()}"
                break

        self.running = False
        mark_camera_offline(self.cam_key, self.source_info, self.last_error)

    # --- DÜZELTME 2: IP kamera reconnect mantığı ---
    def _update_loop_ip(self):
        last_time = time.time()
        empty_frame_count = 0

        while self.running:
            if self.cap is None:
                self.running = False
                break

            try:
                ret, frame_bgr = self.cap.read()

                if not ret or frame_bgr is None:
                    empty_frame_count += 1
                    time.sleep(0.2)

                    # Çok fazla boş frame → bağlantı kopmuş, reconnect dene
                    if empty_frame_count >= IP_MAX_EMPTY_FRAMES:
                        from debug_log import log_to_system
                        log_to_system(
                            f"IP kamera bağlantısı koptu, yeniden bağlanılıyor: "
                            f"{self.source_info.get('display_name', self.cam_key)}",
                            "UYARI", save_csv=True, show_ui=False
                        )
                        reconnected = self._reconnect_ip()
                        if reconnected:
                            empty_frame_count = 0
                            log_to_system(
                                f"IP kamera yeniden bağlandı: "
                                f"{self.source_info.get('display_name', self.cam_key)}",
                                "OK", save_csv=True, show_ui=False
                            )
                        else:
                            # Tüm denemeler başarısız → loop'tan çık, worker yeniden başlatacak
                            self.last_error = (
                                f"IP kamera yeniden bağlanamadı: "
                                f"{self.source_info.get('display_name', self.cam_key)}"
                            )
                            break
                    continue

                # Başarılı frame → sayacı sıfırla
                empty_frame_count = 0
                frame_bgr = self._process_frame(frame_bgr)
                self._handle_reject_if_needed()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb
                self._store_processed_frame(frame_rgb)

            except Exception as e:
                self.last_error = f"IP update loop hatası: {e}\n{traceback.format_exc()}"
                break

        self.running = False
        mark_camera_offline(self.cam_key, self.source_info, self.last_error)

    def _reconnect_ip(self):
        """IP kamera bağlantısını yeniden kurmaya çalışır."""
        url = self.source_info.get("url", "")
        if not url:
            return False

        # Eski cap'i kapat
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None

        for attempt in range(1, IP_MAX_RECONNECT + 1):
            if not self.running:
                return False
            try:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    cap.release()
                    raise Exception("cap.isOpened() = False")

                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.release()
                    raise Exception("İlk frame okunamadı")

                self.cap = cap
                update_camera_status(
                    self.cam_key,
                    {"running": True, "last_error": None},
                    force=True,
                )
                return True
            except Exception as e:
                from debug_log import log_to_system
                log_to_system(
                    f"Reconnect denemesi {attempt}/{IP_MAX_RECONNECT} başarısız: {e}",
                    "UYARI", save_csv=False, show_ui=False
                )
                time.sleep(IP_RECONNECT_DELAY)

        return False

    def stop(self):
        self.running = False

        # --- DÜZELTME 3: Thread'in bitmesini bekle (max 2 sn) ---
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

        try:
            self.reject_timer.clear_queue()
        except Exception:
            pass
        try:
            if self.datastream:
                self.datastream.KillWait()
                self.datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
                self.datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
        except Exception:
            pass
        try:
            if self.device:
                self.device.Close()
        except Exception:
            pass
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass

        self.device = None
        self.datastream = None
        self.nodemap = None
        self.cap = None
        self.latest_frame = None
        self.current_fps = 0.0
        self.access_mode = None
        if self.cam_key:
            mark_camera_offline(self.cam_key, self.source_info, self.last_error)


def get_streamers():
    return STREAMERS


def get_or_create_streamer(cam_key):
    if cam_key not in STREAMERS:
        STREAMERS[cam_key] = CameraStreamer()
    return STREAMERS[cam_key]


def apply_settings_to_streamer(cam_key):
    streamer = STREAMERS.get(cam_key)
    if streamer:
        streamer.refresh_runtime_settings(force=True)


def apply_reject_settings_to_streamer(cam_key):
    streamer = STREAMERS.get(cam_key)
    if streamer:
        streamer.refresh_runtime_settings(force=True)


def apply_reject_settings_to_all_streamers():
    for streamer in STREAMERS.values():
        try:
            streamer.refresh_runtime_settings(force=True)
        except Exception:
            pass


def stop_all_streamers():
    for _, s in list(STREAMERS.items()):
        try:
            s.stop()
        except Exception:
            pass
    STREAMERS.clear()


def any_camera_running():
    return any(s.running for s in STREAMERS.values())


def total_fps():
    vals = [s.current_fps for s in STREAMERS.values() if s.running]
    return sum(vals) if vals else 0.0


def cleanup_all():
    try:
        for s in list(STREAMERS.values()):
            try:
                s.stop()
            except Exception:
                pass
        STREAMERS.clear()
    except Exception:
        pass


def get_streamer(cam_key):
    return STREAMERS.get(cam_key)


def get_active_ids_streamer(cam_key):
    s = get_streamer(cam_key)
    if s is None or not s.running or s.source_info is None:
        return None
    if s.source_info.get("type") != "ids" or s.device is None:
        return None
    return s


atexit.register(cleanup_all)