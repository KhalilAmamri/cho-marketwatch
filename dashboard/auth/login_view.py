import base64
from pathlib import Path

import streamlit as st

from dashboard.auth.data import get_user_safe, update_last_login_safe, verify_password


def _file_to_data_uri(path: Path, mime_type: str) -> str | None:
    if not path.exists():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _load_logo_data_uri() -> str | None:
    logo_path = Path(__file__).resolve().parents[2] / "assets" / "cho_group_logo.png"
    return _file_to_data_uri(logo_path, "image/png")


def _load_left_panel_image_data_uri() -> str | None:
    assets_dir = Path(__file__).resolve().parents[2] / "assets"
    for candidate in ("bg_login.png", "background_login.png"):
        img_uri = _file_to_data_uri(assets_dir / candidate, "image/png")
        if img_uri:
            return img_uri
    return None


def render_login_styles():
    bg_image_uri = _load_left_panel_image_data_uri()
    app_background = (
        f"linear-gradient(135deg, rgba(244,249,255,0.82) 0%, rgba(234,242,252,0.78) 46%, rgba(226,238,250,0.82) 100%), url('{bg_image_uri}')"
        if bg_image_uri
        else "linear-gradient(135deg, #f7fbff 0%, #edf4fb 46%, #e5eef9 100%)"
    )
    shell_background = (
        f"linear-gradient(92deg, rgba(248,252,255,0.86) 0%, rgba(248,252,255,0.74) 42%, rgba(248,252,255,0.34) 68%, rgba(248,252,255,0.60) 100%), url('{bg_image_uri}')"
        if bg_image_uri
        else "linear-gradient(160deg, rgba(255,255,255,0.92), rgba(246,251,255,0.86))"
    )

    css = """
        <style>
        :root {
            --cho-gold: #d2a84a;
            --cho-gold-dark: #ae8326;
            --cho-text: #132238;
            --cho-muted: #33465f;
            --cho-border: rgba(18, 34, 56, 0.12);
        }

        .stApp {
            background-image: __CHO_APP_BG__;
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: var(--cho-text);
        }

        header[data-testid="stHeader"] {
            background: rgba(238, 246, 255, 0.82);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(18, 34, 56, 0.08);
        }

        div[data-testid="stToolbar"],
        div[data-testid="stToolbar"] * {
            background: transparent !important;
        }

        .main,
        .main > div {
            position: relative;
            z-index: 1;
        }

        .main .block-container {
            max-width: 1160px;
            min-height: calc(100vh - 3.2rem);
            padding-top: 4vh;
            padding-bottom: 4vh;
            padding-left: 1rem;
            padding-right: 1rem;
            display: flex;
            align-items: stretch;
        }

        .main .block-container > div[data-testid="stHorizontalBlock"],
        .main .block-container > div > div[data-testid="stHorizontalBlock"] {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid rgba(255, 255, 255, 0.80);
            border-radius: 26px;
            padding: 26px;
            background-image: __CHO_SHELL_BG__;
            background-size: 100% 100%, contain;
            background-repeat: no-repeat, no-repeat;
            background-position: center center, right center;
            box-shadow: 0 16px 36px rgba(18, 34, 56, 0.16);
            align-items: stretch;
            column-gap: 1rem;
            overflow: hidden;
        }

        .cho-login-left-panel {
            padding: 4px 8px 6px 8px;
            width: 100%;
            max-width: 100%;
            min-height: clamp(500px, 66vh, 700px);
            margin-left: 0;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }

        .cho-login-brand-top {
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 16px;
            margin-top: 0;
            margin-bottom: 50px;
        }

        .cho-login-brand-heading {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
        }

        .cho-login-logo-wrap {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            border: 1px solid rgba(18, 34, 56, 0.10);
            background: rgba(255, 255, 255, 0.94);
            padding: 8px 12px;
            margin-bottom: 0;
            box-shadow: 0 8px 18px rgba(18, 34, 56, 0.10);
        }

        .cho-login-logo {
            width: 230px;
            max-width: 100%;
            height: auto;
        }

        .cho-login-brand-title {
            font-size: 2.4rem;
            line-height: 1.1;
            font-weight: 900;
            letter-spacing: 0.015em;
            color: var(--cho-text);
            margin: 0 0 8px 0;
        }

        .cho-login-brand-sub {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #6f5418;
            margin: 0 0 12px 0;
            text-transform: uppercase;
        }

        .cho-login-brand-body {
            color: #223750;
            font-size: 1.02rem;
            line-height: 1.5;
            margin: 0 0 10px 0;
            max-width: 560px;
            font-weight: 700;
        }

        .cho-login-copy-list {
            list-style: none;
            margin: 0 0 12px 0;
            padding: 0;
            max-width: 560px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .cho-login-copy-item {
            position: relative;
            padding-left: 16px;
            color: #2a425f;
            font-size: 0.97rem;
            line-height: 1.48;
            font-weight: 600;
        }

        .cho-login-copy-item::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0.56em;
            width: 6px;
            height: 6px;
            border-radius: 999px;
            background: #b7892b;
        }

        .cho-login-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            margin-top: 12px;
            padding-top: 0;
        }

        .cho-login-badge {
            position: relative;
            padding: 0 0 0 14px;
            border: none;
            background: transparent;
            color: #425976;
            font-size: 0.9rem;
            font-weight: 600;
            letter-spacing: 0;
            line-height: 1.2;
        }

        .cho-login-badge::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0.4em;
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: #d2a84a;
        }

        .cho-login-card-title {
            font-size: 2rem;
            font-weight: 900;
            color: var(--cho-text);
            margin: 4px 0 3px 0;
            text-align: center;
        }

        .cho-login-card-subtitle {
            font-size: 0.98rem;
            color: var(--cho-muted);
            margin: 0 0 14px 0;
            text-align: center;
        }

        .cho-login-form-zone {
            width: 100%;
            max-width: 470px;
            margin: 0 auto;
            padding: 8px 6px;
            align-self: center;
        }

        div[data-testid="stForm"] {
            border: 1px solid var(--cho-border);
            border-radius: 18px;
            padding: 16px 18px 10px 18px;
            background: rgba(255, 255, 255, 0.74);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            box-shadow: 0 8px 22px rgba(18, 34, 56, 0.08);
        }

        div[data-testid="stForm"] .stTextInput > label {
            color: #1e2f46;
            font-weight: 600;
        }

        div[data-testid="stForm"] .stTextInput > div > div > input {
            border-radius: 11px;
            border: 1px solid rgba(18, 34, 56, 0.18);
            background: rgba(255, 255, 255, 0.82);
            color: #132238;
            min-height: 44px;
        }

        div[data-testid="stForm"] .stTextInput > div > div > input::placeholder {
            color: #738399;
        }

        div[data-testid="stForm"] .stTextInput > div > div > input:focus {
            border-color: var(--cho-gold);
            box-shadow: 0 0 0 0.2rem rgba(210, 168, 74, 0.24);
        }

        div[data-testid="stForm"] .stFormSubmitButton > button,
        div[data-testid="stForm"] .stFormSubmitButton > button[kind="primary"] {
            border-radius: 999px;
            border: 1px solid var(--cho-gold-dark) !important;
            background: linear-gradient(135deg, #efc973 0%, #dfb153 58%, #c99638 100%) !important;
            color: #1d2a40 !important;
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            min-height: 46px;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton > button * {
            color: #1d2a40 !important;
            fill: #1d2a40 !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton > button:hover {
            border-color: #966f20 !important;
            background: linear-gradient(135deg, #e5ba61 0%, #d3a143 58%, #bb892d 100%) !important;
            color: #162235 !important;
        }

        div[data-baseweb="notification"] {
            border-radius: 12px;
            border: 1px solid rgba(18, 34, 56, 0.16);
            background: rgba(255, 255, 255, 0.9);
        }

        @media (max-width: 1050px) {
            .main .block-container {
                padding-top: 2.5vh;
                min-height: auto;
                display: block;
                align-items: initial;
            }

            .main .block-container > div[data-testid="stHorizontalBlock"],
            .main .block-container > div > div[data-testid="stHorizontalBlock"] {
                padding: 16px;
            }

            .cho-login-brand-title {
                font-size: 2.05rem;
            }

            .cho-login-brand-body {
                font-size: 0.98rem;
            }

            .cho-login-left-panel {
                margin-bottom: 16px;
                margin-left: 0;
                min-height: auto;
            }

            .cho-login-brand-top {
                margin-top: 0;
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }

            .cho-login-form-zone {
                max-width: 680px;
                margin: 0 auto;
            }

            .cho-login-badges {
                margin-top: 12px;
                padding-top: 0;
            }
        }
        </style>
    """.replace("__CHO_APP_BG__", app_background).replace("__CHO_SHELL_BG__", shell_background)

    st.markdown(css, unsafe_allow_html=True)


