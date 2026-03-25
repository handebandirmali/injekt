import atexit
import threading
import time
import traceback

import cv2
import numpy as np
import streamlit as st
from ids_peak import ids_peak, ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl

from config import TARGET_PIXEL_FORMAT
from core.detector import load_detector
from core.image_utils import apply_sharpness
from core.settings_manager import get_camera_settings, get_default_image_settings
from reject.reject_timer import RejectTimer

detector = load_detector()


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

        self.img_settings = get_default_image_settings()

        self.last_error = None
        self.access_mode = None  # "control" | "readonly" | None

        self.reject_timer = RejectTimer(
            delay_seconds=1.20,
            pulse_seconds=0.15,
            cooldown_seconds=0.70
        )
        self.reject_enabled = True

        try:
            ids_peak.Library.Initialize()
        except Exception as e:
            self.last_error = f"ids_peak.Library.Initialize hatası: {e}"

    def start(self, source_info):
        if self.running:
            self.stop()

        self.source_info = source_info
        self.last_error = None
        self.access_mode = None

        try:
            source_type = source_info.get("type")

            if source_type == "ids":
                return self._start_ids_camera(source_info.get("index", 0))
            elif source_type == "ip":
                return self._start_ip_camera(source_info["url"])
            else:
                self.last_error = f"Bilinmeyen kamera tipi: {source_type}"
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

            try:
                model = dev.ModelName()
            except Exception:
                model = "Bilinmeyen Model"

            try:
                serial = dev.SerialNumber()
            except Exception:
                serial = "Bilinmeyen Seri"

            self.device, self.access_mode = self._open_ids_device_with_fallback(dev)

            if self.device is None:
                raise Exception("OpenDevice başarısız oldu.")

            data_streams = self.device.DataStreams()
            if len(data_streams) == 0:
                raise Exception("Kamerada açılabilir DataStream bulunamadı.")

            self.datastream = data_streams[0].OpenDataStream()
            if self.datastream is None:
                raise Exception("DataStream açılamadı.")

            remote_device = self.device.RemoteDevice()
            if remote_device is None:
                raise Exception("RemoteDevice alınamadı.")

            node_maps = remote_device.NodeMaps()
            if len(node_maps) == 0:
                raise Exception("NodeMap bulunamadı.")

            self.nodemap = node_maps[0]

            payload_node = self.nodemap.FindNode("PayloadSize")
            if payload_node is None:
                raise Exception("PayloadSize node'u bulunamadı.")

            payload_size = payload_node.Value()
            if payload_size is None or int(payload_size) <= 0:
                raise Exception(f"Geçersiz PayloadSize değeri: {payload_size}")

            min_required = self.datastream.NumBuffersAnnouncedMinRequired()
            if min_required <= 0:
                min_required = 3

            for _ in range(min_required):
                buf = self.datastream.AllocAndAnnounceBuffer(payload_size)
                self.datastream.QueueBuffer(buf)

            self.datastream.StartAcquisition()

            acq_start = self.nodemap.FindNode("AcquisitionStart")
            if acq_start is None:
                raise Exception("AcquisitionStart node'u bulunamadı.")

            acq_start.Execute()

            self.running = True
            self.last_error = None
            threading.Thread(target=self._update_loop_ids, daemon=True).start()
            return True

        except Exception as e:
            self.last_error = (
                f"IDS start hatası: {e}\n"
                f"Kamera index: {camera_index}\n"
                f"Kaynak: {self.source_info}\n"
                f"Model/Seri: {locals().get('model', '?')} / {locals().get('serial', '?')}\n"
                f"{traceback.format_exc()}"
            )
            self.stop()
            return False

    def _start_ip_camera(self, url):
        try:
            self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception:
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
            self.last_error = None
            self.access_mode = None
            threading.Thread(target=self._update_loop_ip, daemon=True).start()
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

        try:
            if hasattr(detector, "last_confidence"):
                meta["confidence"] = float(detector.last_confidence)
        except Exception:
            pass

        try:
            if hasattr(detector, "last_box_count"):
                meta["box_count"] = int(detector.last_box_count)
        except Exception:
            pass

        try:
            if self.source_info:
                meta["camera"] = self.source_info.get("display_name", "unknown")
        except Exception:
            pass

        return detected, meta

    def _handle_reject_if_needed(self):
        try:
            self.reject_timer.process()
        except Exception:
            pass

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

            detected, meta = self._extract_detector_result()
            if self.reject_enabled and detected:
                self.reject_timer.schedule(
                    source="AI_DETECT",
                    meta=meta
                )

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
                self._handle_reject_if_needed()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb

            except Exception as e:
                self.last_error = f"IDS update loop hatası: {e}\n{traceback.format_exc()}"
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
                self._handle_reject_if_needed()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                now = time.time()
                self.current_fps = 1.0 / max(now - last_time, 0.001)
                last_time = now

                with self.lock:
                    self.latest_frame = frame_rgb

            except Exception as e:
                self.last_error = f"IP update loop hatası: {e}\n{traceback.format_exc()}"
                break

        self.running = False

    def stop(self):
        self.running = False
        time.sleep(0.1)

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


def get_streamers():
    return st.session_state.streamers


def get_or_create_streamer(cam_key):
    streamers = get_streamers()
    if cam_key not in streamers:
        streamers[cam_key] = CameraStreamer()
    return streamers[cam_key]


def apply_settings_to_streamer(cam_key):
    streamers = get_streamers()
    if cam_key in streamers:
        cam_settings = get_camera_settings(cam_key)
        streamers[cam_key].img_settings.update(cam_settings)


def stop_all_streamers():
    streamers = get_streamers()
    for _, s in list(streamers.items()):
        try:
            s.stop()
        except Exception:
            pass
    streamers.clear()
    st.session_state.streamers = streamers


def stop_unselected_streamers(selected_keys):
    streamers = get_streamers()
    for cam_key in list(streamers.keys()):
        if cam_key not in selected_keys:
            try:
                streamers[cam_key].stop()
            except Exception:
                pass
            del streamers[cam_key]
    st.session_state.streamers = streamers


def any_camera_running():
    streamers = get_streamers()
    return any(s.running for s in streamers.values())


def total_fps():
    streamers = get_streamers()
    vals = [s.current_fps for s in streamers.values() if s.running]
    return sum(vals) if vals else 0.0


def cleanup_all():
    try:
        streamers = get_streamers()
        for s in list(streamers.values()):
            try:
                s.stop()
            except Exception:
                pass
        streamers.clear()
    except Exception:
        pass


def get_streamer(cam_key):
    streamers = get_streamers()
    return streamers.get(cam_key)


def get_active_ids_streamer(cam_key):
    s = get_streamer(cam_key)
    if s is None:
        return None
    if not s.running:
        return None
    if s.source_info is None:
        return None
    if s.source_info.get("type") != "ids":
        return None
    if s.device is None:
        return None
    return s


atexit.register(cleanup_all)