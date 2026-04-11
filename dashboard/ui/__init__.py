from dashboard.ui.pages import (
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

from dashboard.ui.charts import (
    build_price_trend_chart,
    build_store_comparison_chart,
)

from dashboard.ui.theme import (
    apply_theme,
    render_page_title,
)
