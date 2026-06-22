"""
安全检测模块 — XSS / SQL 注入攻击拦截

在每个文本输入点后调用 check_input_safety(value, field_name)，
若检测到攻击则自动跳转到警告页面。
"""
import re
from typing import Tuple
import streamlit as st

# ==================== 攻击特征模式 ====================

XSS_PATTERNS = [
    # HTML 标签注入
    r"<\s*script[\s>/>]",           # <script>
    r"<\s*/\s*script\s*>",          # </script>
    r"<\s*img[\s>]",                # <img ...>
    r"<\s*iframe[\s>]",             # <iframe ...>
    r"<\s*embed[\s>]",              # <embed ...>
    r"<\s*object[\s>]",             # <object ...>
    r"<\s*svg[\s>]",                # <svg ...>
    r"<\s*body[\s>]",               # <body ...>
    r"<\s*link[\s>]",               # <link ...>
    r"<\s*meta[\s>]",               # <meta ...>
    r"<\s*applet[\s>]",             # <applet ...>
    r"<\s*frame[\s>]",              # <frame ...>
    r"<\s*form[\s>]",               # <form ...>
    # 事件处理器
    r"\bonerror\s*=",               # onerror=
    r"\bonclick\s*=",               # onclick=
    r"\bonload\s*=",                # onload=
    r"\bonmouseover\s*=",           # onmouseover=
    r"\bonfocus\s*=",               # onfocus=
    r"\bonblur\s*=",                # onblur=
    r"\bonchange\s*=",              # onchange=
    r"\bonsubmit\s*=",              # onsubmit=
    # 协议注入
    r"\bjavascript\s*:",            # javascript:
    r"\bdata\s*:\s*text\s*/\s*html", # data:text/html
    r"\bvbscript\s*:",              # vbscript:
    # CSS 表达式 (IE)
    r"\bexpression\s*\(",
    # 编码绕过
    r"&#x?[0-9a-fA-F]+[;]?",        # HTML 实体编码 (单独匹配无效，需组合 — 作为辅助)
]

SQLI_PATTERNS = [
    # 经典 SQL 注入
    r"'\s*OR\s+'?\s*\d",           # ' OR '1'='1, ' OR 1=1
    r"'\s*OR\s+\d+\s*=\s*\d+",     # ' OR 1=1
    r"'\s*OR\s+'[^']*'\s*=\s*'",   # ' OR 'a'='a
    r'"\s*OR\s+"?\s*\d',          # " OR "1"="1
    r'"\s*OR\s+\d+\s*=\s+\d+',    # " OR 1=1
    # UNION 注入
    r"\bUNION\s+SELECT\b",         # UNION SELECT
    r"\bUNION\s+ALL\s+SELECT\b",   # UNION ALL SELECT
    # 注释截断
    r"'\s*--",                      # ' --
    r"'\s*#",                       # ' #
    r"'\s*/\*",                     # ' /*
    r'"\s*--',                      # " --
    r'"\s*#',                       # " #
    # 数据库操作
    r"\bDROP\s+TABLE\b",           # DROP TABLE
    r"\bDROP\s+DATABASE\b",        # DROP DATABASE
    r"\bDELETE\s+FROM\b",          # DELETE FROM
    r"\bTRUNCATE\s+TABLE\b",       # TRUNCATE TABLE
    r"\bALTER\s+TABLE\b",          # ALTER TABLE
    r"\bINSERT\s+INTO\b.*\bVALUES\b", # INSERT INTO ... VALUES
    r"\bUPDATE\s+\w+\s+SET\b",     # UPDATE ... SET
    # 系统命令/函数
    r"\bxp_cmdshell\b",            # SQL Server
    r"\bEXEC\s*\(\s*sp_",         # EXEC sp_...
    # 信息探测
    r"\binformation_schema\b",      # MySQL
    r"\bsqlite_master\b",          # SQLite
    r"\b@@version\b",               # MySQL/SQL Server
    r"\bSLEEP\s*\(",               # SLEEP()
    r"\bBENCHMARK\s*\(",           # BENCHMARK()
    r"\bLOAD_FILE\s*\(",           # LOAD_FILE()
    r"\bINTO\s+OUTFILE\b",         # INTO OUTFILE
    r"\bINTO\s+DUMPFILE\b",        # INTO DUMPFILE
]


def is_xss_attack(value: str) -> bool:
    """检测输入是否包含 XSS 攻击特征（大小写不敏感）"""
    if not value or not isinstance(value, str):
        return False
    lower = value.lower()
    for pattern in XSS_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False


def is_sqli_attack(value: str) -> bool:
    """检测输入是否包含 SQL 注入攻击特征（大小写不敏感）"""
    if not value or not isinstance(value, str):
        return False
    upper = value.upper()
    for pattern in SQLI_PATTERNS:
        if re.search(pattern, upper, re.IGNORECASE):
            return True
    return False


def is_attack(value: str) -> Tuple[bool, str]:
    """
    综合检测 XSS 和 SQL 注入攻击

    返回: (is_attack: bool, attack_type: str)
        attack_type: "XSS" | "SQL注入" | "XSS+SQL注入" | ""
    """
    if not value or not isinstance(value, str):
        return False, ""

    xss = is_xss_attack(value)
    sqli = is_sqli_attack(value)

    if xss and sqli:
        return True, "XSS + SQL注入"
    elif xss:
        return True, "XSS 跨站脚本"
    elif sqli:
        return True, "SQL注入"
    return False, ""


def check_input_safety(value: str, field_name: str = "未知字段") -> None:
    """
    检查输入安全性。若检测到攻击则跳转警告页并停止执行。

    用法:
        username = st.text_input("用户名")
        if submitted:
            check_input_safety(username, "用户名")  # 攻击时自动跳转，不会返回
    """
    if not value or not isinstance(value, str):
        return

    is_atk, atk_type = is_attack(value)
    if is_atk:
        redirect_to_warning(atk_type, field_name, value)
        st.stop()  # 防御性：如果 switch_page 没有立即生效


def redirect_to_warning(attack_type: str, field_name: str, payload: str) -> None:
    """
    将攻击信息存入 session_state 并跳转到安全警告页面。
    """
    # 截断 payload 避免 session_state 存过大数据
    payload_short = payload[:200] if len(payload) > 200 else payload

    st.session_state["security_alert"] = {
        "attack_type": attack_type,
        "field_name": field_name,
        "payload": payload_short,
    }

    # 记录攻击日志
    _log_attack_to_db(attack_type, field_name, payload_short)

    st.switch_page("pages/7_⚠️_安全警告.py")


def _log_attack_to_db(attack_type: str, field_name: str, payload: str) -> None:
    """将攻击记录写入 security_log 表（静默失败，不影响主流程）"""
    try:
        import pymysql
        import config

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
                cur.execute(
                    """
                    INSERT INTO security_log (attack_type, field_name, payload, page, username)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        attack_type,
                        field_name,
                        payload[:1000],
                        st.session_state.get("_current_page", "unknown"),
                        st.session_state.get("username", ""),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # 数据库不可用时静默失败
