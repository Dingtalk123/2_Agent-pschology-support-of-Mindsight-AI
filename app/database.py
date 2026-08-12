import sqlite3
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# SQLite 数据库文件位置
DB_PATH = PROJECT_ROOT / "mindsight.db"


def init_db():
    """
    初始化数据库。
    如果 conversation_logs 表不存在，就创建
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                final_response TEXT NOT NULL,
                decision TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                reason TEXT NOT NULL,
                rewrite_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()


def save_conversation(
    session_id: str,
    user_input: str,
    final_response: str,
    decision: str,
    risk_level: str,
    reason: str,
    rewrite_count: int
):
    """
    保存一轮完整对话到 SQLite。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversation_logs (
                session_id,
                user_input,
                final_response,
                decision,
                risk_level,
                reason,
                rewrite_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_input,
                final_response,
                decision,
                risk_level,
                reason,
                rewrite_count
            )
        )

        conn.commit()


def get_recent_context(
    session_id: str,
    limit: int = 5
) -> str:
    """
    查询指定 session 最近的若干轮对话，
    并转换成可以直接放入 LLM Prompt 的文本格式。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_input, final_response
            FROM conversation_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                session_id,
                limit
            )
        )

        rows = cursor.fetchall()

    # SQL 查询出来的是：最新 -> 最旧
    # 给 LLM 阅读时恢复成：最旧 -> 最新
    rows.reverse()

    history_parts = []

    for user_input, final_response in rows:
        history_parts.append(
            f"User: {user_input}\n"
            f"Assistant: {final_response}"
        )

    return "\n\n".join(history_parts)


def get_all_conversations():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM conversation_logs
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()

    return rows