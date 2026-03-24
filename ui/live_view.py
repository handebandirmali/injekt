import os
import time

import numpy as np
import pandas as pd
import streamlit as st

from camera.streamer import any_camera_running, get_or_create_streamer, total_fps
from config import CSV_FILE_PATH


def render_top_metrics(selected_source, streamers):
    selected_ip_text = selected_source.get("ip", "-")
    running_count = sum(1 for s in streamers.values() if s.running)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cihaz", selected_source["display_name"])
    m2.metric("Durum", "Online" if any_camera_running() else "Offline", delta=f"{running_count} Aktif")
    m3.metric("Toplam FPS", f"{total_fps():.1f}")
    m4.metric("Kamera IP", selected_ip_text)


def render_right_report_panel():
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


def render_terminal(log_container):
    try:
        logs = st.session_state.ui_logs[-8:]
        html_logs = "".join([f"<div>{l}</div>" for l in logs[::-1]])
        log_container.markdown(
            f"<div class='terminal-log'>{html_logs}</div>",
            unsafe_allow_html=True
        )
    except:
        pass


def render_single_offline():
    info = st.empty()
    box = st.empty()

    info.caption("Durum: Offline | FPS: 0.0")
    box.image(
        np.zeros((450, 800, 3), dtype=np.uint8),
        caption="Kamera Kapalı",
        use_container_width=True
    )


def render_grid_offline(selected_grid_cameras):
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


def render_single_live(selected_source, log_container):
    single_info = st.empty()
    single_box = st.empty()

    while any_camera_running():
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

        render_terminal(log_container)
        time.sleep(0.03)


def render_grid_live(selected_grid_cameras, log_container):
    cols_per_row = 2

    while any_camera_running():
        grid_boxes = []

        for i in range(0, len(selected_grid_cameras), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                cam_index = i + j
                if cam_index < len(selected_grid_cameras):
                    cam = selected_grid_cameras[cam_index]
                    with cols[j]:
                        st.markdown(f"**{cam['display_name']}**")
                        info = st.empty()
                        box = st.empty()
                        grid_boxes.append((cam, box, info))

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

        render_terminal(log_container)
        time.sleep(0.03)


def render_live_area(view_mode, selected_source, selected_grid_cameras):
    st.divider()

    left_col, center_col, right_col = st.columns([1, 4, 1])

    return left_col, center_col, right_col


def render_center_view(center_col, view_mode, selected_source, selected_grid_cameras, log_container):
    with center_col:
        if any_camera_running():
            if view_mode == "Tekli Odak":
                render_single_live(selected_source, log_container)
            else:
                render_grid_live(selected_grid_cameras, log_container)
        else:
            if view_mode == "Tekli Odak":
                render_single_offline()
            else:
                render_grid_offline(selected_grid_cameras)