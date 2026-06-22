"""
安全警告页面 — 检测到攻击行为时跳转到此页面
"""
import streamlit as st
import pymysql
import config
from datetime import datetime

st.set_page_config(
    page_title="⚠️ 安全警告 - 金融数据分析系统",
    page_icon="⚠️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==================== 确保 security_log 表存在 ====================
try:
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS security_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    attack_type VARCHAR(50) NOT NULL COMMENT '攻击类型: XSS/SQL注入',
                    field_name VARCHAR(100) DEFAULT '' COMMENT '触发字段',
                    payload TEXT COMMENT '攻击载荷',
                    page VARCHAR(100) DEFAULT '' COMMENT '来源页面',
                    username VARCHAR(50) DEFAULT '' COMMENT '操作用户',
                    ip_address VARCHAR(45) DEFAULT '' COMMENT '来源IP',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '攻击时间'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='安全攻击日志'
            """)
        conn.commit()
    finally:
        conn.close()
except Exception:
    pass

# ==================== 读取攻击信息 ====================
alert = st.session_state.get("security_alert", {})

if not alert:
    # 无攻击信息直接访问 → 重定向到首页
    st.switch_page("app.py")
    st.stop()

attack_type = alert.get("attack_type", "未知")
field_name = alert.get("field_name", "未知")
payload = alert.get("payload", "")

# 清除警报状态（防止刷新后重复显示）
st.session_state["security_alert"] = {}

# ==================== 页面样式 ====================
st.markdown("""
<style>
    .warning-container {
        text-align: center;
        padding: 40px 20px;
    }
    .warning-icon {
        font-size: 80px;
        margin-bottom: 10px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    .warning-title {
        font-size: 3rem;
        font-weight: 900;
        color: #ff4444;
        text-shadow: 2px 2px 4px rgba(255,0,0,0.3);
        margin-bottom: 10px;
    }
    .warning-subtitle {
        font-size: 1.2rem;
        color: #ff6666;
        margin-bottom: 30px;
    }
    .attack-info {
        background: #1a1a2e;
        border: 1px solid #ff4444;
        border-radius: 12px;
        padding: 20px;
        max-width: 500px;
        margin: 0 auto 30px auto;
        text-align: left;
    }
    .attack-info th {
        color: #ff6666;
        text-align: right;
        padding-right: 12px;
        white-space: nowrap;
        vertical-align: top;
    }
    .attack-info td {
        color: #ccc;
        word-break: break-all;
    }
    .siren-bar {
        background: repeating-linear-gradient(
            45deg,
            #ff0000,
            #ff0000 10px,
            #cc0000 10px,
            #cc0000 20px
        );
        height: 4px;
        margin: 20px 0;
        border-radius: 2px;
        animation: siren 0.5s linear infinite;
    }
    @keyframes siren {
        0% { background-position: 0 0; }
        100% { background-position: 40px 0; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 页面内容 ====================
st.markdown('<div class="siren-bar"></div>', unsafe_allow_html=True)

st.markdown("""
<div class="warning-container">
    <div class="warning-icon">🚨</div>
    <div class="warning-title">黑客攻击！</div>
    <div class="warning-subtitle">系统检测到恶意输入，已拦截本次请求</div>
</div>
""", unsafe_allow_html=True)

# 攻击详情
st.markdown(f"""
<div class="attack-info">
    <table>
        <tr><th>🛡️ 攻击类型</th><td><b>{attack_type}</b></td></tr>
        <tr><th>📋 触发字段</th><td>{field_name}</td></tr>
        <tr><th>💣 攻击载荷</th><td><code>{payload}</code></td></tr>
        <tr><th>🕐 拦截时间</th><td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
    </table>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="siren-bar"></div>', unsafe_allow_html=True)

# 操作按钮
c1, c2, c3 = st.columns([1, 1.5, 1])
with c2:
    st.warning("⚠️ 您的行为已被系统记录")
    if st.button("🏠 返回首页", type="primary", use_container_width=True):
        # 清除登录状态
        for key in ["logged_in", "username", "user_id", "is_admin"]:
            if key in st.session_state:
                st.session_state[key] = False if key == "logged_in" else None
        st.switch_page("app.py")

st.markdown("---")
st.caption("🔒 金融数据分析系统 · 安全防护 · 攻击行为已记录至安全日志")
