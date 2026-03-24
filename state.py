import streamlit as st

def init_session_state():
    if "manual_cameras" not in st.session_state:
        st.session_state.manual_cameras = []

    if "grid_selected_cameras" not in st.session_state:
        st.session_state.grid_selected_cameras = []

    if "ui_logs" not in st.session_state:
        st.session_state.ui_logs = []

    if "streamers" not in st.session_state:
        st.session_state.streamers = {}

    if "camera_settings" not in st.session_state:
        st.session_state.camera_settings = {}