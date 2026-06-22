"""
股票分析模块 - K线图、MA均线、RSI指标、成交量分析
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from utils.helpers import calc_ma, calc_rsi, fetch_stock_hist, get_stock_name

st.set_page_config(
    page_title="股票分析 - 金融数据分析系统",
    page_icon="📈",
    layout="wide",
)

# 登录守卫
if not st.session_state.get("logged_in"):
    st.switch_page("app.py")
    st.stop()

st.title("📈 股票分析")

# 侧边栏输入
with st.sidebar:
    st.header("参数设置")
    stock_code = st.text_input("股票代码", placeholder="例如: 000001", help="输入6位A股代码")
    period = st.selectbox("数据周期", ["日线", "周线", "月线"], index=0)
    days = st.slider("显示天数", min_value=30, max_value=365, value=180, step=30)

    # 指标开关
    st.header("技术指标")
    show_ma = st.checkbox("MA 均线", value=True)
    show_rsi = st.checkbox("RSI 指标", value=True)
    show_volume = st.checkbox("成交量", value=True)

    search_btn = st.button("🔍 查询", type="primary", use_container_width=True)

# 主体区域
if search_btn and stock_code:
    with st.spinner("正在获取数据..."):
        try:
            # 计算日期范围
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            # 获取A股历史数据（带重试 + 数据源回退）
            period_map = {"日线": "daily", "周线": "weekly", "月线": "monthly"}
            df, source = fetch_stock_hist(
                stock_code=stock_code,
                period=period_map[period],
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                st.error("未获取到数据，请检查股票代码是否正确")
            else:
                # 显示中文名称
                stock_name = get_stock_name(stock_code)
                st.subheader(f"{stock_name}（{stock_code}）")

                # 数据源提示
                source_label = "新浪财经" if source == "sina" else "腾讯证券"
                if source == "tencent":
                    st.info(f"数据来源: {source_label}（新浪财经暂不可用）")
                    if period != "日线":
                        st.warning("腾讯源仅支持日线数据")

                df = df.sort_values("date").tail(days)

                # 计算指标
                if show_ma:
                    calc_ma(df)
                if show_rsi:
                    calc_rsi(df)

                # 成交量是否可用（腾讯源可能无成交量）
                has_volume = "volume" in df.columns and show_volume

                # 绘制K线图
                if has_volume:
                    row_heights = [0.6, 0.2, 0.2] if show_rsi else [0.7, 0.3]
                else:
                    row_heights = [0.7, 0.3] if show_rsi else [1.0]

                rows = len(row_heights)
                fig = make_subplots(
                    rows=rows,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    row_heights=row_heights,
                )

                # K线
                fig.add_trace(
                    go.Candlestick(
                        x=df["date"],
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name="K线",
                    ),
                    row=1,
                    col=1,
                )

                # 均线
                ma_colors = {5: "blue", 10: "orange", 20: "purple", 60: "green"}
                if show_ma:
                    for p, color in ma_colors.items():
                        col_name = f"MA{p}"
                        if col_name in df.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=df["date"],
                                    y=df[col_name],
                                    mode="lines",
                                    name=col_name,
                                    line=dict(color=color, width=1.2),
                                ),
                                row=1,
                                col=1,
                            )

                current_row = 2

                # 成交量
                if has_volume:
                    colors = [
                        "red" if o < c else "green"
                        for o, c in zip(df["open"], df["close"])
                    ]
                    fig.add_trace(
                        go.Bar(
                            x=df["date"],
                            y=df["volume"],
                            name="成交量",
                            marker_color=colors,
                            opacity=0.5,
                        ),
                        row=current_row,
                        col=1,
                    )
                    current_row += 1

                # RSI
                if show_rsi and "RSI" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["date"],
                            y=df["RSI"],
                            mode="lines",
                            name="RSI(14)",
                            line=dict(color="blue", width=1.5),
                        ),
                        row=current_row,
                        col=1,
                    )
                    # 超买超卖线
                    for level, color, label in [
                        (70, "red", "超买线"),
                        (30, "green", "超卖线"),
                    ]:
                        fig.add_hline(
                            y=level,
                            line_dash="dash",
                            line_color=color,
                            opacity=0.5,
                            row=current_row,
                            col=1,
                        )

                # 布局微调
                fig.update_layout(
                    title=f"{stock_name}（{stock_code}）股票走势图",
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                    height=600,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                fig.update_yaxes(title_text="价格", row=1, col=1)
                if has_volume:
                    fig.update_yaxes(title_text="成交量", row=2, col=1)
                if show_rsi:
                    rsi_row = 3 if has_volume else 2
                    fig.update_yaxes(title_text="RSI", range=[0, 100], row=rsi_row, col=1)

                st.plotly_chart(fig, use_container_width=True)

                # 数据表格
                with st.expander("📋 查看原始数据"):
                    display_df = df.copy()
                    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
                    st.dataframe(
                        display_df.tail(20),
                        use_container_width=True,
                        hide_index=True,
                    )

        except Exception as e:
            st.error(f"获取数据出错: {e}")
            st.info("常见原因：① 网络不稳定（已自动重试3次）② 股票代码不存在 ③ 数据源暂时不可用")
            st.info("建议：请稍后重试，或尝试其他股票代码（如 000001、600519）")

elif search_btn and not stock_code:
    st.warning("请输入股票代码")
else:
    # 初始占位
    st.info("👈 请在侧边栏输入股票代码并点击查询")
    st.markdown(
        """
    **使用说明：**
    1. 输入 6 位 A 股代码（如 `000001` 平安银行）
    2. 选择数据周期和显示天数
    3. 勾选需要展示的技术指标
    4. 点击 **查询** 按钮
    """
    )
