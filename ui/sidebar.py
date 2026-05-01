import streamlit as st

from core.camera_registry import get_all_cameras, add_manual_camera, remove_manual_camera
from core.settings_manager import (
    get_camera_settings,
    reset_camera_settings,
    set_camera_settings,
    get_reject_settings,
    set_reject_settings,
    reset_reject_settings,
    get_manual_cameras,
)
from debug_log import log_to_system


def _setting_header(title, value_text):
    st.markdown(
        f"""
        <div class="tune-head">
            <div class="tune-label">{title}</div>
            <div class="tune-value">{value_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _is_admin():
    return st.session_state.get("admin_authenticated", False)


def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="side-workspace-title">Vision Control</div>', unsafe_allow_html=True)

        all_cameras = get_all_cameras()
        camera_names = [cam["display_name"] for cam in all_cameras]
        if not camera_names:
            st.warning("Hiç kamera bulunamadı.")
            return [], None

        st.markdown('<div class="side-block-title">Camera Source</div>', unsafe_allow_html=True)
        selected_cam_name = st.selectbox(
            "Active Camera",
            camera_names,
            key="active_camera_selector",
            label_visibility="collapsed",
        )

        selected_source = next((cam for cam in all_cameras if cam["display_name"] == selected_cam_name), all_cameras[0])
        selected_cam_key = selected_source["cam_key"]
        selected_cam_settings = get_camera_settings(selected_cam_key, reload_from_disk=True)

        admin_mode = _is_admin()
        admin_disabled = not admin_mode

        st.markdown('<div class="side-block-title" style="margin-top:16px;">Image Tuning</div>', unsafe_allow_html=True)
        st.caption("Worker bu ayarları dosyadan otomatik okuyacak.")

        with st.expander("Image Controls", expanded=False):
            _setting_header("Brightness", f"{float(selected_cam_settings['ct']):.2f}")
            ct_val = st.slider("Brightness", 0.1, 3.0, value=float(selected_cam_settings["ct"]), key=f"ct_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)
            _setting_header("Contrast", f"{int(selected_cam_settings['br'])}")
            br_val = st.slider("Contrast", -100, 100, value=int(selected_cam_settings["br"]), key=f"br_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)
            _setting_header("Sharpness", f"{float(selected_cam_settings['sh']):.2f}")
            sh_val = st.slider("Sharpness", -5.0, 5.0, value=float(selected_cam_settings["sh"]), key=f"sh_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)

        with st.expander("RGB Channels", expanded=False):
            _setting_header("Red Channel", f"{float(selected_cam_settings['r_m']):.2f}")
            r_val = st.slider("Red Channel", 0.0, 2.0, value=float(selected_cam_settings["r_m"]), key=f"r_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)
            _setting_header("Green Channel", f"{float(selected_cam_settings['g_m']):.2f}")
            g_val = st.slider("Green Channel", 0.0, 2.0, value=float(selected_cam_settings["g_m"]), key=f"g_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)
            _setting_header("Blue Channel", f"{float(selected_cam_settings['b_m']):.2f}")
            b_val = st.slider("Blue Channel", 0.0, 2.0, value=float(selected_cam_settings["b_m"]), key=f"b_slider_{selected_cam_key}", label_visibility="collapsed", disabled=admin_disabled)

        if admin_mode:
            new_settings = {"ct": ct_val, "br": br_val, "sh": sh_val, "r_m": r_val, "g_m": g_val, "b_m": b_val}
            if new_settings != selected_cam_settings:
                set_camera_settings(selected_cam_key, new_settings)
                log_to_system(f"Görüntü ayarı güncellendi: {selected_source['display_name']}", "OK", save_csv=False, show_ui=True)

        if st.button("↺ Reset Settings", use_container_width=True, disabled=admin_disabled):
            reset_camera_settings(selected_cam_key)
            log_to_system(f"Görüntü ayarları sıfırlandı: {selected_source['display_name']}", "INFO", save_csv=False, show_ui=True)
            st.rerun()

        st.markdown('<div class="side-block-title" style="margin-top:18px;">Reject Timer</div>', unsafe_allow_html=True)
        reject_settings = get_reject_settings(reload_from_disk=True)

        with st.expander("Reject Ayarları", expanded=False):
            st.metric("Gecikme", f"{reject_settings['gecikme_suresi']:.2f}s")
            yeni_gecikme = st.number_input("Gecikme Süresi (sn)", min_value=0.00, max_value=10.00, value=float(reject_settings["gecikme_suresi"]), step=0.05, key="reject_gecikme_input", disabled=admin_disabled)
            if admin_mode:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Kaydet", use_container_width=True, key="save_reject_timer_btn"):
                        set_reject_settings(yeni_gecikme)
                        log_to_system(f"Reject gecikme güncellendi | gecikme={yeni_gecikme:.2f}s", "OK", save_csv=True, show_ui=True)
                        st.success("Reject ayarı güncellendi.")
                        st.rerun()
                with col_b:
                    if st.button("↺ Sıfırla", use_container_width=True, key="reset_reject_timer_btn"):
                        reset_reject_settings()
                        log_to_system("Reject gecikme varsayılan değere sıfırlandı.", "INFO", save_csv=True, show_ui=True)
                        st.warning("Reject ayarı varsayılan değere döndürüldü.")
                        st.rerun()

        st.markdown('<div class="side-block-title" style="margin-top:18px;">Device Management</div>', unsafe_allow_html=True)
        with st.expander("＋ Add Camera", expanded=False):
            add_type = st.selectbox("Camera Type", ["IDS", "IP"], key="add_cam_type", disabled=admin_disabled)
            add_name = st.text_input("Camera Name", value="", placeholder="Örn: Dolum Hattı", key="add_cam_name", disabled=admin_disabled)
            add_ip = add_rtsp = add_full_url = ""
            if add_type == "IP":
                add_ip = st.text_input("IP Address", value="", placeholder="Örn: 192.168.8.115", key="add_cam_ip", disabled=admin_disabled)
                add_rtsp = st.text_input("RTSP Path", value="/live/1", placeholder="/live/1", key="add_cam_rtsp", disabled=admin_disabled)
                add_full_url = st.text_input("Full RTSP URL", value="", placeholder="rtsp://192.168.8.115:554/live/1", key="add_cam_full_url", disabled=admin_disabled)
            if st.button("＋ Register Camera", use_container_width=True, disabled=admin_disabled):
                try:
                    add_manual_camera(add_type, add_name, add_ip, add_rtsp, add_full_url)
                    st.success("Kamera eklendi. Worker birkaç saniye içinde görür.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        manual_cameras = get_manual_cameras(reload_from_disk=True)
        if manual_cameras:
            with st.expander("Registered Cameras", expanded=False):
                for i, cam in enumerate(manual_cameras):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.markdown(f"**{cam['name']}**")
                        st.caption(f"{cam['type'].upper()} | {cam.get('ip', '-')}")
                    with col_b:
                        if st.button("✕", key=f"del_cam_{i}", use_container_width=True, disabled=admin_disabled):
                            remove_manual_camera(i)
                            st.rerun()

        st.markdown("---")
        st.caption("Bu panel artık worker'ı başlatmaz. Worker ayrı Python süreci olarak çalışır.")
    return all_cameras, selected_source
