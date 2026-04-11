import plotly.express as px


def build_price_trend_chart(df, title):
    fig = px.line(
        df,
        x="scraped_at",
        y="price",
        color="store",
        title=f"Price Trend: {title}",
        labels={"scraped_at": "Week", "price": "Price (EUR)", "store": "Store"},
        markers=True,
    )
    fig.update_layout(
        height=500,
        hovermode="x unified",
        template="plotly_white",
        yaxis_tickprefix="€",
        yaxis_tickformat=".2f",
    )
    return fig


def build_store_comparison_chart(df, title):
    fig = px.bar(
        df,
        x="store",
        y="price_eur",
        title=f"Store Comparison: {title}",
        labels={"store": "Store", "price_eur": "Price (EUR)"},
        color="price_eur",
        color_continuous_scale="RdYlGn_r",
        text="price_eur",
    )
    fig.update_layout(
        height=420,
        template="plotly_white",
        coloraxis_showscale=False,
        yaxis_tickprefix="€",
        yaxis_tickformat=".2f",
    )
    fig.update_traces(
        texttemplate="€%{text:.2f}",
        textposition="outside",
    )
    return fig