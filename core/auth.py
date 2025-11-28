import streamlit as st
import os
import datetime
from dotenv import load_dotenv
import extra_streamlit_components as stx

# 加载环境变量
load_dotenv()

def check_password():
    """Returns `True` if the user had a correct password."""
    
    # 1. 获取配置的账号密码
    if "WEB_USER" in os.environ and "WEB_PASSWORD" in os.environ:
        correct_user = os.environ["WEB_USER"]
        correct_password = os.environ["WEB_PASSWORD"]
    elif "WEB_USER" in st.secrets and "WEB_PASSWORD" in st.secrets:
        correct_user = st.secrets["WEB_USER"]
        correct_password = st.secrets["WEB_PASSWORD"]
    else:
        st.error("未配置登录账号密码，请在环境变量或 secrets.toml 中设置 WEB_USER 和 WEB_PASSWORD。")
        return False

    # 2. 初始化 Cookie Manager
    # key 参数用于避免组件重新初始化问题
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    
    # 3. 检查 Cookie (持久化登录)
    # 注意：组件加载需要时间，首次运行时可能为 None
    cookie_val = cookie_manager.get(cookie="is_logged_in")
    
    if cookie_val == "true":
        return True

    # 4. 检查 Session State (用于本次登录后的即时状态)
    if st.session_state.get("password_correct", False):
        return True

    # 5. 显示登录表单
    st.title("🔒 请登录")
    
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    
    if st.button("登录"):
        if username == correct_user and password == correct_password:
            st.session_state["password_correct"] = True
            
            # 设置 7 天有效期的 Cookie
            expires = datetime.datetime.now() + datetime.timedelta(days=7)
            cookie_manager.set("is_logged_in", "true", expires_at=expires)
            
            # 强制刷新以应用状态
            st.rerun()
        else:
            st.error("😕 用户名或密码错误")

    return False
