import os
import pandas as pd
import streamlit as st

from dashboard.ui.theme import render_page_title
from dashboard.admin import (
    get_all_brands,
    get_all_categories,
    get_all_ranges,
    get_all_formats_with_ids,
    add_brand,
    add_category,
    add_range,
    add_product_format,
    update_product_format,
    delete_product_format,
)
from dashboard.ui.views.common import render_admin_flash, set_admin_flash


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HISTORICAL_DATA_CSV = os.path.join(PROJECT_ROOT, "data", "olive_oil_historical_prices.csv")


def _normalize_format_value(value):
    return str(value or "").strip().replace(" ", "").upper()


def _normalize_packaging_value(value):
    return str(value or "").strip()


def _load_historical_format_packaging_options():
    if not os.path.exists(HISTORICAL_DATA_CSV):
        return [], []

    try:
        df = pd.read_csv(HISTORICAL_DATA_CSV, encoding="utf-8-sig")
    except Exception:
        return [], []

    if "Size" not in df.columns or "Packaging" not in df.columns:
        return [], []

    format_values = sorted(
        {
            _normalize_format_value(v)
            for v in df["Size"].dropna().tolist()
            if _normalize_format_value(v)
        }
    )
    packaging_values = sorted(
        {
            _normalize_packaging_value(v)
            for v in df["Packaging"].dropna().tolist()
            if _normalize_packaging_value(v)
        }
    )
    return format_values, packaging_values


def _with_current_option(options, current_value, normalizer):
    current = normalizer(current_value)
    if not current:
        return options
    if any(normalizer(opt) == current for opt in options):
        return options
    return sorted(set(options + [current]))


def _product_label_from_row(row):
    return f"{row[7]} {row[8]} {row[9]} {row[5]} {row[6]}"


