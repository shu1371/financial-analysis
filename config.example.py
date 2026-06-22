"""
系统配置文件（模板）
复制此文件为 config.py 并填写实际值
"""
# MySQL 数据库配置
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "请在此填写数据库密码"
DB_NAME = "financial_analysis"

# 数据库连接URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 页面配置
PAGE_TITLE = "金融数据分析系统"
PAGE_ICON = "📊"
LAYOUT = "wide"
