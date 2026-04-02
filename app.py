import time
import hmac
import streamlit as st

from camera.streamer import (
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


# ================= PAGE CONFIG =================
st.set_page_config(
    layout="wide",
    page_title="VISION-PRO Cockpit",
    page_icon="◉",
    initial_sidebar_state="expanded"
)

apply_ids_peak_theme()
init_session_state()
ensure_camera_settings_loaded()


# ================= ADMIN AUTH =================
def init_admin_auth():
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "admin_login_error" not in st.session_state:
        st.session_state["admin_login_error"] = ""


def is_admin() -> bool:
    return st.session_state.get("admin_authenticated", False)


def check_admin_password(input_password: str) -> bool:
    real_password = st.secrets.get("admin_password", "")
    if not real_password:
        return False
    return hmac.compare_digest(str(input_password), str(real_password))


def render_admin_box():
    init_admin_auth()

    st.markdown("""
    <style>
    div[data-testid="stPopover"] > button {
        border-radius: 999px !important;
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        padding: 0 !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        background: rgba(255,255,255,0.04) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.18) !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stPopover"] > button:hover {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        transform: translateY(-1px);
    }

    .admin-pop-title {
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .admin-pop-sub {
        font-size: 12px;
        opacity: 0.72;
        margin-bottom: 10px;
    }

    .admin-status-ok {
        background: rgba(34, 197, 94, 0.14);
        color: #86efac;
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 12px;
        margin-bottom: 10px;
    }

    .admin-status-bad {
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 12px;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .admin-help {
        font-size: 11px;
        opacity: 0.65;
        margin-top: 8px;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)

    _, admin_col = st.columns([9.55, 0.45])

    with admin_col:
        icon_label = "🟢👤" if is_admin() else "👤"

        with st.popover(icon_label, use_container_width=False):
            st.markdown('<div class="admin-pop-title">Admin Paneli</div>', unsafe_allow_html=True)

            if is_admin():
                st.markdown(
                    '<div class="admin-status-ok">Yetkili oturum açık.</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="admin-pop-sub">Kamera ayarları ve yönetim işlemleri aktif.</div>',
                    unsafe_allow_html=True
                )

                if st.button("Çıkış Yap", use_container_width=True, key="admin_logout_btn"):
                    st.session_state["admin_authenticated"] = False
                    st.session_state["admin_login_error"] = ""
                    st.rerun()

            else:
                st.markdown(
                    '<div class="admin-pop-sub">Yönetim işlemleri için şifre girin.</div>',
                    unsafe_allow_html=True
                )

                with st.form("admin_login_form", clear_on_submit=True):
                    password = st.text_input(
                        "Şifre",
                        type="password",
                        placeholder="Admin şifresi"
                    )

                    submitted = st.form_submit_button("Giriş Yap", use_container_width=True)

                    if submitted:
                        if check_admin_password(password):
                            st.session_state["admin_authenticated"] = True
                            st.session_state["admin_login_error"] = ""
                            st.rerun()
                        else:
                            st.session_state["admin_login_error"] = "Şifre hatalı"

                if st.session_state.get("admin_login_error"):
                    st.markdown(
                        f'<div class="admin-status-bad">{st.session_state["admin_login_error"]}</div>',
                        unsafe_allow_html=True
                    )

                st.markdown(
                    '<div class="admin-help">Admin olmadan yalnızca izleme ve stream kontrolü kullanılabilir.</div>',
                    unsafe_allow_html=True
                )


# ================= AUTO START =================
def auto_start_selected_camera(selected_source):
    current_cam_key = selected_source["cam_key"]
    last_cam_key = st.session_state.get("last_auto_started_cam_key")
    stream_paused = st.session_state.get("stream_paused", False)

    # Stop sonrası aynı kamerayı yeniden otomatik başlatma
    if stream_paused and last_cam_key == current_cam_key:
        return

    # Kamera değiştiyse tekrar auto-start izni ver
    if last_cam_key != current_cam_key:
        st.session_state["stream_paused"] = False

        stop_all_streamers()

        s = get_or_create_streamer(current_cam_key)
        s.img_settings.update(get_camera_settings(current_cam_key))
        success = s.start(selected_source)

        st.session_state["last_auto_started_cam_key"] = current_cam_key

        if success:
            access_mode = getattr(s, "access_mode", None)

            if selected_source.get("type") == "ids":
                if access_mode == "control":
                    msg = f"Kamera otomatik başlatıldı: {selected_source['display_name']} | access=control"
                elif access_mode == "readonly":
                    msg = f"Kamera otomatik başlatıldı: {selected_source['display_name']} | access=readonly"
                else:
                    msg = f"Kamera otomatik başlatıldı: {selected_source['display_name']}"
            else:
                msg = f"Kamera otomatik başlatıldı: {selected_source['display_name']}"

            log_to_system(msg, "OK", save_csv=False, show_ui=True)
        else:
            err = getattr(s, "last_error", "Bilinmeyen hata")
            log_to_system(
                f"Kamera başlatılamadı: {selected_source['display_name']} | {err}",
                "HATA",
                save_csv=True,
                show_ui=True
            )
            st.error("Seçilen kamera başlatılamadı.")


# ================= INITIAL STATE =================
if "last_cset_export" not in st.session_state:
    st.session_state["last_cset_export"] = None

if "last_auto_started_cam_key" not in st.session_state:
    st.session_state["last_auto_started_cam_key"] = None

if "stream_paused" not in st.session_state:
    st.session_state["stream_paused"] = False


# ================= HEADER =================
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

render_admin_box()


# ================= SIDEBAR / SOURCES =================
all_cameras, selected_source = render_sidebar()

auto_start_selected_camera(selected_source)
streamers = get_streamers()

render_top_metrics(selected_source, streamers)

left_col, center_col, right_col = render_live_area()


# ================= RIGHT PANEL =================
with right_col:
    current_cam_key = selected_source["cam_key"]
    active_streamer = get_streamer(current_cam_key)
    is_running = active_streamer.running if active_streamer else False

    if st.button(
        "▶ Start Stream",
        use_container_width=True,
        key="start_btn",
        disabled=is_running
    ):
        s = get_or_create_streamer(current_cam_key)
        s.img_settings.update(get_camera_settings(current_cam_key))
        success = s.start(selected_source)

        if success:
            st.session_state["stream_paused"] = False
            st.session_state["last_auto_started_cam_key"] = current_cam_key
            log_to_system(
                f"Yayın başlatıldı: {selected_source['display_name']}",
                "OK",
                save_csv=False,
                show_ui=True
            )
        else:
            err = getattr(s, "last_error", "Bilinmeyen hata")
            log_to_system(
                f"Kamera başlatılamadı: {selected_source['display_name']} | {err}",
                "HATA",
                save_csv=True,
                show_ui=True
            )
            st.error("Seçilen kamera başlatılamadı.")

        st.rerun()

    if st.button(
        "■ Stop Stream",
        use_container_width=True,
        key="stop_btn",
        disabled=not is_running
    ):
        stop_all_streamers()
        st.session_state["last_cset_export"] = None
        st.session_state["stream_paused"] = True
        log_to_system(
            f"Yayın durduruldu: {selected_source['display_name']}",
            "INFO",
            save_csv=False,
            show_ui=True
        )
        st.rerun()

    st.markdown("---")

    ids_admin_disabled = not is_admin()

    if selected_source.get("type") == "ids":
        if st.button(
            "💾 IDS .cset oluştur",
            use_container_width=True,
            key="create_cset_btn",
            disabled=ids_admin_disabled
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
                on_click="ignore",
                disabled=ids_admin_disabled
            )

        if not is_admin():
            st.caption("Bu bölüm görünür ama sadece admin kullanabilir.")
    else:
        st.caption("CSET export sadece IDS kameralar için kullanılabilir.")

    render_right_report_panel()


# ================= MAIN =================
st.markdown('<div class="ids-section-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ids-panel-title">System Terminal</div>', unsafe_allow_html=True)
log_container = st.empty()

render_center_view(
    center_col=center_col,
    selected_source=selected_source,
    log_container=log_container
)