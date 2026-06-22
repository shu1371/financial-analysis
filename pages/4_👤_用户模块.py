"""
用户管理 - 浏览与修改个人信息
"""
import streamlit as st
import pandas as pd
from database.mysql_conn import User, SessionLocal, test_connection, init_db
from utils.helpers import hash_password
from utils.security import check_input_safety

st.set_page_config(
    page_title="用户管理 - 金融数据分析系统",
    page_icon="👤",
    layout="wide",
)

# 登录守卫
if not st.session_state.get("logged_in"):
    st.switch_page("app.py")
    st.stop()

st.title("👤 用户管理")

# 初始化
try:
    init_db()
except Exception:
    pass

# 数据库状态
db_ok, db_msg = test_connection()

# ---- 已登录 ----
username = st.session_state.get("username", "")
user_id = st.session_state.get("user_id")

st.markdown("---")

# ===== 个人信息 + 修改密码 =====
col_info, col_edit = st.columns([1, 1])

with col_info:
    st.subheader("📋 个人信息")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            st.markdown(f"| 项目 | 内容 |")
            st.markdown(f"|---|---|")
            st.markdown(f"| 用户名 | **{user.username}** |")
            st.markdown(f"| 用户ID | {user.id} |")
            st.markdown(f"| 注册时间 | {user.created_at} |")
            st.markdown(f"| 状态 | 🟢 在线 |")
    except Exception as e:
        st.error(f"加载信息失败: {e}")
    finally:
        db.close()

    # 退出登录
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_id"] = None
        st.rerun()

with col_edit:
    st.subheader("🔒 修改密码")
    with st.form("change_pw", border=True):
        old_pw = st.text_input("原密码", type="password")
        new_pw = st.text_input("新密码", type="password")
        new_pw2 = st.text_input("确认新密码", type="password")
        btn = st.form_submit_button("确认修改", type="primary")

        if btn:
            if not old_pw or not new_pw or not new_pw2:
                st.warning("请填写完整")
            elif len(new_pw) < 3:
                st.warning("新密码至少3个字符")
            elif new_pw != new_pw2:
                st.warning("两次新密码不一致")
            else:
                # 🔒 安全检查
                check_input_safety(old_pw, "原密码")
                check_input_safety(new_pw, "新密码")
                db = SessionLocal()
                try:
                    u = (
                        db.query(User)
                        .filter(
                            User.id == user_id,
                            User.password == hash_password(old_pw),
                        )
                        .first()
                    )
                    if not u:
                        st.error("原密码错误")
                    else:
                        u.password = hash_password(new_pw)
                        db.commit()
                        st.success("密码修改成功！")
                        st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"修改失败: {e}")
                finally:
                    db.close()

st.markdown("---")

if not db_ok:
    st.error(f"数据库状态: {db_msg}")
