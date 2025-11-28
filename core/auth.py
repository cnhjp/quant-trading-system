import streamlit as st
import os
import datetime
import time
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
    # 使用固定 key 以保证组件稳定性
    cookie_manager = stx.CookieManager(key="auth_cookie_manager")
    st.session_state["_auth_cookie_manager"] = cookie_manager
    
    # 3. 检查 Cookie (持久化登录)
    # 如果刚点击了退出登录，强制忽略 Cookie
    if st.session_state.get("logout_reset", False):
        cookie_val = None
    else:
        cookie_val = cookie_manager.get("quant_auth_token")
    
    if cookie_val == "valid":
        return True

    # 4. 检查 Session State (用于本次登录后的即时状态)
    if st.session_state.get("password_correct", False):
        return True

    # 5. 显示登录表单
    st.title("🔒 请登录")
    
    # 调试信息：帮助排查 Cookie 读取问题
    # 如果显示 None，说明组件正在加载或 Cookie 不存在
    # 如果显示 valid，说明 Cookie 存在但可能逻辑判断有误（理论上不会走到这）
    # st.info(f"Debug: Cookie Status = {cookie_val}")
    
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    
    if st.button("登录"):
        if username == correct_user and password == correct_password:
            st.session_state["password_correct"] = True
            
            # 登录成功，清除退出标志
            if "logout_reset" in st.session_state:
                del st.session_state["logout_reset"]
            
            # 设置 7 天有效期的 Cookie
            expires = datetime.datetime.now() + datetime.timedelta(days=7)
            
            # 设置 Cookie (指定 path="/" 确保全局有效)
            cookie_manager.set("quant_auth_token", "valid", expires_at=expires, path="/")
            
            st.success("登录成功！正在跳转...")
            time.sleep(1) # 关键：给浏览器一点时间写入 Cookie
            
            # 强制刷新以应用状态
            st.rerun()
        else:
            st.error("😕 用户名或密码错误")

    return False

def logout():
    """Logs the user out."""
    # 清除 Session State
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    
    # 清除 Cookie
    cookie_manager = st.session_state.get("_auth_cookie_manager")
    if cookie_manager:
        # 双重保险：先设为空，再删除
        cookie_manager.set("quant_auth_token", "", path="/")
        cookie_manager.delete("quant_auth_token")
    
    # 设置标志位，防止页面刷新后立刻通过 Cookie 自动登录
    st.session_state["logout_reset"] = True
    
    st.success("已退出登录")
    time.sleep(1)
    st.rerun()
