"""
utils/helpers.py — Utility functions: format_duration, resolve_user_identifier, get_member_name, is_board_full
"""
import sqlite3
from datetime import datetime
from database import get_db_connection


def format_duration(delta: datetime) -> str:
    """Chuyển timedelta thành chuỗi tiếng Việt dễ hiểu."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if minutes:
        parts.append(f"{minutes} phút")
    if seconds and not parts:
        parts.append(f"{seconds} giây")
    return " ".join(parts) if parts else "0 giây"


def resolve_user_identifier(identifier: str) -> int | None:
    """Chuyển @username hoặc ID thành user_id."""
    if not identifier:
        return None
    ident = identifier.strip()
    if ident.startswith("@"):
        ident = ident[1:]
    if not ident:
        return None
    if ident.lstrip("-").isdigit():
        try:
            return int(ident)
        except ValueError:
            return None
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM user_info WHERE LOWER(username) = ? LIMIT 1",
                (ident.lower(),),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return row[0]
        except sqlite3.Error as e:
            print(f"Lỗi DB (resolve_user_identifier): {e}")
    return None


async def get_member_name(context, chat_id, user_id, fallback="Player"):
    """Lấy tên thành viên từ chat, fallback nếu lỗi."""
    if not user_id:
        return fallback
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.user.first_name
    except:
        return fallback


def is_board_full(board) -> bool:
    """Kiểm tra bàn cờ đã đầy chưa."""
    return all(cell != " " for row in board for cell in row)
