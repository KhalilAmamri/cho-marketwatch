import streamlit as st

from dashboard.auth.login_view import (
    render_login_styles,
    render_login_brand_panel,
    render_login_form_card,
    authenticate_login,
)


def render_login_page():
    render_login_styles()
    st.markdown("<div style='height: 90px;'></div>", unsafe_allow_html=True)
    left_col, right_col, right_spacer = st.columns([1.08, 0.78, 0.14], gap="medium")

    with left_col:
        render_login_brand_panel()

    with right_col:
        submitted, username, password = render_login_form_card()
        if submitted:
            ok, error_message = authenticate_login(username, password)
            if not ok:
                st.error(error_message)
                return
            st.rerun()

    with right_spacer:
        st.empty()
