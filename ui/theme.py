import streamlit as st


def apply_ids_peak_theme():
    st.markdown("""
    <style>
    :root {
        --bg: #1f2328;
        --panel: #2a2f36;
        --border: #4a525e;
        --text: #e6edf3;
        --muted: #9aa4b2;
        --accent: #35c2d1;
        --accent-dark: #1596a6;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 0.6rem;
        max-width: 100%;
    }

    #MainMenu,
    footer,
    .stAppDeployButton,
    div[data-testid="stDecoration"] {
        display: none !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0rem !important;
    }

    div[data-testid="stToolbar"] {
        background: transparent !important;
        height: 2.2rem !important;
        right: 0.5rem !important;
    }

    div[data-testid="stToolbar"] > div {
        background: transparent !important;
    }

    section[data-testid="stSidebar"] {
        background: #22272e;
        border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.8rem;
    }

    h1, h2, h3, h4, h5, h6, p, span, label, div {
        color: var(--text);
    }

    .ids-toolbar {
        background: linear-gradient(180deg, #2d333b 0%, #262b31 100%);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 0;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
    }

    .ids-toolbar-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .ids-logo-badge {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 12px rgba(53,194,209,0.55);
    }

    .ids-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: .3px;
    }

    .ids-chip-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .ids-chip {
        background: #20252b;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 12px;
        color: var(--text);
    }

    .ids-chip-accent {
        border-color: var(--accent);
        color: var(--accent);
    }

    .ids-panel {
        background: linear-gradient(180deg, var(--panel) 0%, #262b31 100%);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.18);
        margin-bottom: 12px;
    }

    .ids-panel-title {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .5px;
        color: var(--accent);
        margin-bottom: 10px;
        text-transform: uppercase;
    }

    .ids-metric-bar {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 12px;
    }

    .ids-metric {
        background: linear-gradient(180deg, #2b313a 0%, #252b32 100%);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 12px;
    }

    .ids-metric-k {
        font-size: 11px;
        color: var(--muted);
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .ids-metric-v {
        font-size: 17px;
        font-weight: 700;
        color: var(--text);
    }

    .ids-preview-shell {
        background: #15191e;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 10px;
        min-height: auto;
        margin-bottom: 10px;
    }

    .ids-preview-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
    }

    .ids-preview-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--text);
    }

    .ids-preview-meta {
        font-size: 12px;
        color: var(--muted);
    }

    .ids-right-stat {
        background: #21262d;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 8px;
    }

    .ids-right-stat .k {
        font-size: 11px;
        color: var(--muted);
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .ids-right-stat .v {
        font-size: 18px;
        font-weight: 700;
        color: var(--text);
    }

    .side-workspace-title {
        font-size: 13px;
        font-weight: 800;
        letter-spacing: .7px;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 12px;
    }

    /* Eski boş kutu görünümünü kaldır */
    .side-block,
    .tuning-shell {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
    }

    .side-block-title {
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .55px;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 10px;
        margin-top: 6px;
    }

    .tune-note {
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 10px;
    }

    .tune-group-title {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .5px;
        text-transform: uppercase;
        color: #8ce4ee;
        margin-bottom: 10px;
    }

    .tune-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        margin-top: 2px;
    }

    .tune-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--text);
    }

    .tune-value {
        min-width: 62px;
        text-align: center;
        padding: 4px 10px;
        border-radius: 999px;
        background: linear-gradient(180deg, #1c232a 0%, #171c22 100%);
        border: 1px solid #4b5866;
        color: #8ce4ee;
        font-size: 11px;
        font-weight: 700;
    }

    .registered-cam-box {
        background: #1f242b;
        border: 1px solid #414a56;
        border-radius: 10px;
        padding: 8px;
        margin-bottom: 8px;
    }

    div.stButton > button {
        background: linear-gradient(180deg, #3b434d 0%, #303740 100%);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 10px;
        height: 42px;
        font-weight: 600;
    }

    div.stButton > button:hover {
        border-color: var(--accent);
        color: var(--accent);
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stTextInput input {
        background: #1f242b !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 10px !important;
    }

    .stTextInput input::placeholder {
        color: var(--muted);
    }

    .stSlider {
        margin-bottom: 14px;
    }

    .terminal-log {
        background: #171b20;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        min-height: 180px;
        max-height: 240px;
        overflow-y: auto;
        font-family: Consolas, monospace;
        font-size: 12px;
        color: #c9d1d9;
    }

    .stExpander {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: #252b31;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)