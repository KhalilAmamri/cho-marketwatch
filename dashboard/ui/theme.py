import streamlit as st


def apply_theme() -> None:
    """Apply a lightweight modern theme without external services."""
    st.markdown(
        """
        <style>
        :root {
            --cho-bg: #f6f8fb;
            --cho-surface: #ffffff;
            --cho-border: #e6eaf2;
            --cho-text: #1f2a44;
            --cho-muted: #5f6b82;
            --cho-accent: #0f766e;
            --cho-accent-soft: #e8f7f5;
        }

        .stApp {
            background: radial-gradient(circle at top right, #eefaf8 0%, var(--cho-bg) 42%);
            color: var(--cho-text);
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--cho-border);
            background: linear-gradient(180deg, #f8fafc 0%, #f2f5fa 100%);
        }

        div[data-testid="metric-container"] {
            background: var(--cho-surface);
            border: 1px solid var(--cho-border);
            border-radius: 14px;
            padding: 10px 14px;
            box-shadow: 0 6px 18px rgba(31, 42, 68, 0.06);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--cho-border);
            border-radius: 14px;
            overflow: hidden;
            background: var(--cho-surface);
        }

        .stButton > button {
            border-radius: 10px;
            border: 1px solid var(--cho-border);
            background: var(--cho-surface);
            color: var(--cho-text) !important;
            font-weight: 600;
        }

        .stButton > button:hover {
            border-color: var(--cho-accent);
            color: var(--cho-accent);
            background: var(--cho-accent-soft);
        }

        .stButton > button[kind="primary"] {
            background: var(--cho-accent);
            border-color: var(--cho-accent);
            color: #ffffff !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: #0e6a63;
            border-color: #0e6a63;
            color: #ffffff !important;
        }

        .stButton > button[kind="secondary"] {
            color: var(--cho-text) !important;
        }

        .stButton > button span {
            color: inherit !important;
        }

        .cho-page-title {
            margin: 2px 0 4px 0;
            font-size: 1.55rem;
            font-weight: 700;
            letter-spacing: .01em;
            color: var(--cho-text);
        }

        .cho-page-subtitle {
            margin: 0 0 14px 0;
            color: var(--cho-muted);
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_title(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"<div class='cho-page-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='cho-page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
