"""
database.py — SQLite (thuky.db) + fallback in-memory storage
"""
import json
import os
import sqlite3
from datetime import datetime

MAX_CONTEXT_LINES = 15
MAX_CONTEXT_CHARS = 5000

# =========================
# DB path & timestamp parsing (AFK duration cần datetime)
# =========================
_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DB_DIR, "thuky.db")


def _decode_timestamp(val):
    if val is None:
        return None
    s = val.decode() if isinstance(val, bytes) else str(val)
    s = s.strip()
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", ""))
        if len(s) >= 19:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


sqlite3.register_converter("TIMESTAMP", _decode_timestamp)

# =========================
# Fallback in-memory storage
# =========================
user_warnings = {}
user_afk = {}
games = {}
quiz_messages = {}
user_info = {}  # {user_id: {'full_name': '...', 'username': '...'}}
session_histories = {}  # {user_id: [{"role": "...", "content": "..."}, ...]}
caro_scores = {}  # {chat_id: {user_id: {"wins": ..., "total": ...}}}
session_scores = {}  # Theo dõi số trận thắng trong một phiên Caro 3x3


# =========================
# SCHEMA
# =========================
def init_db() -> None:
    """Tạo bảng SQLite nếu chưa có (gọi 1 lần lúc khởi động)."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_warnings (
                user_id INTEGER PRIMARY KEY,
                warn_count INTEGER NOT NULL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_afk (
                user_id INTEGER PRIMARY KEY,
                reason TEXT NOT NULL DEFAULT '',
                afk_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_caro_scores (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                caro_wins INTEGER NOT NULL DEFAULT 0,
                total_games INTEGER NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS ai_sessions (
                user_id INTEGER PRIMARY KEY,
                history TEXT NOT NULL DEFAULT '',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_info (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Lỗi init_db: {e}")
    finally:
        conn.close()


# =========================
# DB CONNECTION
# =========================
def get_db_connection():
    """Tạo kết nối đến SQLite (thuky.db)."""
    try:
        return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    except sqlite3.Error as e:
        print(f"Lỗi kết nối DB: {e}")
        return None


# =========================
# CARO SCORES
# =========================
def get_caro_score(user_id: int, chat_id: int = 0) -> dict:
    """Lấy điểm caro của user (wins, total, win_rate) theo từng chat."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT caro_wins, total_games, win_rate
                FROM user_caro_scores
                WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                wins, total, win_rate = row
                return {
                    "wins": wins or 0,
                    "total": total or 0,
                    "win_rate": float(win_rate or 0.0),
                }
        except sqlite3.Error as e:
            print(f"Lỗi DB (get_caro_score): {e}")
    chat_scores = caro_scores.get(chat_id, {})
    record = chat_scores.get(user_id, {"wins": 0, "total": 0})
    wins = record["wins"]
    total = record["total"]
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {"wins": wins, "total": total, "win_rate": win_rate}


def update_caro_score(user_id: int, wins_delta: int, total_delta: int, chat_id: int = 0):
    """Cập nhật điểm Caro của user."""
    if user_id is None:
        return

    chat_scores_map = caro_scores.setdefault(chat_id, {})
    record = chat_scores_map.setdefault(user_id, {"wins": 0, "total": 0})
    record["wins"] += wins_delta
    record["total"] += total_delta
    if record["wins"] < 0:
        record["wins"] = 0
    if record["total"] < 0:
        record["total"] = 0

    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_caro_scores (user_id, chat_id, caro_wins, total_games, win_rate, last_updated)
            VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                caro_wins = MAX(user_caro_scores.caro_wins + excluded.caro_wins, 0),
                total_games = MAX(user_caro_scores.total_games + excluded.total_games, 0),
                win_rate = CASE
                    WHEN MAX(user_caro_scores.total_games + excluded.total_games, 0) = 0 THEN 0
                    ELSE CAST(MAX(user_caro_scores.caro_wins + excluded.caro_wins, 0) AS REAL)
                         / MAX(user_caro_scores.total_games + excluded.total_games, 0) * 100
                END,
                last_updated = CURRENT_TIMESTAMP
            """,
            (user_id, chat_id, wins_delta, total_delta),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except sqlite3.Error as e:
        print(f"Lỗi DB (update_caro_score): {e}")


def record_caro_result(chat_id: int, winner_id=None, loser_id=None, draw_players=None):
    """Cập nhật điểm sau khi kết thúc ván."""
    if draw_players:
        for pid in draw_players:
            update_caro_score(pid, 0, 1, chat_id)
    else:
        if winner_id:
            update_caro_score(winner_id, 1, 1, chat_id)
        if loser_id:
            update_caro_score(loser_id, 0, 1, chat_id)


# =========================
# AI SESSION HISTORY
# =========================
def _trim_history_list(history: list) -> list:
    """Cắt sliding window: xóa phần tử đầu khi vượt giới hạn."""
    trimmed = list(history)
    while len(trimmed) > MAX_CONTEXT_LINES:
        trimmed.pop(0)
    while trimmed and sum(len(str(m.get("content", ""))) for m in trimmed) > MAX_CONTEXT_CHARS:
        trimmed.pop(0)
    return trimmed


def _parse_history_raw(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return _trim_history_list(raw)
    text = raw.decode() if isinstance(raw, bytes) else str(raw)
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return _trim_history_list(data)
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def get_ai_session_history(user_id: int) -> list:
    """Lấy lịch sử phiên AI (list message) từ SQLite hoặc bộ nhớ tạm."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT history FROM ai_sessions WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row and row[0]:
                return _parse_history_raw(row[0])
        except sqlite3.Error as e:
            print(f"Lỗi DB (get_ai_session_history): {e}")
    return _parse_history_raw(session_histories.get(user_id))


def save_ai_session_history(user_id: int, history: list) -> None:
    """Lưu lịch sử phiên AI (JSON list) vào SQLite hoặc bộ nhớ tạm."""
    trimmed = _trim_history_list(history)
    session_histories[user_id] = trimmed
    payload = json.dumps(trimmed, ensure_ascii=False)
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ai_sessions (user_id, history, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                history = excluded.history,
                last_updated = CURRENT_TIMESTAMP
            """,
            (user_id, payload),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except sqlite3.Error as e:
        print(f"Lỗi DB (save_ai_session_history): {e}")
