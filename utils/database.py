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
        conn.commit()
    finally:
        conn.close()
