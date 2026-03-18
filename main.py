import sys
import time
import cv2
import numpy as np
from datetime import datetime

from inkjet_check_save import InkjetCheck

# --- PySide6 tercih, yoksa PySide2'ye düş ---
try:
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QVBoxLayout, QLabel, QMainWindow, QMessageBox,
        QWidget, QSizePolicy, QTextEdit, QGridLayout, QPushButton
    )
    from PySide6.QtGui import QImage, QFont, QPixmap
    from PySide6.QtCore import Qt, Slot, QTimer
except ImportError:
    from PySide2.QtWidgets import (
        QApplication, QHBoxLayout, QVBoxLayout, QLabel, QMainWindow, QMessageBox,
        QWidget, QSizePolicy, QTextEdit, QGridLayout, QPushButton
    )
    from PySide2.QtGui import QImage, QFont, QPixmap
    from PySide2.QtCore import Qt, Slot, QTimer

from ids_peak import ids_peak, ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl

VERSION = "2.3.0"
FPS_LIMIT = 30
TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8

class ConnectCamera(QMainWindow):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # --- Pencere ---
        self.setWindowTitle("Inkjet Check - IDS Peak Integration")
        self.resize(1400, 800)

        # --- Ana widget / layout ---
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QGridLayout(self.central_widget)

        # --- Kamera değişkenleri ---
        self.__device = None
        self.__nodemap_remote_device = None
        self.__datastream = None
        self.__image_converter = ids_peak_ipl.ImageConverter()

        # --- Sayaçlar ve zamanlayıcı ---
        self.__acquisition_timer = QTimer()
        self.__acquisition_running = False
        self.__frame_counter = 0
        self.__error_counter = 0
        self.__last_fps_time = time.time()
        self.__frames_since_last = 0

        # --- Geliştirdiğin Arayüzün Kurulumu ---
        self._setup_dashboard_ui()

        # --- Saat Zamanlayıcısı ---
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_datetime)
        self.clock_timer.start(1000)

        # --- Inkjet detektörü ---
        # Yolunu kendi sistemine göre güncellemen gerekebilir
        self.detector = InkjetCheck(r"C:\Users\Hande\Desktop\inkjet\train4_best.pt")
        self.enable_detection = True

        # --- IDS Peak init ---
        try:
            ids_peak.Library.Initialize()
        except Exception as e:
            self._log(f"[HATA] IDS Peak init: {e}")
            QMessageBox.critical(self, "IDS Peak", f"Initialize() hatası: {e}")
            return

        # Uygulama açılırken otomatik bağlanmasını istemiyorsan aşağıdaki bloğu yoruma alabilirsin. 
        # Ben Butonlar çalıştığı için yoruma alıyorum, başlat butonuna basınca kamera açılacak.
        # if self.__open_device():
        #     self.__start_acquisition()
        # else:
        #     self._log("[HATA] Cihaz acilmadi.")
        #     self.__destroy_all()
        #     sys.exit(1)

    def __del__(self):
        self.__destroy_all()

    # ==========================================
    # SENİN GELİŞTİRDİĞİN ARAYÜZ MİMARİSİ
    # ==========================================
    def _setup_dashboard_ui(self):
        # 1. Üst Kısım (Başlık ve Tarih/Saat)
        self.title = QLabel("Inkjet Check")
        self.title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))

        self.datetime_label = QLabel()
        self.datetime_label.setFont(QFont("Segoe UI", 12))

        top_layout = QVBoxLayout()
        top_layout.addWidget(self.title)
        top_layout.addWidget(self.datetime_label)
        self.main_layout.addLayout(top_layout, 0, 0, 1, 2)

        # 2. Sol Kısım: Video Alanı
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background:black")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.video_label, 1, 0)

        # 3. Sağ Kısım: Dashboard (Bilgi Kartları)
        right_panel = QVBoxLayout()

        self.fps_label = QLabel("FPS: 0.00")
        self.cam_type = QLabel("Kamera: IDS Peak Ethernet")
        self.cam_ip = QLabel("IP: Bağlantı Bekleniyor...")
        self.status_label = QLabel("Durum: Kapalı")

        # Kart Stilleri
        for w in [self.fps_label, self.cam_type, self.cam_ip, self.status_label]:
            w.setStyleSheet("background:white; padding:8px; border-radius:6px;")
            right_panel.addWidget(w)

        # Butonlar
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶")
        self.btn_stop = QPushButton("■")
        self.btn_restart = QPushButton("⟳")

        # Buton Olayları (Senin butonlarına eski kamera fonksiyonlarını bağladım)
        self.btn_play.clicked.connect(self.start_video)
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_restart.clicked.connect(self.restart_video)

        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_restart)

        right_panel.addLayout(btn_layout)
        right_panel.addStretch()
        self.main_layout.addLayout(right_panel, 1, 1)

        # 4. Sol Alt Kısım: Log Ekranı
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color:#0b0b0b; color:#c8facc; font-family:Consolas; font-size:10pt;")
        self.main_layout.addWidget(self.console, 2, 0, 1, 2)

    def update_datetime(self):
        self.datetime_label.setText(datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))

    def _log(self, msg: str):
        if self.console:
            self.console.append(f"[{datetime.now():%H:%M:%S}] {msg}")
            self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())
        else:
            print(msg)

    # ==========================================
    # ARAYÜZ BUTONLARININ KAMERA İLE HABERLEŞMESİ
    # ==========================================
    def start_video(self):
        if not self.__acquisition_running:
            self._log("Kamera başlatılıyor...")
            
            # Eğer cihaza henüz hiç bağlanılmadıysa önce bağlan
            if self.__device is None:
                if not self.__open_device():
                    self._log("[HATA] Cihaz açılamadı.")
                    return
            
            # Cihaz açıksa görüntü akışını başlat
            self.__start_acquisition()

    def stop_video(self):
        if self.__acquisition_running:
            self.__stop_acquisition()
            # self.__close_device()  <-- HATAYA SEBEP OLAN BU SATIRI KALDIRDIK
            self.status_label.setText("Durum: Durduruldu")
            self.status_label.setStyleSheet("background:white; padding:8px; border-radius:6px; color:red;")
            self._log("Kamera akışı durduruldu.")

    def restart_video(self):
        self._log("Kamera yeniden başlatılıyor...")
        self.stop_video()
        
        # IDS Peak'in bufferları temizlemesi için çok kısa bir süre tanıyoruz
        QTimer.singleShot(300, self.start_video)

    # ==========================================
    # SENİN MEVCUT IDS PEAK KAMERA KODLARIN
    # (Hiçbir mantığı değiştirilmedi, sadece arayüze veri basıyor)
    # ==========================================
    def __destroy_all(self):
        try:
            self.__stop_acquisition()
        except Exception:
            pass
        try:
            self.__close_device()
        except Exception:
            pass
        try:
            ids_peak.Library.Close()
        except Exception:
            pass

    def __open_device(self):
        try:
            device_manager = ids_peak.DeviceManager.Instance()
            device_manager.Update()

            if device_manager.Devices().empty():
                QMessageBox.critical(self, "Hata", "Hic cihaz bulunamadi!")
                return False

            for device in device_manager.Devices():
                if device.IsOpenable():
                    self.__device = device.OpenDevice(ids_peak.DeviceAccessType_Control)
                    break

            if self.__device is None:
                QMessageBox.critical(self, "Hata", "Cihaz acilamadi!")
                return False

            datastreams = self.__device.DataStreams()
            if datastreams.empty():
                QMessageBox.critical(self, "Hata", "Cihazda DataStream yok!")
                return False

            self.__datastream = datastreams[0].OpenDataStream()
            self.__nodemap_remote_device = self.__device.RemoteDevice().NodeMaps()[0]

            try:
                self.__nodemap_remote_device.FindNode("UserSetSelector").SetCurrentEntry("User0")
                self.__nodemap_remote_device.FindNode("UserSetLoad").Execute()
                self.__nodemap_remote_device.FindNode("UserSetLoad").WaitUntilDone()
            except ids_peak.Exception as e:
                self._log(f"[UYARI] UserSet yüklenemedi, varsayilan ayarlar kullaniliyor: {e}")
                pass

            payload_size = self.__nodemap_remote_device.FindNode("PayloadSize").Value()
            buffer_count_min = self.__datastream.NumBuffersAnnouncedMinRequired()
            for _ in range(buffer_count_min):
                buf = self.__datastream.AllocAndAnnounceBuffer(payload_size)
                self.__datastream.QueueBuffer(buf)

            self.cam_ip.setText("IP: IDS Stream Aktif")
            self._log("[OK] Kamera bağlandı.")
            return True

        except ids_peak.Exception as e:
            QMessageBox.critical(self, "Exception", str(e))
            self._log(f"[HATA] __open_device: {e}")
            return False

    def __close_device(self):
        self.__stop_acquisition()
        if self.__datastream is not None:
            try:
                for buffer in self.__datastream.AnnouncedBuffers():
                    self.__datastream.RevokeBuffer(buffer)
            except Exception as e:
                self._log(f"[UYARI] Buffer revoke: {e}")

    def __start_acquisition(self):
        if self.__device is None or self.__acquisition_running:
            return False

        target_fps = FPS_LIMIT
        try:
            max_fps = self.__nodemap_remote_device.FindNode("AcquisitionFrameRate").Maximum()
            target_fps = min(max_fps, FPS_LIMIT)
            self.__nodemap_remote_device.FindNode("AcquisitionFrameRate").SetValue(target_fps)
            self._log(f"[OK] FPS limiti: {target_fps:.2f}")
        except ids_peak.Exception:
            self._log("[UYARI] FPS sinirlamasini desteklenmiyor.")

        self.__acquisition_timer.setInterval(int((1.0 / max(1.0, target_fps)) * 1000))
        self.__acquisition_timer.timeout.connect(self.on_acquisition_timer)

        try:
            self.__datastream.StartAcquisition()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").Execute()
            self.__nodemap_remote_device.FindNode("AcquisitionStart").WaitUntilDone()
        except Exception as e:
            self._log(f"[HATA] AcquisitionStart: {e}")
            return False

        self.__frame_counter = 0
        self.__error_counter = 0
        self.__last_fps_time = time.time()
        self.__frames_since_last = 0

        self.__acquisition_timer.start()
        self.__acquisition_running = True
        self.status_label.setText("Durum: Çalışıyor")
        self.status_label.setStyleSheet("background:white; padding:8px; border-radius:6px; color:green;")
        self._log("[OK] Kamera akisi basladi.")
        return True

    def __stop_acquisition(self):
        if self.__device is None or not self.__acquisition_running:
            return
        try:
            self.__acquisition_timer.stop()
            self.__datastream.KillWait()
            self.__datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
            self.__datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
            self.__acquisition_running = False
        except Exception as e:
            self._log(f"[UYARI] stop_acquisition: {e}")

    def _update_perf_labels(self):
        self.__frames_since_last += 1
        now = time.time()
        dt = now - self.__last_fps_time
        if dt >= 1.0:
            fps = self.__frames_since_last / dt
            self.fps_label.setText(f"FPS: {fps:0.2f}")
            self.__frames_since_last = 0
            self.__last_fps_time = now

    def _update_status(self):
        self.status_label.setText(f"Durum: Çalışıyor | Frame: {self.__frame_counter}")

    @Slot()
    def on_acquisition_timer(self):
        try:
            buffer = self.__datastream.WaitForFinishedBuffer(5000)
            ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
            converted = self.__image_converter.Convert(ipl_image, TARGET_PIXEL_FORMAT)
            self.__datastream.QueueBuffer(buffer)

            frame = converted.get_numpy_3D()  # BGRA format
            frame_bgr = frame[:, :, :3]

            # --- Inkjet Tespiti ---
            if self.enable_detection:
                processed_frame = self.detector.check(frame_bgr)
            else:
                processed_frame = frame_bgr

            # --- Qt için RGB'ye çevir ---
            frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            # PyQt6 ve PySide2 uyumluluğu için Format_RGB888
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888 if hasattr(QImage.Format, 'Format_RGB888') else QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)

            # --- Ekranda göster ---
            # Görüntüyü senin yeni video çerçevenin boyutlarına göre oranlıyoruz
            self.video_label.setPixmap(
                pix.scaled(self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
            )

            # --- Sayaçlar ---
            self.__frame_counter += 1
            self._update_perf_labels()
            self._update_status()

        except ids_peak.Exception as e:
            self.__error_counter += 1
            self._log(f"[HATA] Frame alimi: {e}")
            self._update_status()

    def closeEvent(self, event):
        self.stop_video()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ConnectCamera()
    win.show()
    sys.exit(app.exec())