import os
import sys
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.auth import check_login
from dashboard.ui import (
    apply_theme,
    render_failed_scrape_alerts,
    render_footer,
    render_sidebar,
    render_latest_prices_tab,
    render_price_trends_tab,
    render_store_comparison_tab,
    render_forecast_tab,
    render_add_product_tab,
    render_manage_urls_tab,
    render_manage_users_tab,
)


def main():
    st.set_page_config(
        page_title="CHO MarketWatch",
        page_icon="📊",
        layout="wide",
    )
    apply_theme()

    # ── 1. Login gate ──────────────────────────────────────────
    check_login()

    # ── 2. Sidebar navigation (role-aware) ────────────────────
    page = render_sidebar()

    # ── 3. Scraping alerts (visible to all) ───────────────────
    render_failed_scrape_alerts()

    # ── 4. Route to correct page ──────────────────────────────
    role = st.session_state.get("role")
    admin_only_pages = {
        "🧩  Manage Products",
        "🔗  Manage URLs",
        "👥  Manage Users",
    }
    page_handlers = {
        "Prices Explorer": render_latest_prices_tab,
        "Latest Prices": render_latest_prices_tab,
        "Price Trends": render_price_trends_tab,
        "Store Comparison": render_store_comparison_tab,
        "Price Forecast": render_forecast_tab,
        "🧩  Manage Products": render_add_product_tab,
        "➕  Add Product": render_add_product_tab,
        "🔗  Manage URLs": render_manage_urls_tab,
        "👥  Manage Users": render_manage_users_tab,
    }

    if page in admin_only_pages and role != "admin":
        st.error("🚫 Access denied.")
    else:
        page_handlers[page]()

    # ── 5. Footer ─────────────────────────────────────────────
    render_footer()


if __name__ == "__main__":
    main()
