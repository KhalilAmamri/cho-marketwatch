import os
import base64
import pandas as pd
import streamlit as st

from dashboard.auth import logout
from dashboard.data import get_failed_scrapes_summary, get_last_update_timestamp


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _nav_button(label: str, page_name: str, current_page: str):
    clicked = st.button(
        label,
        key=f"nav_{page_name}",
        use_container_width=True,
        type="primary" if current_page == page_name else "secondary",
    )
    if clicked:
        st.session_state["active_page"] = page_name
        st.rerun()


def set_admin_flash(message: str, level: str = "success"):
    st.session_state["admin_flash"] = {"message": message, "level": level}


def render_admin_flash():
    flash = st.session_state.pop("admin_flash", None)
    if not flash:
        return

    message = flash.get("message", "")
    level = flash.get("level", "success")

    if hasattr(st, "toast"):
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        st.toast(message, icon=icon_map.get(level, "ℹ️"))

    if level == "success":
        st.success(message)
    elif level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)


def screenshot_data_uri(path_value):
    if not path_value or str(path_value).strip() == "":
        return None

    screenshot_rel = str(path_value).replace("/", os.sep)
    screenshot_abs = os.path.join(PROJECT_ROOT, screenshot_rel)
    if not os.path.exists(screenshot_abs):
        return None

    try:
        with open(screenshot_abs, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def render_sidebar():
    with st.sidebar:
        st.image("assets/cho_group_logo.png", width=160)
        st.markdown(
            "<p style='color:#C9A84C; font-size:0.75rem; "
            "letter-spacing:0.08em; text-transform:uppercase; margin:4px 0 4px 0;'>"
            "Retail Price Tracker</p>",
            unsafe_allow_html=True,
        )
        st.caption(f"👤 {st.session_state.get('full_name', '')}  ·  {st.session_state.get('role', '').upper()}")
        st.divider()

        market_pages = [
            "Prices Explorer",
            "Price Trends",
            "Store Comparison",
            "Price Forecast",
        ]
        admin_pages = [
            "🧩  Manage Products",
            "🔗  Manage URLs",
            "👥  Manage Users",
        ]

        nav_labels = {
            "Prices Explorer": "🏷️  Prices Explorer",
            "Price Trends": "📈  Price Trends",
            "Store Comparison": "🏪  Store Comparison",
            "Price Forecast": "🔮  Price Forecast",
            "🧩  Manage Products": "🧩  Manage Products",
            "🔗  Manage URLs": "🔗  Manage URLs",
            "👥  Manage Users": "👥  Manage Users",
        }

        role = st.session_state.get("role")
        active_page = st.session_state.get("active_page", "Prices Explorer")

        # Keep compatibility with old sidebar key after label rename.
        if active_page == "➕  Add Product":
            active_page = "🧩  Manage Products"
            st.session_state["active_page"] = active_page

        # Keep compatibility with old market key after rename.
        if active_page == "Latest Prices":
            active_page = "Prices Explorer"
            st.session_state["active_page"] = active_page

        # Keep navigation safe when role/session changes.
        if role != "admin" and active_page in admin_pages:
            active_page = "Prices Explorer"
            st.session_state["active_page"] = active_page

        st.caption("Market Views")
        for page_name in market_pages:
            _nav_button(nav_labels.get(page_name, page_name), page_name, active_page)

        all_pages = market_pages + admin_pages if role == "admin" else market_pages
        page = active_page if active_page in all_pages else "Prices Explorer"

        if role == "admin":
            st.divider()
            st.caption("Administration")
            for page_name in admin_pages:
                _nav_button(nav_labels.get(page_name, page_name), page_name, active_page)

        st.session_state["active_page"] = page

        st.divider()
        st.caption("All prices normalized to EUR")

        if st.button("🚪 Logout", use_container_width=True):
            logout()

    return page


def render_footer():
    st.divider()
    last_scrape_time = get_last_update_timestamp()
    if last_scrape_time is not None:
        st.caption(f"CHO MarketWatch  ·  Last updated: {last_scrape_time:%Y-%m-%d %H:%M:%S}")
    else:
        st.caption("CHO MarketWatch  ·  No scraping data yet")


def render_failed_scrape_alerts():
    failed = get_failed_scrapes_summary()
    if failed.empty:
        return
    with st.expander("⚠️ Some websites had scraping issues"):
        for _, row in failed.iterrows():
            product = (
                f"{row['brand_name']} {row['category_name']} "
                f"{row['range_name']} {row['format']} {row['packaging']}"
            )
            status_code = row["last_status_code"] if not pd.isnull(row["last_status_code"]) else "N/A"
            country = row["country"] if "country" in row and not pd.isnull(row["country"]) else "Unknown"
            st.warning(
                f"🛒 Website: **{row['site_name']}** ({country})\n"
                f"📦 Product: {product}\n"
                f"🔗 URL: {row['url']}\n"
                f"❗ Status Code: {status_code}\n"
                f"⚠️ Error: {row['last_error']}\n"
                f"🔢 Failed Attempts: {row['fail_count']}"
            )
