import pandas as pd
import streamlit as st

from dashboard.ui.theme import render_page_title
from dashboard.data import get_weekly_price_points
from dashboard.ui.views.common import screenshot_data_uri


def render_latest_prices_tab():
    render_page_title(
        "🏷️ Prices Explorer Across All Stores",
        "Default view shows latest week. Use filters to explore older weekly data.",
    )

    df = get_weekly_price_points()
    if df.empty:
        st.warning("No price data available yet. Run scrapers first.")
        return

    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df = df.dropna(subset=["scraped_at", "price_eur"]).copy()
    if df.empty:
        st.warning("No valid price rows available after cleaning.")
        return

    df["week_start"] = df["scraped_at"].dt.date

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        products = ["All Products"] + sorted(df["product"].dropna().unique().tolist())
        selected_product = st.selectbox("Product:", products, key="prices_filter_product")

    product_scope = df[df["product"] == selected_product] if selected_product != "All Products" else df

    with col2:
        countries = ["All Countries"] + sorted(product_scope["country"].dropna().unique().tolist())
        selected_country = st.selectbox("Country:", countries, key="prices_filter_country")

    country_scope = (
        product_scope[product_scope["country"] == selected_country]
        if selected_country != "All Countries"
        else product_scope
    )

    with col3:
        websites = ["All Websites"] + sorted(country_scope["website"].dropna().unique().tolist())
        selected_website = st.selectbox("Website:", websites, key="prices_filter_website")

    website_scope = (
        country_scope[country_scope["website"] == selected_website]
        if selected_website != "All Websites"
        else country_scope
    )

    with col4:
        stores = ["All Stores"] + sorted(website_scope["store"].dropna().unique().tolist())
        selected_store = st.selectbox("Store:", stores, key="prices_filter_store")

    store_scope = (
        website_scope[website_scope["store"] == selected_store]
        if selected_store != "All Stores"
        else website_scope
    )

    with col5:
        currencies = ["All Currencies"] + sorted(store_scope["currency"].dropna().unique().tolist())
        selected_currency = st.selectbox("Currency:", currencies, key="prices_filter_currency")

    base_filtered = df.copy()
    if selected_product != "All Products":
        base_filtered = base_filtered[base_filtered["product"] == selected_product]
    if selected_country != "All Countries":
        base_filtered = base_filtered[base_filtered["country"] == selected_country]
    if selected_website != "All Websites":
        base_filtered = base_filtered[base_filtered["website"] == selected_website]
    if selected_store != "All Stores":
        base_filtered = base_filtered[base_filtered["store"] == selected_store]
    if selected_currency != "All Currencies":
        base_filtered = base_filtered[base_filtered["currency"] == selected_currency]

    if base_filtered.empty:
        st.warning("No results for selected filters.")
        return

    week_options = sorted(base_filtered["week_start"].dropna().unique().tolist(), reverse=True)
    if not week_options:
        st.warning("No week values available for selected filters.")
        return

    control_col1, control_col2, control_col3 = st.columns([1.2, 1.4, 0.8])
    with control_col1:
        time_view = st.selectbox(
            "Time View:",
            ["Latest Week (Default)", "Specific Week", "All Weeks"],
            key="prices_filter_time_view",
        )

    with control_col2:
        selected_week = None
        if time_view == "Specific Week":
            selected_week = st.selectbox(
                "Week Start:",
                week_options,
                key="prices_filter_week",
                format_func=lambda d: d.strftime("%Y-%m-%d"),
            )
        elif time_view == "Latest Week (Default)":
            st.caption(f"Latest available week: {week_options[0]:%Y-%m-%d}")
        else:
            st.caption(f"Weeks available: {len(week_options)}")

    with control_col3:
        show_screenshots = st.checkbox("Show Screenshots", value=False, key="prices_show_screenshots")

    filtered = base_filtered.copy()
    if time_view == "Latest Week (Default)":
        filtered = filtered[filtered["week_start"] == week_options[0]]
    elif time_view == "Specific Week":
        filtered = filtered[filtered["week_start"] == selected_week]

    if filtered.empty:
        st.warning("No results for selected filters.")
        return

    filtered = filtered.sort_values(["scraped_at", "price_eur"], ascending=[False, True])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Products", filtered["product"].nunique())
    c2.metric("Stores", filtered["store"].nunique())
    c3.metric("Weeks", filtered["week_start"].nunique())
    c4.metric("Lowest (EUR)", f"€{filtered['price_eur'].min():.2f}")
    c5.metric("Highest (EUR)", f"€{filtered['price_eur'].max():.2f}")

    st.divider()

    base_columns = [
        "product",
        "country",
        "store",
        "price",
        "currency",
        "price_eur",
        "week_start",
        "product_url",
    ]
    display = filtered[base_columns].copy()

    display.columns = [
        "Product",
        "Country",
        "Store",
        "Weekly Avg (Local Currency)",
        "Currency",
        "Weekly Avg (EUR)",
        "Week Start",
        "Link",
    ]

    display["Weekly Avg (Local Currency)"] = display["Weekly Avg (Local Currency)"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "-"
    )
    display["Weekly Avg (EUR)"] = display["Weekly Avg (EUR)"].apply(lambda x: f"€{x:.2f}")
    display["Week Start"] = pd.to_datetime(display["Week Start"]).dt.strftime("%Y-%m-%d")

    column_config = {
        "Link": st.column_config.LinkColumn("Link"),
    }
    if show_screenshots:
        display["Screenshot"] = filtered["screenshot_path"].apply(screenshot_data_uri)
        column_config["Screenshot"] = st.column_config.ImageColumn("Screenshot")

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )

    st.caption(f"Showing {len(display)} weekly price points")
