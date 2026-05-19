"""
handlers/admin.py — Admin commands: warn, ban, unban, check, admins, rules
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import sqlite3

from database import get_db_connection, user_warnings


async def admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị danh sách admin"""
    chat = update.effective_chat
    admins_list = await context.bot.get_chat_administrators(chat.id)

    text = "👥 **Danh sách Admin:**\n\n"
    for admin in admins_list:
        status = "👑" if admin.status == "creator" else "⭐"
        text += f"{status} {admin.user.full_name}"
        if admin.user.username:
            text += f" (@{admin.user.username})"
        text += "\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cảnh báo thành viên"""
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("⛔ Chỉ admin mới có thể sử dụng lệnh này!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Vui lòng reply tin nhắn của người cần cảnh báo!")
        return

    warned_user = update.message.reply_to_message.from_user
    user_id = warned_user.id

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_warnings (user_id, warn_count, last_updated)
                VALUES (?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    warn_count = user_warnings.warn_count + 1,
                    last_updated = CURRENT_TIMESTAMP
            """, (user_id,))
            conn.commit()
            cursor.execute("SELECT warn_count FROM user_warnings WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            warn_count = result[0] if result else 0
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB: {e}")
            if user_id not in user_warnings:
                user_warnings[user_id] = 0
            user_warnings[user_id] += 1
            warn_count = user_warnings[user_id]
    else:
        if user_id not in user_warnings:
            user_warnings[user_id] = 0
        user_warnings[user_id] += 1
        warn_count = user_warnings[user_id]

    text = f"⚠️ **Cảnh báo {warn_count}/3**\nNgười dùng: {warned_user.full_name}\n"
    if warn_count >= 3:
        text += "\n🚫 Đã đạt 3 cảnh báo!"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị nội quy nhóm"""
    rules_text = """📋 **NỘI QUY NHÓM**
You Are Gay !!!
⚠️ Vi phạm sẽ bị cảnh báo hoặc kick khỏi nhóm!"""
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cấm một thành viên"""
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("⛔ Only admin !")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Vui lòng reply!")
        return

    target_user = update.message.reply_to_message.from_user
    if target_user.username == "sylviee6":
        await update.message.reply_text("Bé tính làm gì ")
        return

    try:
        await context.bot.ban_chat_member(chat.id, target_user.id)
        await update.message.reply_text(f"✅ Đã sút {target_user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gỡ cấm một thành viên"""
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("⛔ Chỉ admin!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Vui lòng reply!")
        return

    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(chat.id, target_user.id)
        await update.message.reply_text(f"✅ Chào em quay lại  {target_user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")


async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra thông tin thành viên"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Vui lòng reply tin nhắn của người cần kiểm tra!")
        return

    user = update.message.reply_to_message.from_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    user_id = user.id

    warn_count = 0
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT warn_count FROM user_warnings WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            warn_count = result[0] if result else 0
            cursor.close()
            conn.close()
        except sqlite3.Error:
            warn_count = user_warnings.get(user_id, 0)
    else:
        warn_count = user_warnings.get(user_id, 0)

    info_text = f"👤 **{user.full_name}**\nUsername: @{user.username or 'N/A'}\nID: `{user.id}`\nStatus: {member.status}\n"
    if warn_count > 0:
        info_text += f"⚠️ Cảnh báo: {warn_count}/3"

    await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)
