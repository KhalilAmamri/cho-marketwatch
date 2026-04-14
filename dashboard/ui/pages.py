"""
Compatibility facade for page-level UI renderers.

The actual implementations live under dashboard.ui.views.
Keeping this module preserves existing imports used across the app.
"""

from dashboard.ui.views import (
    render_sidebar,
    render_failed_scrape_alerts,
    render_footer,
    render_latest_prices_tab,
    render_price_trends_tab,
    render_store_comparison_tab,
    render_forecast_tab,
    render_add_product_tab,
    render_manage_urls_tab,
    render_manage_users_tab,
)

__all__ = [
    "render_sidebar",
    "render_failed_scrape_alerts",
    "render_footer",
    "render_latest_prices_tab",
    "render_price_trends_tab",
    "render_store_comparison_tab",
    "render_forecast_tab",
    "render_add_product_tab",
    "render_manage_urls_tab",
    "render_manage_users_tab",
]
