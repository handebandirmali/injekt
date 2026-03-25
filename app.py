import time
import streamlit as st

from camera.streamer import (
    apply_settings_to_streamer,
    get_or_create_streamer,
    get_streamer,
    get_streamers,
    stop_all_streamers,
)
from core.ids_cset_manager import (
    IdsCsetExportError,
    export_ids_camera_to_cset,
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

if "last_cset_export" not in st.session_state:
    st.session_state["last_cset_export"] = None

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
    if st.button("▶ Start", type="primary", use_container_width=True, key="start_btn"):
        stop_all_streamers()

        s = get_or_create_streamer(selected_source["cam_key"])
        s.img_settings.update(get_camera_settings(selected_source["cam_key"]))
        success = s.start(selected_source)

        if success:
            access_mode = getattr(s, "access_mode", None)

            if selected_source.get("type") == "ids":
                if access_mode == "control":
                    msg = f"Kamera başlatıldı: {selected_source['display_name']} | access=control"
                elif access_mode == "readonly":
                    msg = f"Kamera başlatıldı: {selected_source['display_name']} | access=readonly"
                else:
                    msg = f"Kamera başlatıldı: {selected_source['display_name']}"
            else:
                msg = f"Kamera başlatıldı: {selected_source['display_name']}"

            log_to_system(msg, "OK", save_csv=True, show_ui=True)
            st.success(msg)
            st.rerun()
        else:
            err = getattr(s, "last_error", "Bilinmeyen hata")
            log_to_system(
                f"Kamera başlatılamadı: {selected_source['display_name']} | {err}",
                "HATA",
                save_csv=True,
                show_ui=True
            )
            st.error("Seçilen kamera başlatılamadı.")

    if st.button("■ Stop", use_container_width=True, key="stop_btn"):
        stop_all_streamers()
        st.session_state["last_cset_export"] = None
        log_to_system(
            "Tüm kameralar durduruldu.",
            "INFO",
            save_csv=False,
            show_ui=True
        )
        st.rerun()

    if st.button("↻ Restart", use_container_width=True, key="restart_btn"):
        reset_camera_settings(selected_source["cam_key"])
        apply_settings_to_streamer(selected_source["cam_key"])
        st.session_state["last_cset_export"] = None
        log_to_system(
            f"Görüntü ayarları sıfırlandı: {selected_source['display_name']}",
            "INFO",
            save_csv=False,
            show_ui=True
        )
        st.rerun()

    st.markdown("---")

    if selected_source.get("type") == "ids":
        if st.button(
            "💾 IDS .cset oluştur",
            use_container_width=True,
            key="create_cset_btn"
        ):
            try:
                active_streamer = get_streamer(selected_source["cam_key"])
                if active_streamer is not None and active_streamer.running:
                    active_streamer.stop()
                    time.sleep(0.3)

                result = export_ids_camera_to_cset(selected_source)
                st.session_state["last_cset_export"] = result

                meta = result.get("meta", {})
                api_name = meta.get("api_name", "Bilinmeyen API")
                signature = meta.get("signature", "")

                log_to_system(
                    f".cset oluşturuldu: {result['filename']} | API: {api_name} | {signature}",
                    "OK",
                    save_csv=True,
                    show_ui=True
                )

            except IdsCsetExportError as e:
                st.session_state["last_cset_export"] = None
                log_to_system(
                    f".cset export hatası: {str(e)}",
                    "HATA",
                    save_csv=True,
                    show_ui=True
                )
                st.error(str(e))

            except Exception as e:
                st.session_state["last_cset_export"] = None
                log_to_system(
                    f"Beklenmeyen .cset hatası: {str(e)}",
                    "HATA",
                    save_csv=True,
                    show_ui=True
                )
                st.error(f"Beklenmeyen hata: {e}")

        last_cset = st.session_state.get("last_cset_export", None)
        if last_cset is not None:
            st.download_button(
                label="⬇️ Son oluşturulan .cset indir",
                data=last_cset["bytes"],
                file_name=last_cset["filename"],
                mime="application/octet-stream",
                use_container_width=True,
                key="download_cset_btn",
                on_click="ignore"
            )
    else:
        st.caption("CSET export sadece IDS kameralar için kullanılabilir.")

    render_right_report_panel()

st.markdown('<div class="ids-section-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ids-panel-title">System Terminal</div>', unsafe_allow_html=True)
log_container = st.empty()

render_center_view(
    center_col=center_col,
    selected_source=selected_source,
    log_container=log_container
)