"""
游戏中心 - 炒股贪吃蛇 & 合成方块1024资产
"""
import streamlit as st
import pymysql
import config
from datetime import datetime
from utils.helpers import hash_password, verify_password, escape_html, escape_js

st.set_page_config(
    page_title="游戏中心 - 金融数据分析系统",
    page_icon="🎮",
    layout="wide",
)

# ==================== 数据库工具 ====================

def get_db():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def save_score(game_type: str, username: str, score: float, higher_better: bool = True, max_tile: int = None):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if game_type == "merge1024" and max_tile is not None:
                # merge1024: 比较 max_tile（越大越好），相同则比较时间（越短越好）
                cur.execute(
                    "SELECT score, max_tile FROM game_scores WHERE username = %s AND game_type = %s",
                    (username, game_type),
                )
                row = cur.fetchone()
                if row:
                    old_time = row["score"]
                    old_tile = row["max_tile"] or 0
                    if max_tile > old_tile or (max_tile == old_tile and score < old_time):
                        cur.execute(
                            "UPDATE game_scores SET score = %s, max_tile = %s, last_updated = NOW() "
                            "WHERE username = %s AND game_type = %s",
                            (score, max_tile, username, game_type),
                        )
                        conn.commit()
                        return True, "update"
                    else:
                        return False, "no_better"
                else:
                    cur.execute(
                        "INSERT INTO game_scores (username, game_type, score, max_tile, last_updated) "
                        "VALUES (%s, %s, %s, %s, NOW())",
                        (username, game_type, score, max_tile),
                    )
                    conn.commit()
                    return True, "insert"
            else:
                cur.execute(
                    "SELECT score FROM game_scores WHERE username = %s AND game_type = %s",
                    (username, game_type),
                )
                row = cur.fetchone()
                if row:
                    old_score = row["score"]
                    if higher_better and score > old_score:
                        cur.execute(
                            "UPDATE game_scores SET score = %s, last_updated = NOW() "
                            "WHERE username = %s AND game_type = %s",
                            (score, username, game_type),
                        )
                        conn.commit()
                        return True, "update"
                    elif not higher_better and score < old_score:
                        cur.execute(
                            "UPDATE game_scores SET score = %s, last_updated = NOW() "
                            "WHERE username = %s AND game_type = %s",
                            (score, username, game_type),
                        )
                        conn.commit()
                        return True, "update"
                    else:
                        return False, "no_better"
                else:
                    cur.execute(
                        "INSERT INTO game_scores (username, game_type, score, last_updated) "
                        "VALUES (%s, %s, %s, NOW())",
                        (username, game_type, score),
                    )
                    conn.commit()
                    return True, "insert"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ==================== 接收游戏返回结果（URL query params） ====================
# 必须在登录守卫之前处理，确保成绩始终入库
if "game_type" in st.query_params:
    game_type = st.query_params["game_type"]
    try:
        score = float(st.query_params["score"])
    except (ValueError, TypeError):
        score = 0
    save_username = st.session_state.get("username") or st.query_params.get("username", "")

    if not save_username or save_username == "anonymous":
        st.toast("无法识别用户身份，成绩未保存", icon="⚠️")
    else:
        if game_type == "snake":
            ok, action = save_score("snake", save_username, score, higher_better=True)
            if ok and action in ("insert", "update"):
                st.toast(f"🐍 成绩已记录！最终股价: ¥{score:.2f}", icon="✅")
            elif action == "no_better":
                st.toast(f"🐍 最终股价: ¥{score:.2f}（未超过历史最佳，不更新）", icon="ℹ️")
            else:
                st.toast(f"🐍 最终股价: ¥{score:.2f}（保存失败: {action}）", icon="⚠️")

        elif game_type == "merge1024":
            max_tile = int(st.query_params.get("max_tile", 0))
            if score >= 0 and max_tile >= 128:
                ok, action = save_score("merge1024", save_username, score, max_tile=max_tile)
                mins, secs = divmod(int(score), 60)
                time_str = f"{mins}分{secs}秒"
                if ok and action in ("insert", "update"):
                    st.toast(f"🧊 合成{max_tile}元资产！用时: {time_str}，成绩已记录", icon="🎉")
                elif action == "no_better":
                    st.toast(f"🧊 合成{max_tile}元资产！用时: {time_str}（未超过历史最佳，不更新）", icon="ℹ️")
                else:
                    st.toast(f"🧊 成绩保存失败: {action}", icon="⚠️")
            else:
                st.toast(f"🧊 最大合成{max_tile}元，未达到128元门槛，成绩不记录", icon="ℹ️")

    # 游戏返回时自动恢复登录状态
    if not st.session_state.get("logged_in") and save_username and save_username != "anonymous":
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (save_username,))
                user_row = cur.fetchone()
                if user_row:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = save_username
                    st.session_state["user_id"] = user_row["id"]
        except Exception:
            pass
        finally:
            conn.close()

    st.query_params.clear()
    st.rerun()


