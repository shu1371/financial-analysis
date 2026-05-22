"""
通用工具函数
"""
import time
import ssl
import warnings
import pandas as pd

# ==================== 全局 SSL 兼容配置 ====================
# 必须在任何网络请求前执行，解决国内数据源证书/连接问题
warnings.filterwarnings("ignore")
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# 强制使用 TLS 1.2（兼容部分国内服务器）
import urllib3
urllib3.disable_warnings()
try:
    from requests.packages.urllib3.util.ssl_ import create_urllib3_context
    ctx = create_urllib3_context()
    ctx.load_default_certs()
    ctx.set_alpn_protocols([])
except Exception:
    pass
# ==================== SSL 配置结束 ====================


# 内存缓存股票代码→名称映射
_stock_name_cache: dict = {}


def get_stock_name(stock_code: str) -> str:
    """根据股票代码获取中文名称（带缓存，首次调用拉取全量列表）"""
    if stock_code in _stock_name_cache:
        return _stock_name_cache[stock_code]

    # 首次调用：批量拉取所有A股代码→名称映射
    if not _stock_name_cache:
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                code_col = df.columns[0]
                name_col = df.columns[1]
                for _, row in df.iterrows():
                    full_code = str(row[code_col])
                    name = str(row[name_col])
                    if not full_code or not name:
                        continue
                    _stock_name_cache[full_code] = name
                    # 也存无前缀版本（sz000001 → 000001）
                    if len(full_code) == 8:
                        _stock_name_cache[full_code[2:]] = name
        except Exception:
            pass

    return _stock_name_cache.get(stock_code, stock_code)


def fetch_stock_hist(stock_code, period="daily", start_date="", end_date="", max_retries=3):
    """
    股票历史数据获取

    优先使用新浪财经源（数据字段更全），失败则回退到腾讯源。
    返回 (DataFrame, source_name)
    """
    import akshare as ak

    # 判断市场前缀
    if stock_code.startswith("6") or stock_code.startswith("9"):
        symbol = f"sh{stock_code}"
    else:
        symbol = f"sz{stock_code}"

    # ---- 源1: 新浪财经（字段全：日期/开/高/低/收/成交量/成交额） ----
    last_error = None
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df is not None and not df.empty:
                cols = df.columns.tolist()
                rename_map = {}
                if "date" not in cols:
                    rename_map["日期"] = "date"
                for src, dst in [
                    ("开盘价", "open"), ("收盘价", "close"), ("最高价", "high"), ("最低价", "low"),
                    ("成交量", "volume"), ("成交额", "amount"),
                ]:
                    if src in cols:
                        rename_map[src] = dst
                if rename_map:
                    df = df.rename(columns=rename_map)
                df["date"] = pd.to_datetime(df["date"])
                return df, "sina"
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 1.5)

    # ---- 源2: 腾讯（回退源） ----
    try:
        df = ak.stock_zh_a_hist_tx(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        if df is not None and not df.empty:
            df = df.rename(columns={
                "date": "date", "open": "open", "close": "close",
                "high": "high", "low": "low", "amount": "amount",
            })
            df["date"] = pd.to_datetime(df["date"])
            return df, "tencent"
    except Exception as e:
        pass

    raise last_error or RuntimeError("数据获取失败：所有数据源均不可用")


def safe_float(value, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_pct(value, decimals=2):
    """格式化为百分比字符串"""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def calc_ma(df, periods=(5, 10, 20, 60)):
    """计算移动平均线"""
    for p in periods:
        df[f"MA{p}"] = df["close"].rolling(window=p).mean()
    return df


def calc_rsi(df, period=14):
    """计算 RSI 指标"""
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


# ==================== XSS 防护工具 ====================
import html as _html


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符，防止 XSS"""
    return _html.escape(str(text), quote=True)


def escape_js(text: str) -> str:
    """转义字符串用于安全嵌入 JavaScript 上下文"""
    return str(text).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"') \
        .replace("<", "\\x3c").replace(">", "\\x3e").replace("&", "\\x26")


# ==================== 密码哈希工具 ====================
import hashlib
import secrets

# PBKDF2 迭代次数（OWASP 2023 推荐：SHA256 ≥ 600,000）
_PBKDF2_ITERATIONS = 600_000
_HASH_PREFIX_V2 = "pbkdf2$"  # 新版格式前缀，用于区分旧 SHA256 哈希


def hash_password(password: str) -> str:
    """对密码进行 PBKDF2-SHA256 哈希（随机盐，600k 次迭代）"""
    salt = secrets.token_hex(16)  # 16 字节随机盐 → 32 hex 字符
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
    )
    return f"{_HASH_PREFIX_V2}{salt}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """验证密码，兼容旧版 SHA256 格式和新版 PBKDF2 格式"""
    if stored.startswith(_HASH_PREFIX_V2):
        # 新版格式：pbkdf2$<salt>$<hash>
        _, salt, key_hex = stored.split("$", 2)
        new_key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
        )
        return secrets.compare_digest(new_key.hex(), key_hex)
    # 旧版 SHA256 + static salt（向后兼容）
    return secrets.compare_digest(
        stored,
        hashlib.sha256((password + "fin_analysis_2024").encode("utf-8")).hexdigest(),
    )


def needs_password_upgrade(stored: str) -> bool:
    """检查密码哈希是否需要升级到新版 PBKDF2 格式"""
    return not stored.startswith(_HASH_PREFIX_V2)


def validate_password_strength(password: str) -> tuple:
    """校验密码强度，返回 (is_valid: bool, error_message: str)"""
    if len(password) < 8:
        return False, "密码至少需要 8 个字符"
    if not any(c.isupper() for c in password):
        return False, "密码必须包含至少一个大写字母"
    if not any(c.islower() for c in password):
        return False, "密码必须包含至少一个小写字母"
    if not any(c.isdigit() for c in password):
        return False, "密码必须包含至少一个数字"
    return True, ""
