import pandas as pd
import streamlit as st

from dashboard.ui.theme import render_page_title
from dashboard.admin import (
    get_all_websites,
    get_all_stores,
    get_all_formats,
    get_all_product_urls,
    add_product_url,
    toggle_url_active,
    delete_product_url,
)
from dashboard.ui.views.common import render_admin_flash, set_admin_flash


def _format_label(row):
    return f"{row[1]} {row[2]} {row[3]} {row[4]} {row[5]}"


def _product_label_from_url_row(row):
    parts = [
        row[10] if len(row) > 10 else "",
        row[11] if len(row) > 11 else "",
        row[12] if len(row) > 12 else "",
        row[13] if len(row) > 13 else "",
        row[14] if len(row) > 14 else "",
    ]
    return " ".join(str(part).strip() for part in parts if str(part).strip())


def _url_row_label(row):
    store_part = row[8] or row[9] or "All stores"
    product = _product_label_from_url_row(row)
    status = "Active" if row[5] else "Inactive"
    return f"#{row[0]} · {row[6]} · {store_part} · {product} · {status}"


def render_manage_urls_tab():
    render_page_title("🔗 Manage Product URLs", "Create, activate/deactivate, and delete scraping links.")
    render_admin_flash()

    websites = get_all_websites()
    stores = get_all_stores()
    formats = get_all_formats()
    urls = get_all_product_urls()

    website_by_id = {w[0]: w for w in websites}
    format_by_id = {f[0]: f for f in formats}

    if urls:
        df = pd.DataFrame(
            [
                {
                    "ID": row[0],
                    "Website": row[6],
                    "Country": row[7] or "",
                    "Store": row[9] or row[8] or "All stores",
                    "Product": _product_label_from_url_row(row),
                    "URL": row[4],
                    "Active": row[5],
                }
                for row in urls
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No product URLs found yet.")

    st.divider()
    tab_create, tab_update, tab_delete = st.tabs(["Create", "Update Status", "Delete"])

    with tab_create:
        if not websites or not formats:
            st.warning("Websites and product formats are required before adding product URLs.")
        else:
            website_options = [w[0] for w in websites]
            format_options = [f[0] for f in formats]

            with st.form("create_product_url_form"):
                c1, c2 = st.columns(2)
                with c1:
                    website_id = st.selectbox(
                        "Website",
                        options=website_options,
                        format_func=lambda wid: f"{website_by_id[wid][1]} ({website_by_id[wid][2] or 'Unknown'})",
                    )

                    website_stores = [s for s in stores if s[1] == website_id]
                    store_options = [None] + [s[0] for s in website_stores]

                    store_id = st.selectbox(
                        "Store",
                        options=store_options,
                        format_func=lambda sid: (
                            "All stores / no specific store"
                            if sid is None
                            else f"{next(s for s in website_stores if s[0] == sid)[3]} ({next(s for s in website_stores if s[0] == sid)[4] or 'N/A'})"
                        ),
                    )

                with c2:
                    product_format_id = st.selectbox(
                        "Product Format",
                        options=format_options,
                        format_func=lambda fid: _format_label(format_by_id[fid]),
                    )
                    url = st.text_input("Product URL", placeholder="https://...")

                submitted = st.form_submit_button("💾 Add Product URL", type="primary")

            if submitted:
                if not url.strip().lower().startswith(("http://", "https://")):
                    st.error("Please enter a valid URL starting with http:// or https://")
                elif website_stores and store_id is None:
                    st.error("This website has stores. Please choose a specific store.")
                else:
                    created_id = add_product_url(website_id, store_id, product_format_id, url.strip())
                    if created_id:
                        set_admin_flash(f"Product URL added successfully (ID: {created_id}).")
                        st.rerun()
                    else:
                        st.error("A URL mapping with these values already exists.")

    with tab_update:
        if not urls:
            st.info("No product URLs available to update.")
        else:
            by_id = {row[0]: row for row in urls}
            selected_id = st.selectbox(
                "Select URL",
                options=list(by_id.keys()),
                format_func=lambda uid: _url_row_label(by_id[uid]),
            )
            selected = by_id[selected_id]

            current_active = bool(selected[5])
            desired_active = st.toggle("URL is active", value=current_active)

            if st.button("💾 Save Status", type="primary"):
                if desired_active == current_active:
                    st.info("No status change detected.")
                else:
                    toggle_url_active(selected_id, desired_active)
                    state_text = "activated" if desired_active else "deactivated"
                    set_admin_flash(f"URL #{selected_id} {state_text} successfully.")
                    st.rerun()

    with tab_delete:
        if not urls:
            st.info("No product URLs available to delete.")
        else:
            by_id = {row[0]: row for row in urls}
            delete_id = st.selectbox(
                "Select URL to delete",
                options=list(by_id.keys()),
                format_func=lambda uid: _url_row_label(by_id[uid]),
                key="crud_delete_url_select",
            )
            st.warning("Delete is permanent. This action cannot be undone.")
            confirm_delete = st.checkbox("I understand this action is permanent.", key="crud_delete_url_confirm")
            if st.button("🗑️ Delete URL", type="primary", disabled=not confirm_delete):
                delete_product_url(delete_id)
                set_admin_flash(f"URL #{delete_id} deleted successfully.")
                st.rerun()
