import os
import signal
import sys
import time
from datetime import datetime

from camera.streamer import get_or_create_streamer, get_streamers, stop_all_streamers
from core.camera_registry import get_all_cameras
from core.runtime_state import flush_runtime_state, set_service_running, update_service_heartbeat
from debug_log import log_to_system


def start_missing_cameras():
    all_cameras = get_all_cameras()
    streamers = get_streamers()
    active_keys = set()

    for cam in all_cameras:
        cam_key = cam["cam_key"]
        active_keys.add(cam_key)
        streamer = streamers.get(cam_key)

        if streamer is not None and streamer.running and streamer.is_alive():
            continue

        if streamer is not None and not streamer.running:
            try:
                streamer.stop()
            except Exception:
                pass

        streamer = get_or_create_streamer(cam_key)
        success = streamer.start(cam)
        if success:
            log_to_system(
                f"Background worker kamera başlattı: {cam['display_name']}",
                "OK", save_csv=True, show_ui=False
            )
        else:
            err = getattr(streamer, "last_error", "Bilinmeyen hata")
            log_to_system(
                f"Background worker kamera başlatamadı: {cam['display_name']} | {err}",
                "HATA", save_csv=True, show_ui=False
            )

    for cam_key, streamer in list(streamers.items()):
        if cam_key not in active_keys:
            try:
                streamer.stop()
            except Exception:
                pass
            del streamers[cam_key]
            log_to_system(
                f"Kamera listeden kaldırıldı, worker durdurdu: {cam_key}",
                "INFO", save_csv=True, show_ui=False
            )


def shutdown_handler(signum=None, frame=None):
    log_to_system("Background worker kapanıyor.", "INFO", save_csv=True, show_ui=False)
    stop_all_streamers()
    set_service_running(False, pid=os.getpid())
    flush_runtime_state(force=True)
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown_handler)
    try:
        signal.signal(signal.SIGTERM, shutdown_handler)
    except Exception:
        pass

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_service_running(True, started_at=started_at, pid=os.getpid())
    log_to_system("Background worker başlatıldı.", "OK", save_csv=True, show_ui=False)

    while True:
        start_missing_cameras()
        update_service_heartbeat()
        flush_runtime_state(force=False)
        time.sleep(3.0)


if __name__ == "__main__":
    main()