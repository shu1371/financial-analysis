"""
首页 - 我的股票持仓
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database.mysql_conn import SessionLocal, init_db, UserStock
from utils.helpers import get_stock_name, fetch_stock_hist, escape_html

st.set_page_config(
    page_title="首页 - 金融数据分析系统",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("logged_in"):
    st.warning("请先登录")
    st.switch_page("app.py")

try:
    init_db()
except Exception:
    pass

user_id = st.session_state["user_id"]

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("📊 金融数据分析")

    st.markdown(f"👤 **{st.session_state.get('username', '')}**")
    if st.button("🚪 退出", use_container_width=True):
        for key in ["logged_in", "username", "user_id"]:
            st.session_state[key] = False if key == "logged_in" else (
                "" if key == "username" else None
            )
        st.switch_page("app.py")

    st.markdown("---")
    st.markdown("### 📂 功能导航")
    st.markdown(
        """
    - 🏠 **首页** — 我的持仓
    - 📈 **股票分析** — K线/均线/RSI
    - 📊 **数据统计** — 收益率/波动率
    - 👤 **用户管理** — 个人信息
    - 🎮 **游戏中心** — 预留
    """
    )
    st.markdown("---")
    st.caption("期末课设项目 | Powered by Streamlit")

# ==================== 主页内容 ====================
st.title("📊 我的持仓")
st.markdown("---")

# ==================== 加载持仓数据 ====================
db = SessionLocal()
try:
    stocks = (
        db.query(UserStock)
        .filter(UserStock.user_id == user_id)
        .order_by(UserStock.created_at.desc())
        .all()
    )
finally:
    db.close()

# ==================== 获取行情数据 ====================
stock_data = {}
end_date = datetime.now().strftime("%Y%m%d")
start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

if stocks:
    progress = st.progress(0, text="正在加载行情数据...")
    for i, s in enumerate(stocks):
        try:
            df, _ = fetch_stock_hist(
                s.stock_code, period="daily",
                start_date=start_date, end_date=end_date,
            )
            if df is not None and not df.empty:
                df = df.sort_values("date")
                stock_data[s.stock_code] = df
        except Exception:
            pass
        progress.progress((i + 1) / len(stocks), text=f"加载中... {s.stock_name}")
    progress.empty()

# ==================== 盈亏总览卡片 ====================
if stocks and stock_data:
    total_cost = 0.0
    total_value = 0.0
    for s in stocks:
        if s.stock_code in stock_data:
            latest_price = float(stock_data[s.stock_code].iloc[-1]["close"])
            total_cost += s.buy_price * s.shares
            total_value += latest_price * s.shares
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("持仓总成本", f"¥{total_cost:,.2f}")
    c2.metric("当前总市值", f"¥{total_value:,.2f}")
    c3.metric("总盈亏", f"¥{total_pnl:+,.2f}", delta=f"{total_pnl_pct:+.2f}%")
    c4.metric("持仓数量", f"{len([s for s in stocks if s.stock_code in stock_data])} 只")

    st.markdown("---")

# ==================== 持仓列表 ====================
if not stocks:
    st.info("你还没有添加股票，点击下方「添加股票」开始吧！")
else:
    # 构建数据行
    rows = []
    for s in stocks:
        if s.stock_code not in stock_data:
            continue
        df = stock_data[s.stock_code]
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        current_price = float(latest["close"])
        change_pct = (current_price - float(prev["close"])) / float(prev["close"]) * 100

        cost = s.buy_price * s.shares if s.buy_price else 0
        value = current_price * s.shares
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0

        rows.append({
            "股票名称": s.stock_name,
            "代码": s.stock_code,
            "最新价": current_price,
            "涨跌幅": change_pct,
            "买入价": s.buy_price,
            "持仓(股)": s.shares,
            "成本": cost,
            "市值": value,
            "盈亏": pnl,
            "盈亏%": pnl_pct,
            "id": s.id,
            "df": df,
        })

    if not rows:
        st.warning("暂时无法获取行情数据，请稍后刷新。")
    else:
        # 显示每只股票行
        for row in rows:
            pnl_color = "#e74c3c" if row["盈亏"] >= 0 else "#2ecc71"
            arrow = "▲" if row["盈亏"] >= 0 else "▼"

            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 0.8])

            with col1:
                st.markdown(
                    f"**{escape_html(row['股票名称'])}**  "
                    f"<span style='color:#888;font-size:0.85rem;'>{escape_html(row['代码'])}</span>",
                    unsafe_allow_html=True,
                )
                # 迷你走势图
                df = row["df"]
                fig = go.Figure()
                line_color = pnl_color
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["close"],
                    mode="lines",
                    line=dict(color=line_color, width=1.2),
                    showlegend=False,
                ))
                fig.update_layout(
                    height=50,
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with col2:
                st.markdown(
                    f"<span style='font-size:1.15rem;font-weight:bold;'>¥{row['最新价']:.2f}</span>"
                    f"<br><span style='font-size:0.8rem;color:{'#e74c3c' if row['涨跌幅'] >= 0 else '#2ecc71'};'>"
                    f"{row['涨跌幅']:+.2f}%</span>",
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(
                    f"<span style='font-size:0.85rem;color:#888;'>成本 ¥{row['成本']:,.2f}</span>"
                    f"<br><span style='font-size:0.85rem;'>市值 ¥{row['市值']:,.2f}</span>",
                    unsafe_allow_html=True,
                )

            with col4:
                st.markdown(
                    f"<span style='font-size:1rem;font-weight:bold;color:{pnl_color};'>"
                    f"{arrow} ¥{abs(row['盈亏']):,.2f}</span>"
                    f"<br><span style='font-size:0.85rem;color:{pnl_color};'>"
                    f"{row['盈亏%']:+.2f}%</span>",
                    unsafe_allow_html=True,
                )

            with col5:
                if st.button("🗑️", key=f"del_{row['id']}", help="删除此股票"):
                    db = SessionLocal()
                    try:
                        db.query(UserStock).filter(UserStock.id == row["id"]).delete()
                        db.commit()
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")
                    finally:
                        db.close()

            st.markdown("---")

    # 详细表格
    with st.expander("📋 持仓明细表"):
        table_rows = []
        for row in rows:
            table_rows.append({
                "股票名称": row["股票名称"],
                "代码": row["代码"],
                "最新价": f"{row['最新价']:.2f}",
                "涨跌幅": f"{row['涨跌幅']:+.2f}%",
                "买入价": f"{row['买入价']:.2f}",
                "持仓(股)": row["持仓(股)"],
                "成本": f"¥{row['成本']:,.2f}",
                "市值": f"¥{row['市值']:,.2f}",
                "盈亏": f"¥{row['盈亏']:+,.2f}",
                "盈亏%": f"{row['盈亏%']:+.2f}%",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

# ==================== 添加股票 ====================
st.markdown("---")
st.subheader("➕ 添加股票")
col1, col2, col3, col4 = st.columns([2, 1, 1, 0.8])
with col1:
    new_code = st.text_input("股票代码", placeholder="6位A股代码，如 000001", key="add_code", label_visibility="collapsed")
with col2:
    new_price = st.number_input("买入价格", min_value=0.0, step=0.01, value=0.0, key="add_price", label_visibility="collapsed")
with col3:
    new_shares = st.number_input("持仓股数", min_value=1, step=100, value=100, key="add_shares", label_visibility="collapsed")
with col4:
    add_btn = st.button("➕ 添加", type="primary", use_container_width=True, key="add_btn")

if add_btn:
    new_code = new_code.strip().zfill(6)
    if len(new_code) != 6 or not new_code.isdigit():
        st.error("请输入正确的6位股票代码")
    elif new_price <= 0:
        st.warning("请输入买入价格")
    else:
        db = SessionLocal()
        try:
            exist = (
                db.query(UserStock)
                .filter(UserStock.user_id == user_id, UserStock.stock_code == new_code)
                .first()
            )
            if exist:
                st.warning(f"股票 {new_code} 已添加过")
            else:
                with st.spinner("正在获取股票信息..."):
                    stock_name = get_stock_name(new_code)
                db.add(UserStock(
                    user_id=user_id,
                    stock_code=new_code,
                    stock_name=stock_name,
                    buy_price=new_price,
                    shares=new_shares,
                ))
                db.commit()
                st.success(f"已添加：{stock_name}（{new_code}）")
                st.rerun()
        except Exception as e:
            db.rollback()
            st.error(f"添加失败: {e}")
        finally:
            db.close()

st.markdown("---")
st.caption("📡 数据来源：新浪财经 | 行情延迟约15分钟")
