import cv2
from ultralytics import YOLO
from debug_log import log
import os
import time

save_dir = r"C:\Users\Hande\Desktop\inkjet\save4"
save_dir2 = r"C:\Users\Hande\Desktop\inkjet\save4_2"

class InkjetCheck:
    def __init__(self, inkjet_model_path):
        self.inkjet_model = YOLO(inkjet_model_path)
        self.threshold = 0.4
        self.save_dir = save_dir
        self.save_dir2 = save_dir2

    def check(self, frame):
        """Inkjet tespiti yapar, işlenmiş frame döner."""
        org_h, org_w = frame.shape[:2]

        # GUI performansı için küçültme
        frame_resized = cv2.resize(frame, (org_w // 4, org_h // 4))

        # ================================================================
        # GÜNCELLEME: conf, iou ve verbose parametreleri doğrudan modele eklendi.
        # iou=0.3 sayesinde üst üste binen kutulardan sadece en iyisi kalır.
        # ================================================================
        results = self.inkjet_model(frame_resized, conf=self.threshold, iou=0.3, verbose=False)[0]
        
        detected = False

        # Model zaten threshold'un altındakileri elediği için doğrudan çizebiliriz
        for box, conf in zip(results.boxes.xyxy, results.boxes.conf):
            detected = True
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_resized, f"inkjet {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Log bilgisi ve resim kaydetme işlemleri (Hiç dokunulmadı)
        if detected:
            log("Inkjet detected")

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.save_dir, f"{timestamp}.jpg")

            cv2.imwrite(filename, frame_resized)
            log(f"Frame saved: {filename}")

        else:
            log("Inkjet not found!")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.save_dir2, f"{timestamp}.jpg")

            cv2.imwrite(filename, frame_resized)
            log(f"Frame saved: {filename}")

        # GUI’ye geri gönder
        return frame_resized