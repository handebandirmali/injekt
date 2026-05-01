import hmac
import streamlit as st

from core.runtime_state import load_runtime_state
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
    initial_sidebar_state="expanded",
)

apply_ids_peak_theme()
init_session_state()


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
    _, admin_col = st.columns([9.55, 0.45])
    with admin_col:
        icon_label = "🟢👤" if is_admin() else "👤"
        with st.popover(icon_label, use_container_width=False):
            st.markdown('<div class="admin-pop-title">Admin Paneli</div>', unsafe_allow_html=True)
            if is_admin():
                st.markdown('<div class="admin-status-ok">Yetkili oturum açık.</div>', unsafe_allow_html=True)
                if st.button("Çıkış Yap", use_container_width=True, key="admin_logout_btn"):
                    st.session_state["admin_authenticated"] = False
                    st.session_state["admin_login_error"] = ""
                    st.rerun()
            else:
                with st.form("admin_login_form", clear_on_submit=True):
                    password = st.text_input("Şifre", type="password", placeholder="Admin şifresi")
                    submitted = st.form_submit_button("Giriş Yap", use_container_width=True)
                    if submitted:
                        if check_admin_password(password):
                            st.session_state["admin_authenticated"] = True
                            st.session_state["admin_login_error"] = ""
                            st.rerun()
                        else:
                            st.session_state["admin_login_error"] = "Şifre hatalı"
                if st.session_state.get("admin_login_error"):
                    st.markdown(f'<div class="admin-status-bad">{st.session_state["admin_login_error"]}</div>', unsafe_allow_html=True)
                st.markdown('<div class="admin-help">Admin olmadan yalnızca izleme ve rapor alanı kullanılabilir.</div>', unsafe_allow_html=True)


st.markdown("""
<div class="ids-toolbar">
    <div class="ids-toolbar-left">
        <div class="ids-logo-badge"></div>
        <div><div class="ids-title">VISION-PRO Cockpit</div></div>
    </div>
    <div class="ids-chip-row">
        <div class="ids-chip ids-chip-accent">Background Inspection</div>
    </div>
</div>
""", unsafe_allow_html=True)

render_admin_box()
all_cameras, selected_source = render_sidebar()

if not selected_source:
    st.stop()

render_top_metrics(selected_source, streamers=None)
left_col, center_col, right_col = render_live_area()

with right_col:
    runtime = load_runtime_state()
    service = runtime.get("service", {})

    st.markdown("---")
    render_right_report_panel()


st.markdown('<div class="ids-section-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="ids-panel-title">System Terminal</div>', unsafe_allow_html=True)
log_container = st.empty()
render_center_view(center_col=center_col, selected_source=selected_source, log_container=log_container)
