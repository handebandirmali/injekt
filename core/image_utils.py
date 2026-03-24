import cv2
import numpy as np


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