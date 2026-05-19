"""
handlers/events.py — Event handlers: welcome, answer_handler, check_user_info_change, check_afk
"""
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import get_db_connection, user_afk, user_info, quiz_messages
from utils.helpers import format_duration
from handlers.ai_chat import ai_chat_handler
from handlers.media import download_video


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chào mừng baby đã đến với nhóm"""
    for new_member in update.message.new_chat_members:
        welcome_text = f"👋 **Chào mừng {new_member.full_name} đến với nhóm!**\n\n📰 /news - Tin mới từ VnExpress\n🌤️ /tt - Tra thời tiết\n🎲 /daoly - Đạo lý hôm nay\n♟️ /caro - Đánh Caro\n❓ /quiz - Trò chơi quiz"
        keyboard = [
            [InlineKeyboardButton("📜 Xem Nội Quy", callback_data="show_rules")],
            [InlineKeyboardButton("💬 Liên hệ Admin", url="https://t.me/sylviee6")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


async def check_user_info_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra nếu người dùng thay đổi tên hoặc username"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    current_full_name = user.full_name or "No Name"
    current_username = user.username or "No Username"

    # Lần đầu gặp user này
    if user_id not in user_info:
        user_info[user_id] = {
            'full_name': current_full_name,
            'username': current_username
        }
        return

    old_info = user_info[user_id]
    old_full_name = old_info['full_name']
    old_username = old_info['username']

    name_changed = old_full_name != current_full_name
    username_changed = old_username != current_username

    if name_changed or username_changed:
        message = "👀 Check\n\n"
        message += f"🌞 Người dùng: {current_full_name} [{user_id}]\n"

        if name_changed:
            message += f"✨ Đã thay đổi tên từ {old_full_name} ➡️ {current_full_name}\n"

        if username_changed:
            old_username_display = f"@{old_username}" if old_username != "No Username" else "Không có"
            new_username_display = f"@{current_username}" if current_username != "No Username" else "Không có"
            message += f"✨ Đã thay đổi họ từ {old_username_display} ➡️ {new_username_display}"

        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except:
            pass

        user_info[user_id] = {
            'full_name': current_full_name,
            'username': current_username
        }


async def check_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra AFK"""
    message = update.message
    user_id = message.from_user.id

    afk_record = None
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT reason, afk_time FROM user_afk WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                afk_record = {"reason": result[0], "time": result[1]}
                cursor.execute("DELETE FROM user_afk WHERE user_id = ?", (user_id,))
                conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB: {e}")
    else:
        if user_id in user_afk:
            afk_record = user_afk[user_id]
            del user_afk[user_id]

    if afk_record:
        duration = format_duration(datetime.now() - afk_record["time"])
        await message.reply_text(
            f"👋 {message.from_user.full_name} đã trở lại sau {duration}!\nLý do AFK: {afk_record['reason']}"
        )
        return

    if message.entities:
        for entity in message.entities:
            if entity.type in ["mention", "text_mention"]:
                mentioned_user = entity.user if hasattr(entity, 'user') else None
                if mentioned_user and mentioned_user.id != user_id:
                    mentioned_id = mentioned_user.id
                    afk_info = None
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT reason, afk_time FROM user_afk WHERE user_id = ?", (mentioned_id,))
                            result = cursor.fetchone()
                            if result:
                                afk_info = {"reason": result[0], "time": result[1]}
                            cursor.close()
                            conn.close()
                        except sqlite3.Error as e:
                            print(f"Lỗi DB: {e}")
                    if not afk_info and mentioned_id in user_afk:
                        afk_info = user_afk[mentioned_id]
                    if afk_info:
                        duration = format_duration(datetime.now() - afk_info["time"])
                        await message.reply_text(
                            f"💤 {mentioned_user.full_name} đang AFK {duration}\nLý do: {afk_info['reason']}"
                        )


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router chính cho text messages - xử lý theo thứ tự ưu tiên"""
    # 1. Kiểm tra thay đổi tên/username
    await check_user_info_change(update, context)

    # 2. AI chat (nếu mention/reply bot) — FIX: return nếu đã xử lý
    handled = await ai_chat_handler(update, context)
    if handled:
        return

    text = update.message.text.strip() if update.message.text else ""
    text_lower = text.lower()
    user_id = update.effective_user.id

    # 3. Auto-download TikTok/YouTube links
    is_link = text.startswith("http://") or text.startswith("https://")
    is_tiktok = is_link and ("tiktok.com" in text_lower or "vm.tiktok.com" in text_lower or "vt.tiktok.com" in text_lower)
    is_youtube = is_link and ("youtube.com" in text_lower or "youtu.be" in text_lower)
    is_soundcloud = is_link and "soundcloud.com" in text_lower

    if (is_tiktok or is_youtube) and not is_soundcloud:
        context.args = [text]
        await download_video(update, context)
        return

    # 4. Quiz answer check
    text_clean = text.strip().lower()
    expected = context.user_data.get('quiz_answer')
    if expected:
        if text_clean == expected:
            response = await update.message.reply_text("✅ Giỏi quá em!")
        else:
            response = await update.message.reply_text(f"❌ Sai rồi baby. Đáp án là: {expected}")

        if user_id in quiz_messages:
            quiz_messages[user_id].append(update.message.message_id)
            quiz_messages[user_id].append(response.message_id)

        del context.user_data['quiz_answer']
        return

    # 5. Fallback: AFK check
    await check_afk(update, context)
