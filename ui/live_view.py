import os
import time

<<<<<<< HEAD
import streamlit as st

from config import CSV_FILE_PATH
from core.runtime_state import load_runtime_state
from debug_log import read_recent_logs


def _status_summary(runtime_state):
    service = runtime_state.get("service", {})
    cameras = runtime_state.get("cameras", {})
    running_count = sum(1 for item in cameras.values() if item.get("running"))
    total_fps = sum(float(item.get("fps", 0.0) or 0.0) for item in cameras.values() if item.get("running"))
    return service, cameras, running_count, total_fps


def render_top_metrics(selected_source, streamers=None):
    runtime_state = load_runtime_state()
    service, cameras, running_count, total_fps = _status_summary(runtime_state)
    selected = cameras.get(selected_source["cam_key"], {})

    status_text = "ONLINE" if service.get("running") else "OFFLINE"
    ip_text = selected.get("ip") or selected_source.get("ip", "-")
    cam_text = selected.get("display_name") or selected_source.get("display_name")
=======
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
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d

    st.markdown(f"""
    <div class="ids-metric-bar">
        <div class="ids-metric">
            <div class="ids-metric-k">Active Device</div>
            <div class="ids-metric-v">{cam_text}</div>
        </div>
        <div class="ids-metric">
<<<<<<< HEAD
            <div class="ids-metric-k">Worker Status</div>
=======
            <div class="ids-metric-k">System Status</div>
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
            <div class="ids-metric-v">{status_text} ({running_count})</div>
        </div>
        <div class="ids-metric">
            <div class="ids-metric-k">Total FPS</div>
<<<<<<< HEAD
            <div class="ids-metric-v">{total_fps:.1f}</div>
=======
            <div class="ids-metric-v">{fps_text}</div>
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
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
<<<<<<< HEAD
                use_container_width=True,
=======
                use_container_width=True
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
            )


def render_terminal(log_container):
<<<<<<< HEAD
    logs = read_recent_logs(limit=8)
    html_logs = "".join([f"<div>{l}</div>" for l in logs[::-1]])
    log_container.markdown(
        f"<div class='terminal-log'>{html_logs}</div>",
        unsafe_allow_html=True,
    )


def _render_offline_html(selected_source, service_running=False, err_text=None):
    """Offline kartı için HTML string döner — container.markdown() ile kullanılır."""
    subtitle = "Worker açık değil" if not service_running else "Kamera kapalı / frame yok"
    if err_text:
        subtitle = err_text[:180]
    return f"""
    <div class="ids-preview-card">
        <div class="ids-preview-topbar">
            <div class="ids-preview-label">{selected_source['display_name']}</div>
            <div class="ids-preview-meta">Offline / No active frame</div>
        </div>
        <div class="ids-empty-state">
            <div class="ids-empty-title">Görüntü Yok</div>
            <div class="ids-empty-subtitle">{subtitle}</div>
        </div>
    </div>
    """


def render_single_live(selected_source, log_container):
    shell    = st.empty()
    img_box  = st.empty()
    info_box = st.empty()

    while True:
        runtime_state = load_runtime_state()
        service, cameras, _, _ = _status_summary(runtime_state)
        selected_status = cameras.get(selected_source["cam_key"], {})

        is_running = bool(selected_status.get("running"))
        fps        = float(selected_status.get("fps", 0.0) or 0.0)
        frame_path = selected_status.get("frame_path")
        detected   = selected_status.get("detected")
        err_text   = selected_status.get("last_error")
=======
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
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d

        shell.markdown(f"""
        <div class="ids-preview-shell">
            <div class="ids-preview-topbar">
                <div class="ids-preview-label">{selected_source['display_name']}</div>
                <div class="ids-preview-meta">{'Online' if is_running else 'Offline'} / {fps:.1f} FPS</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

<<<<<<< HEAD
        if frame_path and os.path.exists(frame_path):
            img_box.image(frame_path, use_container_width=True)
        else:
            # img_box placeholder'ına yaz — sayfaya ekleme yapmaz, üzerine yazar
            img_box.markdown(
                _render_offline_html(
                    selected_source,
                    service_running=service.get("running", False),
                    err_text=err_text,
                ),
                unsafe_allow_html=True,
            )

    

        render_terminal(log_container)
        time.sleep(0.40)
=======
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
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d


def render_live_area():
    left_col, center_col, right_col = st.columns([1.2, 4.8, 1.3])
    return left_col, center_col, right_col


def render_center_view(center_col, selected_source, log_container):
    with center_col:
<<<<<<< HEAD
        render_single_live(selected_source, log_container)
=======
        if any_camera_running():
            render_single_live(selected_source, log_container)
        else:
            render_single_offline(selected_source)
>>>>>>> e676ff9672229d0236498e41b759b39286e1c50d
