import os
import time

import pandas as pd
import streamlit as st

from camera.streamer import any_camera_running, get_or_create_streamer, total_fps
from config import CSV_FILE_PATH


def render_top_metrics(selected_source, streamers):
    selected_ip_text = selected_source.get("ip", "-")
    running_count = sum(1 for s in streamers.values() if s.running)

    status_text = "ONLINE" if any_camera_running() else "OFFLINE"
    fps_text = f"{total_fps():.1f}"
    cam_text = selected_source["display_name"]
    ip_text = selected_ip_text

    st.markdown(f"""
    <div class="ids-metric-bar">
        <div class="ids-metric">
            <div class="ids-metric-k">Active Device</div>
            <div class="ids-metric-v">{cam_text}</div>
        </div>
        <div class="ids-metric">
            <div class="ids-metric-k">System Status</div>
            <div class="ids-metric-v">{status_text} ({running_count})</div>
        </div>
        <div class="ids-metric">
            <div class="ids-metric-k">Total FPS</div>
            <div class="ids-metric-v">{fps_text}</div>
        </div>
        <div class="ids-metric">
            <div class="ids-metric-k">Connection</div>
            <div class="ids-metric-v">{ip_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_right_report_panel():
    if os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, "rb") as f:
            st.download_button(
                "Export CSV",
                f,
                "rapor.csv",
                "text/csv",
                use_container_width=True
            )


def render_terminal(log_container):
    try:
        logs = st.session_state.ui_logs[-8:]
        html_logs = "".join([f"<div>{l}</div>" for l in logs[::-1]])
        log_container.markdown(
            f"<div class='terminal-log'>{html_logs}</div>",
            unsafe_allow_html=True
        )
    except Exception:
        pass


def render_single_offline(selected_source):
    st.markdown(f"""
    <div class="ids-preview-card">
        <div class="ids-preview-topbar">
            <div class="ids-preview-label">{selected_source['display_name']}</div>
            <div class="ids-preview-meta">Offline / No active stream</div>
        </div>
        <div class="ids-empty-state">
            <div class="ids-empty-title">Kamera Kapalı</div>
            <div class="ids-empty-subtitle">Görüntü akışı başlatıldığında burada canlı yayın görünecek.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_single_live(selected_source, log_container):
    shell = st.empty()
    img_box = st.empty()

    while any_camera_running():
        selected_streamer = get_or_create_streamer(selected_source["cam_key"])
        with selected_streamer.lock:
            frame = selected_streamer.latest_frame
            fps = selected_streamer.current_fps
            is_running = selected_streamer.running

        shell.markdown(f"""
        <div class="ids-preview-shell">
            <div class="ids-preview-topbar">
                <div class="ids-preview-label">{selected_source['display_name']}</div>
                <div class="ids-preview-meta">{'Online' if is_running else 'Offline'} / {fps:.1f} FPS</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if frame is not None:
            img_box.image(frame, channels="RGB", use_container_width=True)
        else:
            img_box.markdown("""
            <div class="ids-preview-card">
                <div class="ids-empty-state">
                    <div class="ids-empty-title">Görüntü Bekleniyor</div>
                    <div class="ids-empty-subtitle">Kamera açık ama henüz frame gelmedi.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        render_terminal(log_container)
        time.sleep(0.03)


def render_live_area():
    left_col, center_col, right_col = st.columns([1.2, 4.8, 1.3])
    return left_col, center_col, right_col


def render_center_view(center_col, selected_source, log_container):
    with center_col:
        if any_camera_running():
            render_single_live(selected_source, log_container)
        else:
            render_single_offline(selected_source)