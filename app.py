import streamlit as st

from camera.streamer import (
    apply_settings_to_streamer,
    get_or_create_streamer,
    get_streamers,
    stop_all_streamers,
)
from debug_log import log_to_system
from core.settings_manager import (
    ensure_camera_settings_loaded,
    get_camera_settings,
    reset_camera_settings,
)
from state import init_session_state
from ui.live_view import (
    render_center_view,
    render_live_area,
    render_right_report_panel,
    render_top_metrics,
)
from ui.sidebar import render_sidebar
from ui.theme import apply_ids_peak_theme


st.set_page_config(
    layout="wide",
    page_title="VISION-PRO Cockpit",
    page_icon="◉",
    initial_sidebar_state="expanded"
)

apply_ids_peak_theme()
init_session_state()
ensure_camera_settings_loaded()

st.markdown("""
<div class="ids-toolbar">
    <div class="ids-toolbar-left">
        <div class="ids-logo-badge"></div>
        <div>
            <div class="ids-title">VISION-PRO Cockpit</div>
        </div>
    </div>
    <div class="ids-chip-row">
        <div class="ids-chip ids-chip-accent">Live Inspection</div>
    </div>
</div>
""", unsafe_allow_html=True)

all_cameras, selected_source = render_sidebar()
streamers = get_streamers()

render_top_metrics(selected_source, streamers)

left_col, center_col, right_col = render_live_area()

with right_col:
    if st.button("▶ Start ", type="primary", use_container_width=True):
        stop_all_streamers()
        s = get_or_create_streamer(selected_source["cam_key"])
        s.img_settings.update(get_camera_settings(selected_source["cam_key"]))
        success = s.start(selected_source)

        if success:
            log_to_system(
                f"Kamera baslatildi: {selected_source['display_name']}",
                "OK",
                save_csv=True,
                show_ui=True
            )
        else:
            log_to_system(
                f"Kamera baslatilamadi: {selected_source['display_name']}",
                "HATA",
                save_csv=True,
                show_ui=True
            )
            st.error("Seçilen kamera baslatilamadi.")

        st.rerun()

    if st.button("■ Stop ", use_container_width=True):
        stop_all_streamers()
        log_to_system("Tüm kameralar durduruldu.", "INFO", save_csv=False, show_ui=True)
        st.rerun()

    if st.button("↻ Restart ", use_container_width=True):
        reset_camera_settings(selected_source["cam_key"])
        apply_settings_to_streamer(selected_source["cam_key"])
        log_to_system(
            f"Görüntü ayarları sıfırlandı: {selected_source['display_name']}",
            "INFO",
            save_csv=False,
            show_ui=True
        )
        st.rerun()

    render_right_report_panel()

st.markdown('<div class="ids-section-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ids-panel-title">System Terminal</div>', unsafe_allow_html=True)
log_container = st.empty()

render_center_view(
    center_col=center_col,
    selected_source=selected_source,
    log_container=log_container
)