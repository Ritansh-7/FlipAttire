import runtime_env
import streamlit as st

st.set_page_config(page_title="FlipAttire personalization", page_icon=":material/checkroom:", layout="wide")
st.session_state.setdefault("customer_id", "00000dbacae5abe5e23885899a1fa44253a17956c6d1c3d25f88aa139fdfc657")

page = st.navigation(
    {
        "Customer": [st.Page("app_pages/user.py", title="My recommendations", icon=":material/checkroom:")],
        "Operations": [st.Page("app_pages/admin.py", title="Admin console", icon=":material/admin_panel_settings:")],
    },
    position="sidebar",
)
page.run()
