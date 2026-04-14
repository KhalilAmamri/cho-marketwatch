import streamlit as st

from dashboard.auth.view import render_login_page


def _clear_auth_state():
    for key in ["user_id", "username", "full_name", "role"]:
        st.session_state.pop(key, None)


def check_login():
    if "role" in st.session_state and "username" in st.session_state:
        return

    _clear_auth_state()

    render_login_page()
    st.stop()


def logout():
    _clear_auth_state()
    st.rerun()
