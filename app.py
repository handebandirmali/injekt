import streamlit as st

from camera.streamer import (
    any_camera_running,
    apply_settings_to_streamer,
    get_or_create_streamer,
    get_streamers,
    stop_all_streamers,
    stop_unselected_streamers,
)
from debug_log import log_to_system
from core.settings_manager import ensure_camera_settings_loaded, get_camera_settings, reset_camera_settings
from state import init_session_state
from ui.live_view import (
    render_center_view,
    render_live_area,
    render_right_report_panel,
    render_top_metrics,
)
from ui.sidebar import render_sidebar


st.set_page_config(layout="wide", page_title="VISION-PRO V3.0", page_icon="👁️")

st.markdown("""
<style>
.main { background-color: #0e1117; }

div.stButton > button {
    border-radius: 5px;
    height: 45px;
    font-weight: bold;
}

.stMetric {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 10px;
    border-radius: 10px;
}

.terminal-log {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: monospace;
    padding: 10px;
    border-radius: 5px;
    height: 200px;
    overflow-y: auto;
    border: 1px solid #30363d;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

init_session_state()
ensure_camera_settings_loaded()

view_mode, all_cameras, selected_source = render_sidebar()
streamers = get_streamers()

selected_grid_cameras = [
    cam for cam in all_cameras
    if cam["display_name"] in st.session_state.grid_selected_cameras
]

if not selected_grid_cameras and all_cameras:
    selected_grid_cameras = all_cameras[:1]

render_top_metrics(selected_source, streamers)

left_col, center_col, right_col = render_live_area(
    view_mode,
    selected_source,
    selected_grid_cameras
)

with left_col:
    st.write("### 🎮 Akış")

    if st.button("▶ Başlat", type="primary", use_container_width=True):
        if view_mode == "Tekli Odak":
            stop_all_streamers()
            s = get_or_create_streamer(selected_source["cam_key"])
            s.img_settings.update(get_camera_settings(selected_source["cam_key"]))
            success = s.start(selected_source)

            if success:
                log_to_system(
                    f"Kamera başlatıldı: {selected_source['display_name']}",
                    "OK",
                    save_csv=True,
                    show_ui=True
                )
            else:
                log_to_system(
                    f"Kamera başlatılamadı: {selected_source['display_name']}",
                    "HATA",
                    save_csv=True,
                    show_ui=True
                )
                st.error("Seçilen kamera başlatılamadı.")
        else:
            selected_keys = [cam["cam_key"] for cam in selected_grid_cameras]
            stop_unselected_streamers(selected_keys)

            started_any = False
            for cam in selected_grid_cameras:
                s = get_or_create_streamer(cam["cam_key"])
                s.img_settings.update(get_camera_settings(cam["cam_key"]))
                ok = s.start(cam)
                if ok:
                    started_any = True
                    log_to_system(
                        f"Kamera başlatıldı: {cam['display_name']}",
                        "OK",
                        save_csv=True,
                        show_ui=True
                    )

            if not started_any:
                log_to_system(
                    "Seçili grid kameraları başlatılamadı.",
                    "HATA",
                    save_csv=True,
                    show_ui=True
                )
                st.error("Seçili grid kameraları başlatılamadı.")

        st.rerun()

    if st.button("■ Durdur", use_container_width=True):
        stop_all_streamers()
        log_to_system("Tüm kameralar durduruldu.", "INFO", save_csv=False, show_ui=True)
        st.rerun()

    if st.button("↺ Sıfırla", use_container_width=True):
        reset_camera_settings(selected_source["cam_key"])
        apply_settings_to_streamer(selected_source["cam_key"])
        log_to_system(
            f"Görüntü ayarları sıfırlandı: {selected_source['display_name']}",
            "INFO",
            save_csv=False,
            show_ui=True
        )
        st.rerun()

with right_col:
    render_right_report_panel()

st.divider()
st.write("### 📝 Sistem Terminali")
log_container = st.empty()

render_center_view(
    center_col=center_col,
    view_mode=view_mode,
    selected_source=selected_source,
    selected_grid_cameras=selected_grid_cameras,
    log_container=log_container
)