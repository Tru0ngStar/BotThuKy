"""
handlers/misc.py — Misc commands: /start, /news, /tt, /daoly, /quiz, /afk, /ping, /restart
"""
import random
import requests
import feedparser
import sys
import time
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import RSS_URL, QUOTES, QUIZ_QUESTIONS
import sqlite3
from database import get_db_connection, user_afk, quiz_messages
from utils.helpers import format_duration

_BOT_START_TIME = datetime.now()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start"""
    user = update.effective_user
    welcome_text = f"""👋 Chào bé {user.full_name}🤓!

Một số lệnh cơ bản:
📰 /news - Báo mới từ VnExpress
🌦️ /tt - thời tiết
🎲 /daoly - Đạo lý từ thư ký
📥 /download - Tải video YT/TikTok
🎵 /mp3 - Tải nhạc MP3

Trò chơi giải trí 😴:
♟️ /caro - Đánh Caro cùng nhau
♟️ /xo - Reply để thách đấu caro"""
    await update.message.reply_text(welcome_text)


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tin tức"""
    msg = await update.message.reply_text("📰 Loading...")
    try:
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            await msg.edit_text("❌ No news")
            return
        news_text = "📰 **Tin tức mới:**\n\n"
        for i, entry in enumerate(feed.entries[:10], 1):
            news_text += f"{i}. [{entry.title}]({entry.link})\n"
        await msg.edit_text(news_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /tt <location>"""
    if not context.args:
        await update.message.reply_text("❌ /tt Ha Noi")
        return
    location = "+".join(context.args)
    try:
        url = f"https://wttr.in/{location}?format=3"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            await update.message.reply_text(f"🌤️ {resp.text}")
        else:
            await update.message.reply_text("❌ Lỗi lấy thời tiết")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")


async def daoly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gửi đạo lý"""
    quote = random.choice(QUOTES)
    if update.message.reply_to_message:
        target_name = update.message.reply_to_message.from_user.full_name
    else:
        target_name = update.effective_user.full_name
    message_text = (
        f"Đây là đạo lý hôm nay dành cho {target_name}:\n\n"
        f"_{quote}_\n\n"
        "Đạo lý bởi Thư ký 🤓"
    )
    await update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN)
    try:
        await update.message.delete()
    except:
        pass


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gửi câu quiz"""
    user_id = update.effective_user.id
    q = random.choice(QUIZ_QUESTIONS)
    context.user_data['quiz_answer'] = q['a'].lower()
    quiz_msg = await update.message.reply_text(f"❓ {q['q']}")
    if user_id not in quiz_messages:
        quiz_messages[user_id] = []
    quiz_messages[user_id].append(update.message.message_id)
    quiz_messages[user_id].append(quiz_msg.message_id)
    context.job_queue.run_once(
        delete_quiz_messages, 300,
        data={'user_id': user_id, 'chat_id': update.effective_chat.id}
    )


async def delete_quiz_messages(context: ContextTypes.DEFAULT_TYPE):
    """Xóa quiz sau 5 phút"""
    job = context.job
    user_id = job.data['user_id']
    chat_id = job.data['chat_id']
    if user_id in quiz_messages:
        for msg_id in quiz_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except:
                pass
        del quiz_messages[user_id]


async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Đặt trạng thái AFK"""
    user = update.effective_user
    reason = " ".join(context.args) if context.args else "Không có lý do"
    user_id = user.id
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_afk (user_id, reason, afk_time)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    reason = excluded.reason,
                    afk_time = CURRENT_TIMESTAMP
            """, (user_id, reason))
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB: {e}")
            user_afk[user_id] = {"reason": reason, "time": datetime.now()}
    else:
        user_afk[user_id] = {"reason": reason, "time": datetime.now()}
    await update.message.reply_text(f"💤 {user.full_name} đã offline\nLý do: {reason}")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /ping — đo latency và uptime."""
    receive_ms = max(0.0, (datetime.now(timezone.utc) - update.message.date).total_seconds() * 1000)
    t0 = time.monotonic()
    msg = await update.message.reply_text("🏓")
    api_ms = (time.monotonic() - t0) * 1000
    delta = datetime.now() - _BOT_START_TIME
    total_s = int(delta.total_seconds())
    days, rem = divmod(total_s, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    await msg.edit_text(
        f"🏓 *Pong\!*\n"
        f"📡 Nhận tin nhắn: `{receive_ms:.0f} ms`\n"
        f"🌐 Telegram API: `{api_ms:.0f} ms`\n"
        f"⏱️ Uptime: `{uptime_str}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /restart — chỉ owner."""
    from config import OWNER_ID
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Chỉ owner mới dùng được lệnh này.")
        return
    await update.message.reply_text("🔄 Đang khởi động lại bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)
