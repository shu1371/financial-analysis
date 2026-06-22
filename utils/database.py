"""
数据库连接工具 — 提供原生 pymysql 连接（参数化查询）
"""
import pymysql
import config


def get_db_connection():
    """获取原生 pymysql 数据库连接"""
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_game_scores_table():
    """确保 game_scores 表存在"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS game_scores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    game_type VARCHAR(50) NOT NULL,
                    score FLOAT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    max_tile INT DEFAULT NULL COMMENT '最大合成资产(仅merge1024)',
                    UNIQUE KEY uk_user_game (username, game_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            # 兼容旧表：如果表已存在但缺少 max_tile 字段，则添加
            try:
                cur.execute(
                    """
                    ALTER TABLE game_scores
                    ADD COLUMN max_tile INT DEFAULT NULL COMMENT '最大合成资产(仅merge1024)'
                    """
                )
            except Exception:
                pass  # 字段已存在或其他错误忽略
        conn.commit()
    finally:
        conn.close()


def ensure_users_admin_column():
    """兼容旧表：确保 users 表存在 is_admin 字段"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    ALTER TABLE users
                    ADD COLUMN is_admin INT NOT NULL DEFAULT 0 COMMENT '是否管理员 0=否 1=是'
                    """
                )
                conn.commit()
                print("[OK] users.is_admin 字段已添加")
            except Exception:
                pass  # 字段已存在或其他错误忽略
    finally:
        conn.close()
