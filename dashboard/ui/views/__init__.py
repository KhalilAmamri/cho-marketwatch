from dashboard.ui.views.common import (
    render_sidebar,
    render_failed_scrape_alerts,
    render_footer,
)
from dashboard.ui.views.latest_prices import render_latest_prices_tab
from dashboard.ui.views.price_trends import render_price_trends_tab
from dashboard.ui.views.store_comparison import render_store_comparison_tab
from dashboard.ui.views.forecast import render_forecast_tab
from dashboard.ui.views.admin_products import render_add_product_tab
from dashboard.ui.views.admin_urls import render_manage_urls_tab
from dashboard.ui.views.admin_users import render_manage_users_tab

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
