import streamlit as st

from dashboard.ui.charts import build_store_comparison_chart
from dashboard.ui.theme import render_page_title
from dashboard.data import get_products_list, get_store_comparison


def render_store_comparison_tab():
    render_page_title(
        "🏪 Store Price Comparison (EUR)",
        "Compare latest store prices side by side.",
    )

    products_df = get_products_list()
    if products_df.empty:
        st.warning("No products available.")
        return

    col1, col2 = st.columns(2)
    with col1:
        product_label = st.selectbox("Product:", products_df["label"].tolist(), key="compare_product")
    with col2:
        comparison_all = get_store_comparison(product_label)
        countries = ["All Countries"] + list(comparison_all["country"].unique())
        selected_country = st.selectbox("Country:", countries, key="compare_country")

    if selected_country != "All Countries":
        comparison_df = comparison_all[comparison_all["country"] == selected_country]
    else:
        comparison_df = comparison_all

    if comparison_df.empty:
        st.warning(f"No store data for {product_label}")
        return

    cheapest = comparison_df.iloc[0]
    expensive = comparison_df.iloc[-1]
    saving = expensive["price_eur"] - cheapest["price_eur"]

    c1, c2, c3, c4 = st.columns(4)
    cheapest_label = cheapest["store"]
    cheapest_country = f"{cheapest['country']}" if selected_country == "All Countries" else ""
    expensive_label = expensive["store"]
    expensive_country = f"{expensive['country']}" if selected_country == "All Countries" else ""
    c1.metric("Cheapest Store ✅", cheapest_label)
    if cheapest_country:
        c1.caption(cheapest_country)
    c2.metric("Most Expensive 🔴", expensive_label)
    if expensive_country:
        c2.caption(expensive_country)
    c3.metric("Max Saving", f"€{saving:.2f}")
    c4.metric("Saving %", f"{(saving / expensive['price_eur'] * 100):.1f}%")

    st.divider()
    st.plotly_chart(build_store_comparison_chart(comparison_df, product_label), use_container_width=True)

    st.divider()
    st.subheader("🏆 Price Ranking")
    for idx, row in comparison_df.reset_index(drop=True).iterrows():
        diff = row["price_eur"] - cheapest["price_eur"]
        diff_str = f" (+€{diff:.2f})" if diff > 0 else ""
        price = f"€{row['price_eur']:.2f}"
        country = f" · {row['country']}" if selected_country == "All Countries" else ""
        if idx == 0:
            st.success(f"🥇 **{row['store']}**{country} — {price} ✅ CHEAPEST")
        elif idx == len(comparison_df) - 1:
            st.error(f"🔴 **{row['store']}**{country} — {price}{diff_str}")
        else:
            st.info(f"**{row['store']}**{country} — {price}{diff_str}")
