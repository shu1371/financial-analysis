# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 运行与开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用（默认 http://localhost:8501）
streamlit run app.py
```

## 架构概览

这是一个基于 Streamlit 多页面的金融数据分析系统，无前端框架、无后端 API，全部由 Streamlit 原生渲染。

**数据流：** 用户输入股票代码 → `utils/helpers.py::fetch_stock_hist()` → AkShare → Plotly 图表渲染

**多页面机制：** Streamlit 自动扫描 `pages/` 目录，按文件名排序生成侧边栏导航。`app.py` 是首页，每个子页面必须独立调用 `st.set_page_config()`（Streamlit 要求）。

## 关键设计决策

### 双数据源回退

`fetch_stock_hist()` 优先使用新浪财经源（`ak.stock_zh_a_daily`，字段含 date/open/close/high/low/volume/amount），失败则回退到腾讯源（`ak.stock_zh_a_hist_tx`）。新浪源在某些网络环境下会被阻断，腾讯源作为稳定备选。函数返回 `(DataFrame, source_name)` 元组——调用方必须解包两个值。

腾讯源**无 `volume` 字段**，仅含 `date/open/close/high/low/amount`。各页面在绘制成交量图前需检查 `"volume" in df.columns`。

### 股票名称缓存

`get_stock_name()` 首次调用时通过 `ak.stock_zh_a_spot()` 批量拉取全量 A 股代码→名称映射，存入模块级 `_stock_name_cache` dict。同时缓存带前缀（sh/sz）和无前缀（6 位纯数字）两种 key，因此 O(1) 查找不需网络请求。

### SSL 兼容处理

`utils/helpers.py` 模块顶部设置了全局 SSL 忽略（`ssl._create_unverified_context`），并在导入 akShare 前执行。这是因为国内金融数据源（新浪、腾讯）的 HTTPS 证书在部分 Windows 环境下会导致 `RemoteDisconnected` 错误。任何新增的数据获取函数都应放在该模块中以确保 SSL 设置先生效。

### 数据库模块

- `database/mysql_conn.py` — SQLAlchemy ORM 引擎，`User` 和 `UserStock` 模型，`init_db()` 建表并执行 `ALTER TABLE users MODIFY password VARCHAR(256)` 兼容迁移，`test_connection()` 健康检查
- `utils/database.py` — 原生 pymysql 连接（`get_db_connection()`），用于游戏中心等需要参数化 SQL 的场景；`ensure_game_scores_table()` 建表

### MySQL 可选运行

用户模块页面（`pages/4_👤_用户模块.py`）在 MySQL 不可用时会优雅降级：展示错误提示但页面不崩溃，登录注册按钮在检测到数据库未连接时不会执行实际查询。`init_db()` 调用包裹了 try-except。

### 游戏中心

`pages/5_🎮_游戏中心.py` 包含两个游戏，均通过 JavaScript 注入实现键盘方向键操控：

- **贪吃蛇炒股** — 15×15 网格，吃到 💰 股价 +5%，吃到 💣 股价 -10%。JS `setInterval` 实现 280ms 自动踏步，方向键改变方向。`#snake-auto-move` 隐藏 div 标记模式。
- **合成方块资产 2048** — 标准 2048 合并逻辑，通关/失败/手动结束均记录用时到排行榜。

方向按钮渲染为 Streamlit button，JS 通过 `document.querySelectorAll('button')` 查找并 `.click()`。排行榜使用参数化 `%s` 查询，INSERT/UPDATE 仅在分数更高时更新。**ORDER BY 方向通过白名单校验后拼接**（`ASC`/`DESC`），禁止直接 f-string 注入。

游戏结束后通过 URL query params 回传成绩。会话恢复时 2 小时内免密自动登录（仅校验用户名），超时后使用 `verify_password()` 验证密码。

### 安全设计

#### 密码哈希 (PBKDF2-SHA256)

在 `utils/helpers.py` 中集中管理：

| 函数 | 用途 |
|------|------|
| `hash_password(password)` | PBKDF2-HMAC-SHA256，600k 迭代，`secrets.token_hex(16)` 随机盐。输出格式：`pbkdf2$<salt>$<hash>` |
| `verify_password(password, stored)` | 验证密码。旧 SHA256+static-salt 格式自动兼容，使用 `secrets.compare_digest` 防时序攻击 |
| `needs_password_upgrade(stored)` | 检测是否为旧格式（无 `pbkdf2$` 前缀），登录时自动升级 |
| `validate_password_strength(password)` | 返回 `(bool, msg)`：≥8 字符 + 大写 + 小写 + 数字 |

**旧格式兼容机制**：`app.py` 登录成功且 `needs_password_upgrade()` 为 True 时自动调用 `hash_password()` 重哈希并写回 DB，对用户透明。游戏中心的恢复登录表单同理。

**密码长度**：`users.password` 列已扩至 `VARCHAR(256)`，`init_db()` 中 ALTER TABLE 自动迁移旧表。

#### SQL 注入防护

- **全项目**：所有 `cursor.execute()` 使用 `%s` 参数化占位符，禁止 f-string / .format / % 拼接用户输入
- **ORDER BY 例外**：游戏中心排行榜的排序方向无法参数化，采用白名单校验 `if order not in ("ASC", "DESC")` 后拼接

#### XSS 防护

在 `utils/helpers.py` 中提供两个转义函数：

| 函数 | 实现 | 使用位置 |
|------|------|----------|
| `escape_html(text)` | `html.escape(str(text), quote=True)` | `pages/1` 股票名称/代码嵌入 HTML；`pages/5` 游戏卡片 username |
| `escape_js(text)` | 转义 `\ ' " < > &` 为 `\xNN` 形式 | — |

此外 `app.py` 登录后 username 写入 localStorage 使用 `json.dumps()` 生成安全的 JS 字符串字面量。

**规则**：任何 `st.markdown(..., unsafe_allow_html=True)` 或 `st.components.v1.html()` 中包含来自用户/外部数据源的字符串时，必须先用对应函数转义。

### 页面独立性

每个页面文件顶部都有完整的 import 和 `st.set_page_config()`。页面之间不共享状态（除 `st.session_state` 外），可独立测试。

## 配置文件

`config.py` 包含 MySQL 连接参数和数据库 URL 构造。**此文件已加入 `.gitignore`，不会被提交。** 新克隆者需复制 `config.example.py` → `config.py` 并填写实际值。

默认凭据仅用于本地开发，部署前务必修改 `DB_PASSWORD`。建议使用环境变量：`os.environ.get("DB_PASSWORD", "默认值")`。
