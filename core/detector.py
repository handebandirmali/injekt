import streamlit as st
from inkjet_check_save import InkjetCheck
from config import MODEL_PATH


@st.cache_resource
def load_detector():
    return InkjetCheck(MODEL_PATH)