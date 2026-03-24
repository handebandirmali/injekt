import atexit
import threading
import time

import cv2
import streamlit as st
import numpy as np
from ids_peak import ids_peak, ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl

from config import TARGET_PIXEL_FORMAT
from core.detector import load_detector
from core.image_utils import apply_sharpness
from core.settings_manager import get_camera_settings, get_default_image_settings


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
        except:
            pass
    streamers.clear()
    st.session_state.streamers = streamers


def stop_unselected_streamers(selected_keys):
    streamers = get_streamers()
    for cam_key in list(streamers.keys()):
        if cam_key not in selected_keys:
            try:
                streamers[cam_key].stop()
            except:
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
            except:
                pass
        streamers.clear()
    except:
        pass


atexit.register(cleanup_all)