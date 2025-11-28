import streamlit as st
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_password():
    """Returns `True` if the user had a correct password."""
    
    # 获取配置的账号密码
    # Streamlit Cloud uses st.secrets, local development uses .env
    if "WEB_USER" in os.environ and "WEB_PASSWORD" in os.environ:
        correct_user = os.environ["WEB_USER"]
        correct_password = os.environ["WEB_PASSWORD"]
    elif "WEB_USER" in st.secrets and "WEB_PASSWORD" in st.secrets:
        correct_user = st.secrets["WEB_USER"]
        correct_password = st.secrets["WEB_PASSWORD"]
    else:
        # 如果没有配置，默认不需要登录，或者报错
        # 这里我们为了安全，如果没配置，默认不让进，提示配置
        st.error("未配置登录账号密码，请在环境变量或 secrets.toml 中设置 WEB_USER 和 WEB_PASSWORD。")
        return False

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] == correct_user and st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            # 清除敏感信息
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # 如果已经验证通过，直接返回 True
    if st.session_state.get("password_correct", False):
        return True

    # 显示登录表单
    st.title("🔒 请登录")
    
    st.text_input("用户名", key="username")
    st.text_input("密码", type="password", key="password")
    
    if st.button("登录"):
        password_entered()
        if st.session_state.get("password_correct", False):
            st.rerun()
        else:
            st.error("😕 用户名或密码错误")

    return False