def render_add_product_tab():
    render_page_title("🧩 Product Management", "Create, read, update, and delete product formats.")

    formats = get_all_formats_with_ids()
    if formats:
        df = pd.DataFrame(
            [
                {
                    "ID": row[0],
                    "Brand": row[7],
                    "Category": row[8],
                    "Range": row[9],
                    "Format": row[5],
                    "Packaging": row[6],
                }
                for row in formats
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No product formats found yet.")

    st.divider()
    render_admin_flash()
    tab_create, tab_update, tab_delete = st.tabs(["Create", "Update", "Delete"])

    brands = get_all_brands()
    categories = get_all_categories()
    ranges = get_all_ranges()

    brand_names = [b[1] for b in brands]
    category_names = [c[1] for c in categories]
    range_names = [r[1] for r in ranges]

    with tab_create:
        tracking_formats, tracking_packaging = _load_historical_format_packaging_options()
        fallback_formats = sorted({_normalize_format_value(row[5]) for row in formats if _normalize_format_value(row[5])})
        fallback_packaging = sorted({_normalize_packaging_value(row[6]) for row in formats if _normalize_packaging_value(row[6])})

        format_options = tracking_formats or fallback_formats
        packaging_options = tracking_packaging or fallback_packaging

        with st.expander("Add new lookup values (Brand / Category / Range)"):
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.form("form_add_brand", clear_on_submit=True):
                    new_brand = st.text_input("New Brand", key="crud_new_brand")
                    submit_brand = st.form_submit_button("Add Brand")
                if submit_brand:
                    if new_brand.strip():
                        created = add_brand(new_brand.strip())
                        if created:
                            set_admin_flash("Brand added successfully.")
                        else:
                            set_admin_flash("Brand already exists.", level="warning")
                        st.rerun()
                    else:
                        st.warning("Brand name is required.")
            with c2:
                with st.form("form_add_category", clear_on_submit=True):
                    new_category = st.text_input("New Category", key="crud_new_category")
                    submit_category = st.form_submit_button("Add Category")
                if submit_category:
                    if new_category.strip():
                        created = add_category(new_category.strip())
                        if created:
                            set_admin_flash("Category added successfully.")
                        else:
                            set_admin_flash("Category already exists.", level="warning")
                        st.rerun()
                    else:
                        st.warning("Category name is required.")
            with c3:
                with st.form("form_add_range", clear_on_submit=True):
                    new_range = st.text_input("New Range", key="crud_new_range")
                    submit_range = st.form_submit_button("Add Range")
                if submit_range:
                    if new_range.strip():
                        created = add_range(new_range.strip())
                        if created:
                            set_admin_flash("Range added successfully.")
                        else:
                            set_admin_flash("Range already exists.", level="warning")
                        st.rerun()
                    else:
                        st.warning("Range name is required.")

        with st.form("create_product_format_form"):
            c1, c2 = st.columns(2)
            with c1:
                brand_name = st.selectbox("Brand", brand_names)
                category_name = st.selectbox("Category", category_names)
                range_name = st.selectbox("Range", range_names)
            with c2:
                if format_options:
                    fmt = st.selectbox("Format / Size", format_options)
                else:
                    st.warning("No format options available from tracking list yet.")
                    fmt = ""

                if packaging_options:
                    packaging = st.selectbox("Packaging", packaging_options)
                else:
                    st.warning("No packaging options available from tracking list yet.")
                    packaging = ""
            submitted = st.form_submit_button("💾 Create Product Format", type="primary")

        if submitted:
            if not fmt.strip() or not packaging.strip():
                st.error("Format and packaging are required.")
            else:
                brand_id = next(b[0] for b in brands if b[1] == brand_name)
                cat_id = next(c[0] for c in categories if c[1] == category_name)
                range_id = next(r[0] for r in ranges if r[1] == range_name)
                created_id = add_product_format(brand_id, cat_id, range_id, fmt.strip(), packaging.strip())
                if created_id:
                    set_admin_flash(f"Product format created successfully (ID: {created_id}).")
                    st.rerun()
                else:
                    st.error("A product format with these values already exists.")

    with tab_update:
        formats = get_all_formats_with_ids()
        if not formats:
            st.info("No product formats available to update.")
        else:
            tracking_formats, tracking_packaging = _load_historical_format_packaging_options()
            fallback_formats = sorted({_normalize_format_value(row[5]) for row in formats if _normalize_format_value(row[5])})
            fallback_packaging = sorted({_normalize_packaging_value(row[6]) for row in formats if _normalize_packaging_value(row[6])})

            base_format_options = tracking_formats or fallback_formats
            base_packaging_options = tracking_packaging or fallback_packaging

            by_id = {row[0]: row for row in formats}
            selected_id = st.selectbox(
                "Select product format",
                options=list(by_id.keys()),
                format_func=lambda x: f"#{x} · {_product_label_from_row(by_id[x])}",
                key="crud_update_select",
            )
            selected = by_id[selected_id]

            brand_ids = [b[0] for b in brands]
            category_ids = [c[0] for c in categories]
            range_ids = [r[0] for r in ranges]

            format_options = _with_current_option(base_format_options, selected[5], _normalize_format_value)
            packaging_options = _with_current_option(base_packaging_options, selected[6], _normalize_packaging_value)

            selected_fmt = _normalize_format_value(selected[5])
            selected_packaging = _normalize_packaging_value(selected[6])

            fmt_index = 0
            if selected_fmt and selected_fmt in format_options:
                fmt_index = format_options.index(selected_fmt)

            packaging_index = 0
            if selected_packaging and selected_packaging in packaging_options:
                packaging_index = packaging_options.index(selected_packaging)

            with st.form("update_product_format_form"):
                c1, c2 = st.columns(2)
                with c1:
                    upd_brand = st.selectbox("Brand", brand_names, index=brand_ids.index(selected[2]))
                    upd_category = st.selectbox("Category", category_names, index=category_ids.index(selected[3]))
                    upd_range = st.selectbox("Range", range_names, index=range_ids.index(selected[4]))
                with c2:
                    if format_options:
                        upd_fmt = st.selectbox("Format / Size", format_options, index=fmt_index)
                    else:
                        st.warning("No format options available from tracking list yet.")
                        upd_fmt = ""

                    if packaging_options:
                        upd_packaging = st.selectbox("Packaging", packaging_options, index=packaging_index)
                    else:
                        st.warning("No packaging options available from tracking list yet.")
                        upd_packaging = ""
                update_submitted = st.form_submit_button("💾 Update Product Format", type="primary")

            if update_submitted:
                if not upd_fmt.strip() or not upd_packaging.strip():
                    st.error("Format and packaging are required.")
                else:
                    brand_id = next(b[0] for b in brands if b[1] == upd_brand)
                    cat_id = next(c[0] for c in categories if c[1] == upd_category)
                    range_id = next(r[0] for r in ranges if r[1] == upd_range)
                    ok, message = update_product_format(
                        selected_id,
                        brand_id,
                        cat_id,
                        range_id,
                        upd_fmt.strip(),
                        upd_packaging.strip(),
                    )
                    if ok:
                        set_admin_flash(message)
                        st.rerun()
                    else:
                        st.error(message)

    with tab_delete:
        formats = get_all_formats_with_ids()
        if not formats:
            st.info("No product formats available to delete.")
        else:
            by_id = {row[0]: row for row in formats}
            delete_id = st.selectbox(
                "Select product format to delete",
                options=list(by_id.keys()),
                format_func=lambda x: f"#{x} · {_product_label_from_row(by_id[x])}",
                key="crud_delete_select",
            )
            st.warning("Delete is blocked if URLs or price history still reference the product.")
            confirm_delete = st.checkbox("I understand this action is permanent.", key="crud_delete_confirm")
            if st.button("🗑️ Delete Product Format", type="primary", disabled=not confirm_delete):
                ok, message = delete_product_format(delete_id)
                if ok:
                    set_admin_flash(message)
                    st.rerun()
                else:
                    st.error(message)
