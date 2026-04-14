import streamlit as st

from dashboard.ui.charts import build_price_trend_chart
from dashboard.ui.theme import render_page_title
from dashboard.data import get_price_history, get_products_list


def render_price_trends_tab():
    render_page_title(
        "📈 Price Trends Over Time (EUR)",
        "Track historical movement by store.",
    )

    products_df = get_products_list()
    if products_df.empty:
        st.warning("No products available.")
        return

    product_label = st.selectbox("Product:", products_df["label"].tolist(), key="trend_product")
    history_df = get_price_history(product_label)

    if history_df.empty:
        st.warning(f"No price history for {product_label}")
        return

    st.plotly_chart(build_price_trend_chart(history_df, product_label), use_container_width=True)

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lowest", f"€{history_df['price'].min():.2f}")
    c2.metric("Highest", f"€{history_df['price'].max():.2f}")
    c3.metric("Average", f"€{history_df['price'].mean():.2f}")
    c4.metric("Range", f"€{(history_df['price'].max() - history_df['price'].min()):.2f}")
