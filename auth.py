# -*- coding: utf-8 -*-
"""
密码验证模块 - HR分析看板
密码存储在 Streamlit Cloud Secrets 中，键名：hr_dashboard_password
本地运行时请在项目根目录创建 .streamlit/secrets.toml 文件：
    hr_dashboard_password = "你的密码"
"""

import streamlit as st

def check_password():
    """密码验证，通过则返回 True"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # 从 Streamlit Secrets 读取密码（必须配置，否则无法登录）
    try:
        correct_pw = st.secrets["hr_dashboard_password"]
    except Exception:
        correct_pw = None

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="max-width:400px; margin:80px auto; text-align:center;">
            <h1 style="font-size:36px; color:#1E293B;">🔐 HR分析看板</h1>
            <p style="color:#64748B; font-size:15px; margin:10px 0 30px 0;">
                请输入访问密码以查看数据
            </p>
        </div>
        """, unsafe_allow_html=True)

        pw = st.text_input("访问密码", type="password", placeholder="请输入密码", key="pw_input")
        if correct_pw is None:
            st.warning("⚠️ 密码未配置，请联系管理员设置 Streamlit Secrets")
            return False
        if st.button("进入看板", type="primary", use_container_width=True):
            if pw == correct_pw:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ 密码错误，请重试")
                return False
    return False