def render_login_brand_panel():
    logo_data_uri = _load_logo_data_uri()
    logo_html = (
        f"<div class='cho-login-logo-wrap'><img class='cho-login-logo' src='{logo_data_uri}' alt='CHO Group logo' /></div>"
        if logo_data_uri
        else ""
    )

    st.markdown(
        "<div class='cho-login-left-panel'>"
        "<div class='cho-login-brand-top'>"
        f"{logo_html}"
        "<div class='cho-login-brand-heading'>"
        "<div class='cho-login-brand-title'>CHO MarketWatch</div>"
        "<div class='cho-login-brand-sub'>Retail Price Tracker</div>"
        "</div>"
        "</div>"
        "<div class='cho-login-brand-body'>"
        "What you can do in this dashboard:"
        "</div>"
        "<ul class='cho-login-copy-list'>"
        "<li class='cho-login-copy-item'>Track olive oil retail prices in real time.</li>"
        "<li class='cho-login-copy-item'>Compare stores instantly and react faster to market changes.</li>"
        "<li class='cho-login-copy-item'>View latest prices, trend history, and side-by-side retailer comparisons in one place.</li>"
        "<li class='cho-login-copy-item'>Support confident weekly pricing and sourcing decisions for CHO teams.</li>"
        "</ul>"
        "<div class='cho-login-badges'>"
        "<span class='cho-login-badge'>Live Prices</span>"
        "<span class='cho-login-badge'>Store Comparison</span>"
        "<span class='cho-login-badge'>AI Forecast</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_login_form_card():
    st.markdown("<div class='cho-login-form-zone'>", unsafe_allow_html=True)
    st.markdown("<div class='cho-login-card-title'>Welcome Back</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='cho-login-card-subtitle'>Secure access to your dashboard</div>",
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    return submitted, username, password


def authenticate_login(username: str, password: str):
    if not username or not password:
        return False, "Please enter both username and password."

    user, db_error = get_user_safe(username)
    if db_error:
        return False, db_error

    if user is None:
        return False, "Invalid username or password."

    user_id, uname, password_hash, full_name, role, is_active = user

    if not is_active:
        return False, "Your account is disabled. Contact the administrator."

    if not verify_password(password, password_hash):
        return False, "Invalid username or password."

    st.session_state.user_id = user_id
    st.session_state.username = uname
    st.session_state.full_name = full_name or uname
    st.session_state.role = role

    update_error = update_last_login_safe(user_id)
    if update_error:
        st.warning(update_error)
    return True, None
