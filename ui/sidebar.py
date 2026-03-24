import streamlit as st

from camera.streamer import apply_settings_to_streamer, get_streamers
from core.camera_registry import get_all_cameras, add_manual_camera, remove_manual_camera
from debug_log import log_to_system
from core.settings_manager import (
    get_camera_settings,
    reset_camera_settings,
    save_camera_settings_to_disk,
    set_camera_settings,
)


def render_sidebar():
    with st.sidebar:
        st.title("⚙️ Kontrol Merkezi")
        view_mode = st.radio("Düzen Seçin", ["Tekli Odak", "Izgara (Grid)"], horizontal=True)

        st.divider()

        all_cameras = get_all_cameras()
        camera_names = [cam["display_name"] for cam in all_cameras]

        if view_mode == "Izgara (Grid)":
            st.subheader("🧩 Grid Kamera Seçimi")

            default_grid_selection = st.session_state.grid_selected_cameras
            valid_names = [name for name in default_grid_selection if name in camera_names]

            selected_grid_camera_names = st.multiselect(
                "Grid modunda açılacak kameralar",
                options=camera_names,
                default=valid_names if valid_names else camera_names[:2],
                key="grid_camera_selector"
            )

            st.session_state.grid_selected_cameras = selected_grid_camera_names
            st.divider()

        with st.expander("➕ Kamera Ekle", expanded=False):
            add_type = st.selectbox("Kamera Türü", ["IDS", "IP"], key="add_cam_type")
            add_name = st.text_input(
                "Kamera Adı",
                value="",
                placeholder="Örn: Dolum Hattı",
                key="add_cam_name"
            )

            add_ip = ""
            add_rtsp = ""
            add_full_url = ""

            if add_type == "IP":
                add_ip = st.text_input(
                    "IP Adresi",
                    value="",
                    placeholder="Örn: 192.168.8.115",
                    key="add_cam_ip"
                )
                add_rtsp = st.text_input(
                    "RTSP Yolu",
                    value="/live/0",
                    placeholder="/live/0",
                    key="add_cam_rtsp"
                )
                add_full_url = st.text_input(
                    "Tam RTSP URL (istersen direkt bunu kullan)",
                    value="",
                    placeholder="Örn: rtsp://192.168.8.115:554/live/0",
                    key="add_cam_full_url"
                )

            if st.button("Kamera Ekle", use_container_width=True):
                try:
                    add_manual_camera(
                        camera_type=add_type,
                        custom_name=add_name,
                        ip_address=add_ip,
                        rtsp_path=add_rtsp,
                        full_url=add_full_url
                    )
                    st.success("Kamera eklendi.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if st.session_state.manual_cameras:
            with st.expander("🗂️ Eklenen Kameralar", expanded=False):
                for i, cam in enumerate(st.session_state.manual_cameras):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.write(f"**{cam['name']}**")
                        st.caption(f"{cam['type'].upper()} | {cam.get('ip', '-')}")
                    with col_b:
                        if st.button("Sil", key=f"del_cam_{i}"):
                            remove_manual_camera(i)
                            st.rerun()

        st.divider()

        selected_cam_name = st.selectbox("Aktif Cihaz", camera_names)

        selected_source = next(
            (cam for cam in all_cameras if cam["display_name"] == selected_cam_name),
            all_cameras[0]
        )

        st.caption(f"Bağlantı Türü: {selected_source['type'].upper()}")
        st.caption(f"IP / Bilgi: {selected_source.get('ip', '-')}")

        st.divider()
        st.subheader("🎨 Görüntü Ayarları")

        selected_cam_key = selected_source["cam_key"]
        selected_cam_settings = get_camera_settings(selected_cam_key)

        ct_val = st.slider(
            "Parlaklık",
            0.1, 3.0,
            value=float(selected_cam_settings["ct"]),
            key=f"ct_slider_{selected_cam_key}"
        )

        br_val = st.slider(
            "Kontrast",
            -100, 100,
            value=int(selected_cam_settings["br"]),
            key=f"br_slider_{selected_cam_key}"
        )

        sh_val = st.slider(
            "Keskinlik",
            -5.0, 5.0,
            value=float(selected_cam_settings["sh"]),
            key=f"sh_slider_{selected_cam_key}"
        )

        with st.expander("RGB Kanalları", expanded=False):
            r_val = st.slider(
                "Kırmızı",
                0.0, 2.0,
                value=float(selected_cam_settings["r_m"]),
                key=f"r_slider_{selected_cam_key}"
            )
            g_val = st.slider(
                "Yeşil",
                0.0, 2.0,
                value=float(selected_cam_settings["g_m"]),
                key=f"g_slider_{selected_cam_key}"
            )
            b_val = st.slider(
                "Mavi",
                0.0, 2.0,
                value=float(selected_cam_settings["b_m"]),
                key=f"b_slider_{selected_cam_key}"
            )

        new_settings = {
            "ct": ct_val,
            "br": br_val,
            "sh": sh_val,
            "r_m": r_val,
            "g_m": g_val,
            "b_m": b_val
        }

        if new_settings != selected_cam_settings:
            set_camera_settings(selected_cam_key, new_settings)
            apply_settings_to_streamer(selected_cam_key)

        col_reset, col_reset_all = st.columns(2)

        with col_reset:
            if st.button("↺ Bu Kamerayı Sıfırla", use_container_width=True):
                reset_camera_settings(selected_cam_key)
                apply_settings_to_streamer(selected_cam_key)
                log_to_system(
                    f"Görüntü ayarları sıfırlandı: {selected_source['display_name']}",
                    "INFO",
                    save_csv=False,
                    show_ui=True
                )
                st.rerun()

        with col_reset_all:
            if st.button("🗑️ Tüm Ayarları Temizle", use_container_width=True):
                st.session_state.camera_settings = {}
                save_camera_settings_to_disk()
                streamers = get_streamers()
                for cam_key in list(streamers.keys()):
                    apply_settings_to_streamer(cam_key)
                log_to_system(
                    "Tüm kamera ayarları temizlendi.",
                    "INFO",
                    save_csv=False,
                    show_ui=True
                )
                st.rerun()

    return view_mode, all_cameras, selected_source