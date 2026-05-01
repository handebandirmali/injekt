import cv2
from ultralytics import YOLO
from debug_log import log
import os
import time

save_dir = r"C:\Users\Hande\Desktop\inkjet\save4"
save_dir2 = r"C:\Users\Hande\Desktop\inkjet\save4_2"

os.makedirs(save_dir, exist_ok=True)
os.makedirs(save_dir2, exist_ok=True)


class InkjetCheck:
    def __init__(self, inkjet_model_path):
        self.inkjet_model = YOLO(inkjet_model_path)
        self.threshold = 0.4
        self.save_dir = save_dir
        self.save_dir2 = save_dir2

        
        self.last_status = None          # "detected" / "not_found"
        self.last_save_time = 0
        self.min_save_interval = 10      # aynı olaylar arasında en az 3 sn bekle

    def _should_save_and_log(self, current_status):
        now = time.time()

        # Durum değiştiyse kaydet/logla
        if current_status != self.last_status:
            self.last_status = current_status
            self.last_save_time = now
            return True

       
        if now - self.last_save_time >= self.min_save_interval:
            self.last_save_time = now
            return True

        return False

    def _generate_filename(self, folder):
     
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ms = int((time.time() % 1) * 1000)
        return os.path.join(folder, f"{timestamp}_{ms:03d}.jpg")

    def check(self, frame):
        """Inkjet tespiti yapar, işlenmiş frame döner."""
        org_h, org_w = frame.shape[:2]

      
        new_w = max(org_w // 4, 1)
        new_h = max(org_h // 4, 1)
        frame_resized = cv2.resize(frame, (new_w, new_h))

        results = self.inkjet_model(
            frame_resized,
            conf=self.threshold,
            iou=0.3,
            verbose=False
        )[0]

        detected = False

        for box, conf in zip(results.boxes.xyxy, results.boxes.conf):
            detected = True
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame_resized,
                f"inkjet {conf:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )

        current_status = "detected" if detected else "not_found"

        if self._should_save_and_log(current_status):
            if detected:
                log("Inkjet detected")
                filename = self._generate_filename(self.save_dir)
                cv2.imwrite(filename, frame_resized)
                log(f"Frame saved: {filename}")
            else:
                log("Inkjet not found!")
                filename = self._generate_filename(self.save_dir2)
                cv2.imwrite(filename, frame_resized)
                log(f"Frame saved: {filename}")

        return frame_resized