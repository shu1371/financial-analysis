"""
MySQL 数据库连接模块
"""
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, declarative_base
import config

# 创建数据库引擎
try:
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    engine = None
    SessionLocal = None
    Base = declarative_base()
    print(f"数据库连接失败: {e}")


# ==================== ORM 模型（统一定义，禁止重复） ====================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password = Column(String(100), nullable=False, comment="密码(SHA256)")
    is_admin = Column(Integer, default=0, nullable=False, comment="是否管理员 0=否 1=是")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment="注册时间")


class UserStock(Base):
    __tablename__ = "user_stocks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    stock_code = Column(String(10), nullable=False, comment="股票代码")
    stock_name = Column(String(50), nullable=False, comment="股票名称")
    buy_price = Column(Float, default=0.0, comment="买入价格")
    shares = Column(Integer, default=100, comment="持仓股数")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment="添加时间")


# ==================== 工具函数 ====================


def get_db():
    """获取数据库会话（生成器，用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """测试数据库连接是否正常"""
    if engine is None:
        return False, "数据库引擎未初始化"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "数据库连接成功"
    except Exception as e:
        return False, f"数据库连接失败: {e}"


def init_db():
    """初始化数据库表（创建所有 ORM 模型对应的表）"""
    if engine is None:
        print("数据库引擎未初始化，跳过建表")
        return
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")
