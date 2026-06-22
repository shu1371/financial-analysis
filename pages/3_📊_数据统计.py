"""
数据统计模块 - 收益率分析、波动率分析、最大涨跌幅统计
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.helpers import fetch_stock_hist, get_stock_name

st.set_page_config(
    page_title="数据统计 - 金融数据分析系统",
    page_icon="📊",
    layout="wide",
)

# 登录守卫
if not st.session_state.get("logged_in"):
    st.switch_page("app.py")
    st.stop()

st.title("📊 数据统计")

# 侧边栏
with st.sidebar:
    st.header("参数设置")
    stock_code = st.text_input("股票代码", placeholder="例如: 000001")
    days = st.slider("统计天数", 30, 365, 180, 30)

    analyze_btn = st.button("📐 开始分析", type="primary", use_container_width=True)

if analyze_btn and stock_code:
    with st.spinner("正在获取并分析数据..."):
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df, source = fetch_stock_hist(
                stock_code=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                st.error("未获取到数据，请检查股票代码")
            else:
                stock_name = get_stock_name(stock_code)
                st.subheader(f"{stock_name}（{stock_code}）")

                if source == "tencent":
                    st.info("数据来源: 腾讯证券（新浪财经暂不可用）")

                df = df.sort_values("date").tail(days).copy()

                # 计算日收益率
                df["daily_return"] = df["close"].pct_change() * 100

                # ==================== 指标计算 ====================

                # 累计收益率
                total_return = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

                # 年化波动率（日收益率标准差 * sqrt(252)）
                daily_vol = df["daily_return"].std()
                annual_vol = daily_vol * (252**0.5)

                # 最大涨幅 / 最大跌幅
                max_up = df["daily_return"].max()
                max_down = df["daily_return"].min()

                # 最大回撤
                cummax = df["close"].cummax()
                drawdown = (df["close"] - cummax) / cummax * 100
                max_drawdown = drawdown.min()

                # 胜率
                win_rate = (df["daily_return"] > 0).sum() / df["daily_return"].notna().sum() * 100

                # ==================== 指标卡片 ====================
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("累计收益率", f"{total_return:.2f}%")
                col2.metric("年化波动率", f"{annual_vol:.2f}%")
                col3.metric("最大日涨幅", f"{max_up:.2f}%")
                col4.metric("最大日跌幅", f"{max_down:.2f}%")

                col5, col6 = st.columns(2)
                col5.metric("最大回撤", f"{max_drawdown:.2f}%")
                col6.metric("日胜率", f"{win_rate:.1f}%")

                # ==================== 图表 ====================

                tab1, tab2, tab3 = st.tabs(["收益率曲线", "波动率分布", "涨跌幅统计"])

                with tab1:
                    # 累计收益曲线
                    df["cum_return"] = (1 + df["daily_return"] / 100).cumprod()
                    fig1 = go.Figure()
                    fig1.add_trace(
                        go.Scatter(
                            x=df["date"],
                            y=(df["cum_return"] - 1) * 100,
                            mode="lines",
                            fill="tozeroy",
                            name="累计收益率",
                            line=dict(color="#2E86AB", width=1.5),
                        )
                    )
                    fig1.update_layout(
                        title=f"{stock_name}（{stock_code}）累计收益率曲线",
                        template="plotly_white",
                        height=400,
                        yaxis_title="收益率 (%)",
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    # 收益率直方图
                    valid_returns = df["daily_return"].dropna()
                    fig2 = go.Figure()
                    fig2.add_trace(
                        go.Histogram(
                            x=valid_returns,
                            nbinsx=30,
                            name="日收益率分布",
                            marker_color="#A23B72",
                            opacity=0.75,
                        )
                    )
                    fig2.update_layout(
                        title=f"{stock_name}（{stock_code}）日收益率分布",
                        template="plotly_white",
                        height=400,
                        xaxis_title="收益率 (%)",
                        yaxis_title="频次",
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    # 涨跌幅条形图（最近20日）
                    recent = df.tail(20).copy()
                    colors = [
                        "red" if v > 0 else "green"
                        for v in recent["daily_return"]
                    ]
                    fig3 = go.Figure()
                    fig3.add_trace(
                        go.Bar(
                            x=recent["date"],
                            y=recent["daily_return"],
                            marker_color=colors,
                            name="日收益率",
                        )
                    )
                    fig3.update_layout(
                        title=f"{stock_name}（{stock_code}）近20日涨跌幅",
                        template="plotly_white",
                        height=400,
                        xaxis_title="日期",
                        yaxis_title="涨跌幅 (%)",
                    )
                    st.plotly_chart(fig3, use_container_width=True)

                # 原始数据
                with st.expander("📋 统计数据详情"):
                    stats_df = pd.DataFrame(
                        {
                            "指标": [
                                "累计收益率(%)",
                                "年化波动率(%)",
                                "最大日涨幅(%)",
                                "最大日跌幅(%)",
                                "最大回撤(%)",
                                "日胜率(%)",
                                "均值(%)",
                                "标准差(%)",
                            ],
                            "数值": [
                                f"{total_return:.2f}",
                                f"{annual_vol:.2f}",
                                f"{max_up:.2f}",
                                f"{max_down:.2f}",
                                f"{max_drawdown:.2f}",
                                f"{win_rate:.1f}",
                                f"{df['daily_return'].mean():.2f}",
                                f"{daily_vol:.2f}",
                            ],
                        }
                    )
                    st.dataframe(stats_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"获取数据出错: {e}")
            st.info("常见原因：① 网络不稳定（已自动重试3次）② 股票代码不存在 ③ 数据源暂时不可用")

elif analyze_btn and not stock_code:
    st.warning("请输入股票代码")
else:
    st.info("👈 请在侧边栏输入股票代码并点击开始分析")