# ==================== 登录守卫（带会话恢复） ====================
if not st.session_state.get("logged_in"):
    recover_user = st.query_params.get("recover_user")

    if recover_user:
        # 检查是否在 2 小时内，是则自动恢复
        auto_login = False
        ts_str = st.query_params.get("ts", "")
        if ts_str:
            try:
                elapsed = (datetime.now().timestamp() * 1000 - float(ts_str)) / 1000 / 3600
                if elapsed < 2:
                    auto_login = True
            except (ValueError, TypeError):
                pass

        if auto_login:
            # 2 小时内自动恢复，无需密码
            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE username = %s", (recover_user,))
                    user_row = cur.fetchone()
                    if user_row:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = recover_user
                        st.session_state["user_id"] = user_row["id"]
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("用户不存在")
            except Exception as e:
                st.error(f"恢复失败: {e}")
            finally:
                conn.close()
        else:
            # 超过 2 小时，需要密码验证
            st.title("🎮 游戏中心")
            st.info(f"欢迎回来，**{recover_user}**！会话已过期，请重新输入密码。")
            with st.form("recover_form"):
                pwd = st.text_input("密码", type="password", key="recover_pwd")
                c1, c2 = st.columns(2)
                with c1:
                    submit_recover = st.form_submit_button("恢复登录", type="primary", use_container_width=True)
                with c2:
                    submit_switch = st.form_submit_button("切换账号", use_container_width=True)

                if submit_recover:
                    if not pwd:
                        st.warning("请输入密码")
                    else:
                        conn = get_db()
                        try:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "SELECT id, password FROM users WHERE username = %s",
                                    (recover_user,),
                                )
                                user_row = cur.fetchone()
                                if user_row and verify_password(pwd, user_row["password"]):
                                    # 旧格式自动升级
                                    if "$" not in user_row["password"]:
                                        cur.execute(
                                            "UPDATE users SET password = %s WHERE id = %s",
                                            (hash_password(pwd), user_row["id"]),
                                        )
                                        conn.commit()
                                    st.session_state["logged_in"] = True
                                    st.session_state["username"] = recover_user
                                    st.session_state["user_id"] = user_row["id"]
                                    st.query_params.clear()
                                    st.rerun()
                                else:
                                    st.error("密码错误")
                        except Exception as e:
                            st.error(f"恢复失败: {e}")
                        finally:
                            conn.close()

                if submit_switch:
                    st.session_state["redirect_after_login"] = "pages/5_🎮_游戏中心.py"
                    st.switch_page("app.py")
        st.stop()

    # 尝试从 localStorage 恢复用户名
    st.components.v1.html("""
    <script>
    (function() {
        if (window.location.search.indexOf('recover_user') !== -1) return;
        var u = localStorage.getItem('fa_username');
        var l = localStorage.getItem('fa_logged_in');
        var ts = localStorage.getItem('fa_timestamp');
        if (u && l === '1') {
            var url = '?recover_user=' + encodeURIComponent(u);
            if (ts) url += '&ts=' + ts;
            window.location.search = url;
        }
    })();
    </script>
    """, height=0)

    # 未找到 localStorage，显示手动登录入口
    st.title("🎮 游戏中心")
    st.warning("请先登录以访问游戏中心")
    if st.button("🔐 前往登录", type="primary", use_container_width=True):
        st.session_state["redirect_after_login"] = "pages/5_🎮_游戏中心.py"
        st.switch_page("app.py")
    st.stop()

username = st.session_state.get("username", "")


def get_leaderboard(game_type: str, order_desc: bool = True):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if game_type == "merge1024":
                cur.execute(
                    "SELECT username, score, max_tile, last_updated FROM game_scores "
                    "WHERE game_type = %s ORDER BY max_tile DESC, score ASC LIMIT 10",
                    (game_type,),
                )
            else:
                order = "DESC" if order_desc else "ASC"
                if order not in ("ASC", "DESC"):
                    order = "DESC"
                cur.execute(
                    "SELECT username, score, last_updated FROM game_scores "
                    "WHERE game_type = %s ORDER BY score " + order + " LIMIT 10",
                    (game_type,),
                )
            return cur.fetchall()
    except Exception:
        return []
    finally:
        conn.close()


# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("📊 金融数据分析")
    st.markdown(f"👤 **{username}**")
    if st.button("🚪 退出", use_container_width=True):
        for key in ["logged_in", "username", "user_id"]:
            st.session_state[key] = False if key == "logged_in" else ("" if key == "username" else None)
        st.components.v1.html("""
        <script>
        localStorage.removeItem('fa_username');
        localStorage.removeItem('fa_logged_in');
        localStorage.removeItem('fa_timestamp');
        </script>
        """, height=0)
        st.switch_page("app.py")

# ==================== 主页面 ====================
st.title("🎮 游戏中心")

# 排行榜（每10分钟自动刷新）
@st.fragment(run_every=600)
def leaderboards():
    snake_board = get_leaderboard("snake", order_desc=True)
    merge_board = get_leaderboard("merge1024", order_desc=False)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🐍 炒股贪吃蛇排行榜")
        if snake_board:
            rows = [{
                "排名": i + 1,
                "玩家": r["username"],
                "股价 (¥)": f"{r['score']:.2f}",
                "时间": r["last_updated"].strftime("%m-%d %H:%M") if isinstance(r["last_updated"], datetime) else str(r["last_updated"])[:16],
            } for i, r in enumerate(snake_board)]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("暂无记录，快来玩一局吧！")

    with col2:
        st.subheader("🧊 合成方块1024排行榜")
        if merge_board:
            rows = [{
                "排名": i + 1,
                "玩家": r["username"],
                "用时": f"{int(r['score'] // 60)}分{int(r['score'] % 60)}秒",
                "最大资产": f"{r.get('max_tile', '?')}元",
                "时间": r["last_updated"].strftime("%m-%d %H:%M") if isinstance(r["last_updated"], datetime) else str(r["last_updated"])[:16],
            } for i, r in enumerate(merge_board)]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("暂无记录，快来挑战吧！")

    if st.button("🔄 刷新排行榜", key="refresh_lb"):
        pass  # 按钮本身触发 fragment 重跑

leaderboards()

st.markdown("---")

# 游戏卡片
c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div style="background:#161b22; border:2px solid #3fb950; border-radius:14px; padding:28px; text-align:center;">
        <h2 style="color:#3fb950; margin-bottom:12px;">🐍 炒股贪吃蛇</h2>
        <p style="color:#8b949e; font-size:0.9rem; line-height:1.8;">
            操控贪吃蛇在15x15股市棋盘上生存<br>
            💰 吃到金币 → 股价上涨 5%<br>
            💣 碰到炸弹 → 股价下跌 10%<br>
            右上角实时查看股价走势图<br>
            存活越久，股价越高，排名越高！
        </p>
        <a href="/app/static/snake_game.html?username={escape_html(username)}" target="_blank" rel="opener"
           style="display:inline-block;margin-top:16px;padding:12px 40px;background:#238636;
                  color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;font-size:1rem;">
           🎮 在新窗口开始游戏
        </a>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background:#161b22; border:2px solid #f0c040; border-radius:14px; padding:28px; text-align:center;">
        <h2 style="color:#f0c040; margin-bottom:12px;">🧊 合成方块 1024 资产</h2>
        <p style="color:#8b949e; font-size:0.9rem; line-height:1.8;">
            经典2048玩法，资产主题<br>
            2元 → 4元 → 8元 → ... → 1024元<br>
            合成128元及以上即可上榜<br>
            按最大资产排名，相同时用时短优先
        </p>
        <a href="/app/static/merge1024_game.html?username={escape_html(username)}" target="_blank" rel="opener"
           style="display:inline-block;margin-top:16px;padding:12px 40px;background:#d4a72c;
                  color:#000;border-radius:8px;text-decoration:none;font-weight:bold;font-size:1rem;">
           🎮 在新窗口开始游戏
        </a>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "点击按钮在新标签页打开游戏。游戏结束后成绩自动提交到此页面更新排行榜。"
    "点击「刷新排行榜」可立即查看最新排名。排行榜每 10 分钟自动刷新。"
    "成绩仅在超过个人历史最佳时更新。"
)
