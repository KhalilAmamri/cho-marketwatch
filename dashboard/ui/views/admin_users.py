import pandas as pd
import streamlit as st

from dashboard.ui.theme import render_page_title
from dashboard.auth import hash_password
from dashboard.admin import (
    get_all_users,
    add_user,
    update_user,
    update_user_password,
    delete_user,
)
from dashboard.ui.views.common import render_admin_flash, set_admin_flash


def render_manage_users_tab():
    render_page_title("👥 Manage Users", "Create, read, update, and delete user accounts.")
    render_admin_flash()

    users = get_all_users()
    tab_view, tab_create, tab_update, tab_delete = st.tabs(["All Users", "Create", "Update", "Delete"])

    with tab_view:
        if not users:
            st.info("No users found.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "ID": u[0],
                        "Username": u[1],
                        "Full Name": u[2] or "",
                        "Role": u[3],
                        "Active": u[4],
                        "Last Login": u[5].strftime("%Y-%m-%d %H:%M") if u[5] else "Never",
                    }
                    for u in users
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_create:
        with st.form("create_user_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Username")
                new_fullname = st.text_input("Full Name")
            with c2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                new_is_active = st.checkbox("Active account", value=True)
            create_submitted = st.form_submit_button("💾 Create User", type="primary")

        if create_submitted:
            if not new_username.strip() or not new_password:
                st.error("Username and password are required.")
            else:
                created_id = add_user(new_username.strip(), hash_password(new_password), new_fullname.strip(), new_role)
                if not created_id:
                    st.error("Username already exists.")
                else:
                    if not new_is_active:
                        update_user(created_id, new_fullname.strip(), new_role, False)
                    set_admin_flash(f"User '{new_username.strip()}' created successfully.")
                    st.rerun()

    with tab_update:
        if not users:
            st.info("No users available to update.")
        else:
            by_id = {u[0]: u for u in users}
            selected_user_id = st.selectbox(
                "Select user",
                options=list(by_id.keys()),
                format_func=lambda uid: f"{by_id[uid][1]} ({by_id[uid][3]})",
                key="user_update_select",
            )
            selected_user = by_id[selected_user_id]

            with st.form("update_user_form"):
                upd_fullname = st.text_input("Full Name", value=selected_user[2] or "")
                upd_role = st.selectbox("Role", ["user", "admin"], index=0 if selected_user[3] == "user" else 1)
                upd_is_active = st.checkbox("Active account", value=selected_user[4])
                upd_new_password = st.text_input("New password (optional)", type="password")
                update_submitted = st.form_submit_button("💾 Update User", type="primary")

            if update_submitted:
                current_user_id = st.session_state.get("user_id")
                current_user_role = st.session_state.get("role")

                if selected_user_id == current_user_id and not upd_is_active:
                    st.error("You cannot deactivate your own account.")
                elif selected_user_id == current_user_id and current_user_role == "admin" and upd_role != "admin":
                    st.error("You cannot remove your own admin role.")
                else:
                    ok, message = update_user(selected_user_id, upd_fullname.strip(), upd_role, upd_is_active)
                    if not ok:
                        st.error(message)
                    else:
                        if upd_new_password:
                            ok_pw, msg_pw = update_user_password(selected_user_id, hash_password(upd_new_password))
                            if not ok_pw:
                                st.error(msg_pw)
                                return
                        set_admin_flash(message)
                        st.rerun()

    with tab_delete:
        current_user_id = st.session_state.get("user_id")
        deletable_users = [u for u in users if u[0] != current_user_id]

        if not deletable_users:
            st.info("No deletable users available.")
        else:
            by_id = {u[0]: u for u in deletable_users}
            delete_user_id = st.selectbox(
                "Select user to delete",
                options=list(by_id.keys()),
                format_func=lambda uid: f"{by_id[uid][1]} ({by_id[uid][3]})",
                key="user_delete_select",
            )
            st.warning("Delete is permanent. This action cannot be undone.")
            confirm_delete = st.checkbox("I understand this action is permanent.", key="user_delete_confirm")

            if st.button("🗑️ Delete User", type="primary", disabled=not confirm_delete):
                ok, message = delete_user(delete_user_id, current_user_id=current_user_id)
                if ok:
                    set_admin_flash(message)
                    st.rerun()
                else:
                    st.error(message)
