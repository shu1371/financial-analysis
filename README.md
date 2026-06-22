# 📊 金融数据分析系统 — 第4版

基于 Streamlit 的 A 股金融数据分析与可视化平台，支持 K 线/趋势图绘制、技术指标分析、用户管理与游戏化互动体验。

---

## 🚀 功能特性

| 模块 | 说明 |
|------|------|
| 📈 **股票数据查询** | 支持 A 股历史行情查询，双数据源（新浪/腾讯）自动回退 |
| 📉 **K 线/趋势图** | 交互式 Plotly 图表，含成交量、均线等技术指标 |
| 👤 **用户模块** | 注册/登录体系，支持个人股票收藏管理（MySQL 后端） |
| 🎮 **游戏中心** | 贪吃蛇炒股 + 合成方块资产 2048，寓教于乐 |

---

## 🛠 技术栈

- **前端/框架**：Streamlit（纯 Python 原生渲染，无前后端分离）
- **数据获取**：AkShare（新浪财经 + 腾讯财经双源）
- **图表库**：Plotly
- **数据库**：MySQL（可选，用户模块支持离线降级运行）

---

## 📦 安装与运行

### 1. 克隆仓库
```bash
git clone https://github.com/Qk-max/financial-analysis.git
cd financial-analysis
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库（可选）
编辑 `config.py`，填写你的 MySQL 连接信息：
```python
DB_PASSWORD = "你的密码"  # 必填，其他保持默认即可
```

### 4. 启动应用
```bash
streamlit run app.py
```

应用默认运行在 http://localhost:8501

---

## 📁 项目结构

```
financial-analysis/
├── app.py                  # 应用入口（首页）
├── config.py               # 配置文件（数据库连接等）
├── requirements.txt        # Python 依赖
├── CLAUDE.md               # 项目开发文档
├── database/
│   └── mysql_conn.py       # SQLAlchemy ORM 模型与连接
├── utils/
│   ├── helpers.py          # 股票数据获取（AkShare 双源回退）
│   └── database.py         # pymysql 原生连接（游戏排行榜）
└── pages/                  # Streamlit 多页面目录
    ├── 1_📈_股票数据查询.py
    ├── 2_📉_K线_趋势图.py
    ├── 3_📊_技术指标分析.py
    ├── 4_👤_用户模块.py
    └── 5_🎮_游戏中心.py
```

---

## 🔑 关键设计

- **双数据源回退**：优先新浪财经，网络受阻时自动切换腾讯源，确保行情数据稳定获取
- **股票名称缓存**：首次启动时批量缓存全量 A 股代码→名称映射，后续查询零延迟
- **MySQL 可选运行**：用户模块在无数据库时自动降级，页面不崩溃、功能不中断

---

## 📝 更新日志

| 版本 | 更新内容 |
|------|---------|
| v4.0 | 完善文档 + 项目整理（第4版） |
| v3.0 | 移除游戏中心 + 项目优化 |
| v2.0 | 重构登录体系 + 双数据源 + 密码哈希 |
| v1.0 | 初始化：金融数据分析系统 + 游戏中心 |

---

## 📄 License

MIT License
